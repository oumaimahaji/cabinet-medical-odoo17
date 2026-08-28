# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api # type: ignore
from odoo.exceptions import ValidationError # type: ignore

_logger = logging.getLogger(__name__)

class Facture(models.Model):
    _name = 'cabinet.facture'
    _description = 'Facture Médicale'
    _order = 'date_facture desc'

    name = fields.Char(string='Numéro facture', readonly=True, default='Nouveau')
    patient_id = fields.Many2one('cabinet.patient', string='Patient', required=True)
    consultation_id = fields.Many2one('cabinet.consultation', string='Consultation', required=True)
    date_facture = fields.Date(string='Date', required=True, default=fields.Date.today)
    
    # Montants
    montant_total = fields.Float(string='Montant total (DT)', compute='_compute_montant_total', store=True)
    montant_paye_cabinet = fields.Float(string='Payé par le patient (DT)', compute='_compute_parts', store=True)
    montant_cnam_cabinet = fields.Float(string='Payé par CNAM au cabinet (DT)', compute='_compute_parts', store=True)
    reste_a_charge_final = fields.Float(string='Reste à charge final patient (DT)', compute='_compute_parts', store=True)
    
    # Champs d'affichage dynamiques pour la fiche Facture (US15/US16)
    part_cnam_display = fields.Float(string='Part CNAM (DT)', compute='_compute_parts_display', store=True)
    part_assurance_display = fields.Float(string='Part Assurance (DT)', compute='_compute_parts_display', store=True)
    reste_apres_cnam_seule = fields.Float(string='Reste à charge après CNAM (DT)', compute='_compute_parts_display', store=True)

    scenario = fields.Selection([
        ('sans_couverture', 'Sans couverture'),
        ('cnam_remboursement', 'CNAM Remboursement'),
        ('cnam_tiers_payant', 'CNAM Tiers-payant'),
        ('apci_tiers_payant', 'APCI Tiers-payant (Bordereau)'),
        ('apci_remboursement', 'APCI Remboursement (BS1)'),
        ('cnam_remb_assur', 'CNAM Remboursement + Assurance'),
        ('cnam_tp_assur', 'CNAM Tiers-payant + Mutuelle (Remboursement Patient)'),
        ('sans_cnam_assur', 'Sans CNAM + Assurance'),
    ], string='Scénario de Facturation', compute='_compute_scenario', store=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('validated', 'Validée'),
    ], string='État', default='draft')

    # Lien avec Bordereau M5
    bordereau_id = fields.Many2one('cabinet.bordereau', string='Bordereau CNAM', ondelete='set null')
    statut_cnam = fields.Selection([
        ('non_envoye', 'Non Envoyé'),
        ('envoye', 'Envoyé (En attente)'),
        ('paye', 'Payé'),
        ('rejete', 'Rejeté')
    ], string='Statut Paiement CNAM', default='non_envoye')

    @api.depends('consultation_id.acte_ids.montant', 'consultation_id.acte_ids.active')
    def _compute_montant_total(self):
        for rec in self:
            active_actes = rec.consultation_id.acte_ids.filtered(lambda a: a.active)
            total = sum(active_actes.mapped('montant'))
            rec.montant_total = total if total > 0 else 30.0  # Tarif fixe de base

    @api.depends('patient_id.is_cnam', 'patient_id.filiere_cnam', 'patient_id.is_apci', 'patient_id.has_assurance')
    def _compute_scenario(self):
        for rec in self:
            p = rec.patient_id
            if p.is_apci and p.filiere_cnam == 'remboursement':
                rec.scenario = 'apci_remboursement'
            elif p.is_apci:
                rec.scenario = 'apci_tiers_payant'
            elif p.is_cnam and p.filiere_cnam == 'privee' and p.has_assurance:
                rec.scenario = 'cnam_tp_assur'
            elif p.is_cnam and p.filiere_cnam == 'privee':
                rec.scenario = 'cnam_tiers_payant'
            elif p.is_cnam and p.filiere_cnam == 'remboursement' and p.has_assurance:
                rec.scenario = 'cnam_remb_assur'
            elif p.is_cnam and p.filiere_cnam == 'remboursement':
                rec.scenario = 'cnam_remboursement'
            elif not p.is_cnam and p.has_assurance:
                rec.scenario = 'sans_cnam_assur'
            else:
                rec.scenario = 'sans_couverture'

    def _get_part_cnam_reelle(self):
        self.ensure_one()
        total = self.montant_total or 0.0
        if self.scenario in ('apci_tiers_payant', 'apci_remboursement'):
            return round(total, 2)
        if self.scenario in ('sans_couverture', 'sans_cnam_assur'):
            return 0.0

        part_cnam = 0.0
        active_actes = self.consultation_id.acte_ids.filtered(lambda a: a.active)
        if active_actes:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            taux_default = float(IrConfigParam.get_param('cabinet.cnam_taux_consultation', '70.0')) / 100.0
            for acte in active_actes:
                param = getattr(acte, 'parametrage_id', None)
                taux_cnam = getattr(param, 'taux_cnam', None) if param else None
                if param and taux_cnam is not None and taux_cnam is not False:
                    taux = float(taux_cnam) / 100.0
                else:
                    acte_label = getattr(acte, 'name', getattr(acte, 'type_acte', 'Inconnu'))
                    acte_id = getattr(acte, 'id', 'N/A')
                    fac_name = getattr(self, 'name', 'Nouveau')
                    fac_id = getattr(self, 'id', 'N/A')
                    _logger.warning(
                        "Facture %s (ID: %s) : Acte '%s' (ID: %s) sans taux CNAM paramétré -> application du taux consultation par défaut (%s%%)",
                        fac_name, fac_id, acte_label, acte_id, taux_default * 100
                    )
                    taux = taux_default
                part_cnam += acte.montant * taux
        else:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            taux_remb_pct = float(IrConfigParam.get_param('cabinet.cnam_taux_remboursement', '70.0')) / 100.0
            part_cnam = total * taux_remb_pct
        return round(part_cnam, 2)

    @api.depends(
        'montant_total', 'scenario',
        'patient_id.assurance_taux',
        'consultation_id.acte_ids',
        'consultation_id.acte_ids.montant',
        'consultation_id.acte_ids.active',
        'consultation_id.acte_ids.parametrage_id',
        'consultation_id.acte_ids.parametrage_id.taux_cnam',
    )
    def _compute_parts(self):
        for rec in self:
            total = rec.montant_total or 0.0
            taux_assur = (rec.patient_id.assurance_taux or 0.0) / 100.0
            tp_direct = rec.patient_id.assurance_id and rec.patient_id.assurance_id.tiers_payant_direct
            part_cnam_reelle = rec._get_part_cnam_reelle()

            if rec.scenario == 'sans_couverture':  # Sans couverture
                rec.montant_paye_cabinet = round(total, 2)
                rec.montant_cnam_cabinet = 0.0
                rec.reste_a_charge_final = round(total, 2)

            elif rec.scenario == 'apci_tiers_payant':  # APCI Tiers Payant : exonération totale au cabinet
                rec.montant_paye_cabinet = 0.0
                rec.montant_cnam_cabinet = round(total, 2)
                rec.reste_a_charge_final = 0.0

            elif rec.scenario == 'apci_remboursement':  # APCI Remboursement : patient avance tout
                rec.montant_paye_cabinet = round(total, 2)
                rec.montant_cnam_cabinet = 0.0
                rec.reste_a_charge_final = 0.0  # 0 car la CNAM va lui rembourser 100% plus tard

            elif rec.scenario in ('cnam_tiers_payant', 'cnam_tp_assur'):
                ticket_mod = total - part_cnam_reelle
                rec.montant_cnam_cabinet = round(part_cnam_reelle, 2)
                
                # Flexibilité mutuelle
                if rec.scenario == 'cnam_tp_assur' and tp_direct:
                    rec.montant_paye_cabinet = round(ticket_mod * (1.0 - taux_assur), 2)
                else:
                    rec.montant_paye_cabinet = round(ticket_mod, 2)
                    
                rec.reste_a_charge_final = round(ticket_mod * (1.0 - taux_assur), 2) if rec.scenario == 'cnam_tp_assur' else round(ticket_mod, 2)

            elif rec.scenario == 'cnam_remboursement':  # CNAM Remboursement
                # Patient avance tout — CNAM rembourse la part réelle acte par acte après dépôt du dossier
                rec.montant_paye_cabinet = round(total, 2)
                rec.montant_cnam_cabinet = 0.0  # Pas de tiers-payant sur ce scénario
                rec.reste_a_charge_final = round(total - part_cnam_reelle, 2)

            elif rec.scenario == 'cnam_remb_assur':  # CNAM Remboursement + Assurance
                rec.montant_cnam_cabinet = 0.0
                reste_cnam = total - part_cnam_reelle
                
                if tp_direct:
                    rec.montant_paye_cabinet = round(total - (reste_cnam * taux_assur), 2)
                else:
                    rec.montant_paye_cabinet = round(total, 2)
                    
                rec.reste_a_charge_final = round(reste_cnam * (1.0 - taux_assur), 2)

            elif rec.scenario == 'sans_cnam_assur':  # Sans CNAM + Assurance privée
                rec.montant_cnam_cabinet = 0.0
                if tp_direct:
                    rec.montant_paye_cabinet = round(total * (1.0 - taux_assur), 2)
                else:
                    rec.montant_paye_cabinet = round(total, 2)
                rec.reste_a_charge_final = round(total * (1.0 - taux_assur), 2)

    @api.depends(
        'scenario', 'montant_total', 'montant_cnam_cabinet',
        'montant_paye_cabinet', 'reste_a_charge_final',
        'patient_id.assurance_taux', 'patient_id.has_assurance',
        'consultation_id.acte_ids',
        'consultation_id.acte_ids.montant',
        'consultation_id.acte_ids.active',
        'consultation_id.acte_ids.parametrage_id',
        'consultation_id.acte_ids.parametrage_id.taux_cnam',
    )
    def _compute_parts_display(self):
        for rec in self:
            total = rec.montant_total or 0.0
            taux_assur = (rec.patient_id.assurance_taux or 0.0) / 100.0
            part_cnam_reelle = rec._get_part_cnam_reelle()
            
            part_cnam = 0.0
            part_assurance = 0.0
            
            if rec.scenario == 'sans_couverture':
                part_cnam = 0.0
                part_assurance = 0.0
            elif rec.scenario in ('apci_tiers_payant', 'apci_remboursement'):
                part_cnam = total
                part_assurance = 0.0
            elif rec.scenario in ('cnam_tiers_payant', 'cnam_tp_assur'):
                part_cnam = part_cnam_reelle
                if rec.scenario == 'cnam_tp_assur':
                    ticket_mod = total - part_cnam
                    part_assurance = ticket_mod * taux_assur
            elif rec.scenario == 'cnam_remboursement':
                part_cnam = part_cnam_reelle
                part_assurance = 0.0
            elif rec.scenario == 'cnam_remb_assur':
                part_cnam = part_cnam_reelle
                reste_cnam = total - part_cnam
                part_assurance = reste_cnam * taux_assur
            elif rec.scenario == 'sans_cnam_assur':
                part_cnam = 0.0
                part_assurance = total * taux_assur
                
            rec.part_cnam_display = round(part_cnam, 2)
            rec.part_assurance_display = round(part_assurance, 2)
            rec.reste_apres_cnam_seule = round(max(0.0, total - part_cnam), 2)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau') == 'Nouveau':
                vals['name'] = self.env['ir.sequence'].next_by_code('cabinet.facture') or 'Nouveau'
        records = super(Facture, self).create(vals_list)
        for record in records:
            if record.state == 'validated' and record.patient_id:
                self.env['cabinet.notification'].create_notification(
                    patient_id=record.patient_id.id,
                    title="Nouvelle facture disponible",
                    message=f"La facture {record.name} d'un montant de {record.montant_total} DT est disponible.",
                    notif_type='facture',
                    res_url='/my/factures'
                )
        return records

    def write(self, vals):
        pre_vals = {getattr(rec, 'id'): rec.state for rec in self}
        res = super(Facture, self).write(vals)
        if 'state' in vals:
            for record in self:
                old_state = pre_vals.get(getattr(record, 'id'))
                if old_state != 'validated' and record.state == 'validated' and record.patient_id:
                    self.env['cabinet.notification'].create_notification(
                        patient_id=record.patient_id.id,
                        title="Nouvelle facture disponible",
                        message=f"La facture {record.name} d'un montant de {record.montant_total} DT est disponible.",
                        notif_type='facture',
                        res_url='/my/factures'
                    )
        return res

    def action_valider(self):
        self.ensure_one()
        if self.montant_total <= 0:
            raise ValidationError("Le montant total doit être supérieur à 0")
        self.state = 'validated'

    # --- IA n°3 : Assistant LLM pour la reformulation des alertes ---
    @api.model
    def _get_llm_alert(self, anomaly_type, context_data, default_message):
        """ Envoie le contexte à Ollama en local pour reformuler l'alerte en langage naturel """
        import requests # type: ignore
        import time
        url = "http://localhost:11434/api/generate"
        prompt = f"""Tu es l'assistant médical intelligent d'un cabinet médical Odoo.
Alerte : {anomaly_type}
Contexte technique : {context_data}
Message par défaut : {default_message}
Consigne : Rédige une seule phrase d'alerte claire, fluide et professionnelle en français pour la secrétaire médicale. Intègre impérativement tous les détails concrets pertinents fournis dans le contexte (nom du patient, délais en jours, pathologie, référence/décision). Réponds directement sans préambule ni guillemets."""

        start_time = time.time()
        try:
            # Timeout : 1.5s connexion TCP, 15.0s max réponse Phi3 + keep_alive permanent
            response = requests.post(url, json={
                "model": "phi3",
                "prompt": prompt,
                "stream": False,
                "keep_alive": -1,
                "options": {
                    "num_predict": 95,
                    "temperature": 0.1,
                }
            }, timeout=(1.5, 15.0))
            
            if response.status_code == 200:
                result = response.json()
                if 'response' in result and result['response']:
                    cleaned_resp = result['response'].strip().strip('"').strip("'")
                    return f"✨ [IA Assistant] : {cleaned_resp}"
        except Exception as e:
            elapsed = time.time() - start_time
            _logger.warning(
                "Ollama/Phi3 _get_llm_alert failed after %.2fs (%s: %s). Fallback to default message.",
                elapsed, type(e).__name__, e
            )
            
        return default_message

    # --- IA n°2 & 3 : Détection d'anomalie & Assistant LLM ---
    @api.constrains('patient_id')
    def _check_apci_decision(self):
        for rec in self:
            if rec.patient_id.is_apci and not rec.patient_id.numero_decision_apci:
                default_msg = "Anomalie 3 : APCI sans décision. Le statut APCI est activé mais aucune décision CNAM n'est enregistrée pour ce patient."
                context = f"Patient: {rec.patient_id.name}, APCI activé, Décision non fournie"
                alert = self._get_llm_alert("Patient APCI sans décision formelle", context, default_msg)
                raise ValidationError(alert)
