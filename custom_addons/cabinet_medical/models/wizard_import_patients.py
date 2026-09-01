from odoo import models, fields
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError, ValidationError
import base64
import io
import datetime
import logging

_logger = logging.getLogger(__name__)

# Batch size for creation – avoids memory issues on large files
BATCH_SIZE = 50


class WizardImportPatients(models.TransientModel):
    _name = 'cabinet.wizard.import.patients'
    _description = 'Import patients depuis Excel'

    fichier_excel = fields.Binary(string='Fichier Excel', required=True)
    nom_fichier = fields.Char(string='Nom du fichier')
    resultat = fields.Text(string='Résultat', readonly=True)

    # ---------------------------------------------------------------------
    # Helper utilities
    # ---------------------------------------------------------------------
    @staticmethod
    def _safe_str(value):
        """Return a stripped string or None. Does NOT upper‑case (caller decides)."""
        if value is None:
            return None
        try:
            return str(value).strip()
        except Exception:
            return None

    @staticmethod
    def _to_upper(value):
        """Return a stripped upper‑cased string or None."""
        if value is None:
            return None
        try:
            return str(value).strip().upper()
        except Exception:
            return None

    @staticmethod
    def _to_bool(value):
        """Convert common Excel truthy representations to bool.
        Accepts booleans, integers (1/0), and strings like 'TRUE', 'Oui'.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in ('true', '1', 'yes', 'oui', 'y', 'vrai')
        return False

    @staticmethod
    def _clean_regime_cnam(value):
        """Map flexible user inputs to valid regime_cnam Selection keys."""
        if not value:
            return None
        v = str(value).strip().lower()
        mapping = {
            'cnss': 'cnss_salarie',
            'cnss_salarie': 'cnss_salarie',
            'salarie': 'cnss_salarie',
            'cnss_independant': 'cnss_independant',
            'independant': 'cnss_independant',
            'cnrps': 'cnrps_fonctionnaire',
            'cnrps_fonctionnaire': 'cnrps_fonctionnaire',
            'fonctionnaire': 'cnrps_fonctionnaire',
            'cnrps_militaire': 'cnrps_militaire',
            'militaire': 'cnrps_militaire',
            'retraite_cnss': 'retraite_cnss',
            'retraite_cnrps': 'retraite_cnrps',
            'retraite': 'retraite_cnss',
            'etudiant': 'etudiant',
            'autre': 'autre',
        }
        return mapping.get(v, 'autre' if v else None)

    @staticmethod
    def _clean_filiere_cnam(value):
        """Map flexible user inputs to valid filiere_cnam Selection keys."""
        if not value:
            return None
        v = str(value).strip().lower()
        if 'prive' in v or 'tiers' in v:
            return 'privee'
        if 'rembours' in v:
            return 'remboursement'
        if 'publi' in v:
            return 'remboursement'  # standard fallback for public/remboursement
        return 'remboursement' if v else None

    @staticmethod
    def _to_date(value):
        """Convert Excel cell values to datetime.date.
        Handles datetime objects, Excel serial numbers, common string formats.
        Returns None if conversion fails or value is empty.
        """
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            return value.date()
        if isinstance(value, datetime.date):
            return value
        # Excel serial number (float/int)
        if isinstance(value, (int, float)):
            try:
                from openpyxl.utils.datetime import from_excel  # type: ignore
                return from_excel(value).date()
            except Exception:
                return None
        # String parsing (common formats)
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
                try:
                    return datetime.datetime.strptime(value, fmt).date()
                except Exception:
                    continue
        return None

    # ---------------------------------------------------------------------
    # Main import action
    # ---------------------------------------------------------------------
    def action_importer(self):
        """Import patients from an uploaded Excel file.

        Processing flow:
        1. Parse & validate each row (mandatory fields, CNAM rules, CIN format)
        2. Check CIN uniqueness against DB + within the file itself
        3. Create patients row‑by‑row inside a per‑row savepoint
        4. Report errors per line number
        """
        # Ensure openpyxl is available
        try:
            import openpyxl  # type: ignore
        except ImportError:
            raise UserError("openpyxl non installé. Installez‑le via : pip install openpyxl")

        if not self.fichier_excel:
            raise UserError("Veuillez sélectionner un fichier à importer.")

        # Decode the uploaded file
        data = base64.b64decode(self.fichier_excel)  # type: ignore
        workbook = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
        sheet = workbook.active

        # Column indexes (0‑based) – keep in sync with the Excel template
        COL = {
            'name': 0, 'date_naissance': 1, 'genre': 2, 'telephone': 3,
            'cin': 4, 'adresse': 5, 'is_cnam': 6, 'numero_cnam': 7,
            'regime_cnam': 8, 'filiere_cnam': 9, 'date_validite_cnam': 10,
            'is_apci': 11, 'numero_decision_apci': 12, 'date_fin_apci': 13,
            'has_assurance': 14, 'assurance_name': 15, 'assurance_numero': 16,
        }

        # Pre‑load insurance cache {name: record}
        Assurance = self.env['cabinet.assurance']
        assurance_cache = {rec.name: rec for rec in Assurance.search([])}

        # Pre‑load existing CINs for duplicate detection
        existing_cins = set()
        patients = self.env['cabinet.patient'].search_read(
            [('cin', '!=', False)], ['cin']
        )
        for p in patients:
            if p['cin']:
                existing_cins.add(p['cin'].strip())

        # Track CINs seen in this file to catch intra‑file duplicates
        file_cins = set()

        Patient = self.env['cabinet.patient']
        created = 0
        errors = []
        warnings = []
        total_rows = 0

        for idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):  # type: ignore
            # Skip entirely empty rows
            if all(cell.value is None for cell in row[:5]):
                continue

            total_rows += 1

            try:
                with self.env.cr.savepoint():
                    # --- Extract & validate mandatory fields ---
                    name = self._to_upper(row[COL['name']].value)
                    cin = self._safe_str(row[COL['cin']].value)

                    if not name:
                        raise ValidationError("Nom obligatoire manquant")
                    if not cin:
                        raise ValidationError("CIN obligatoire manquant")

                    # CIN format: exactly 8 digits
                    cin_clean = cin.replace(' ', '')
                    if not cin_clean.isdigit() or len(cin_clean) != 8:
                        raise ValidationError(
                            f"CIN '{cin}' invalide (8 chiffres attendus)"
                        )
                    cin = cin_clean

                    # CIN uniqueness: against DB and within the file
                    if cin in existing_cins:
                        raise ValidationError(
                            f"CIN {cin} existe déjà dans la base"
                        )
                    if cin in file_cins:
                        raise ValidationError(
                            f"CIN {cin} en doublon dans le fichier (déjà vu)"
                        )

                    # --- CNAM business rules ---
                    is_cnam = self._to_bool(row[COL['is_cnam']].value)
                    numero_cnam = self._safe_str(row[COL['numero_cnam']].value)

                    if is_cnam and not numero_cnam:
                        raise ValidationError(
                            "CNAM actif mais numéro CNAM manquant"
                        )
                    if not is_cnam and numero_cnam:
                        raise ValidationError(
                            "Numéro CNAM renseigné alors que CNAM n'est pas actif"
                        )

                    # --- Build vals ---
                    vals = {
                        'name': name,
                        'date_naissance': self._to_date(row[COL['date_naissance']].value),
                        'genre': self._safe_str(row[COL['genre']].value).lower() if self._safe_str(row[COL['genre']].value) else None,
                        'telephone': self._safe_str(row[COL['telephone']].value) or None,
                        'cin': cin,
                        'adresse': self._safe_str(row[COL['adresse']].value) or None,
                        'is_cnam': is_cnam,
                        'numero_cnam': numero_cnam or None,
                        'regime_cnam': self._clean_regime_cnam(row[COL['regime_cnam']].value) if is_cnam else None,
                        'filiere_cnam': self._clean_filiere_cnam(row[COL['filiere_cnam']].value) if is_cnam else None,
                        'date_validite_cnam': self._to_date(row[COL['date_validite_cnam']].value),
                        'is_apci': self._to_bool(row[COL['is_apci']].value),
                        'numero_decision_apci': self._safe_str(row[COL['numero_decision_apci']].value) or None,
                        'date_fin_apci': self._to_date(row[COL['date_fin_apci']].value),
                        'has_assurance': self._to_bool(row[COL['has_assurance']].value),
                    }

                    # --- Insurance handling with cache ---
                    assurance_raw = self._safe_str(row[COL['assurance_name']].value)
                    if assurance_raw:
                        assurance = assurance_cache.get(assurance_raw)
                        if not assurance:
                            assurance = Assurance.search([('name', '=', assurance_raw)], limit=1)
                            if not assurance:
                                assurance = Assurance.create({'name': assurance_raw, 'taux': 80.0})
                                warnings.append(
                                    f"⚠️ Ligne {idx} : Nouvelle assurance '{assurance_raw}' créée avec un taux par défaut de 80% — à vérifier et ajuster manuellement si besoin."
                                )
                            assurance_cache[assurance_raw] = assurance
                        vals['assurance_id'] = assurance.id
                    vals['assurance_numero'] = self._safe_str(
                        row[COL['assurance_numero']].value
                    ) or None

                    Patient.create(vals)
                    created += 1
                    # Track CIN as successfully imported
                    existing_cins.add(cin)
                    file_cins.add(cin)

            except Exception as e:
                err_msg = getattr(e, 'name', str(e))
                errors.append(f"Ligne {idx} : {err_msg}")
                _logger.warning("Import patients – ligne %s: %s", idx, e)

        # --- Si succès sans erreurs : Ouvrir la boîte de dialogue professionnelle avec bouton OK ---
        if created > 0 and not errors:
            success_msg = f"🎉 Importation réussie !\n\n{created} patient{'s ont été créés' if created > 1 else ' a été créé'} avec succès dans la base de données."
            if warnings:
                success_msg += f"\n\n⚠️ {len(warnings)} avertissement(s) :\n" + "\n".join(warnings)

            success_wizard = self.env['cabinet.wizard.import.patients.success'].create({
                'message': success_msg,
            })
            return {
                'name': '✅ Importation réussie',
                'type': 'ir.actions.act_window',
                'res_model': 'cabinet.wizard.import.patients.success',
                'res_id': success_wizard.id,
                'view_mode': 'form',
                'target': 'new',
            }


        # --- Si des erreurs sont survenues ou 0 patient créé : Conserver le formulaire ouvert avec le rapport détaillé ---
        parts = [f"Traitement terminé — {total_rows} lignes traitées."]
        parts.append(f"✅ {created} patients créés.")
        if warnings:
            parts.append(f"\n⚠️ {len(warnings)} avertissement(s) :")
            parts.extend(warnings)
        if errors:
            parts.append(f"\n❌ {len(errors)} erreur(s) détectée(s) :")
            parts.extend(errors)
        self.resultat = "\n".join(parts)

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,  # type: ignore
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'new',
        }


class WizardImportPatientsSuccess(models.TransientModel):
    _name = 'cabinet.wizard.import.patients.success'
    _description = 'Confirmation de succès import patients'

    message = fields.Text(string='Message', readonly=True)

    def action_ok(self):
        """Ferme la boîte de dialogue et recharge la vue liste des patients"""
        action = self.env['ir.actions.act_window']._for_xml_id('cabinet_medical.action_patient_secretaire') if self.env.ref('cabinet_medical.action_patient_secretaire', raise_if_not_found=False) else self.env['ir.actions.act_window']._for_xml_id('cabinet_medical.action_patient')
        action['target'] = 'main'
        return action
