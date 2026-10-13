# -*- coding: utf-8 -*-
import unittest
import os
import sys
from datetime import date, datetime, timedelta
import io
import base64
from unittest.mock import MagicMock

addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(addon_dir)

# -------------------------------------------------------------------------
# ÉMULATION LÉGÈRE DU CADRE ODOO (STANDALONE UNIT TEST ENVIRONMENT)
# -------------------------------------------------------------------------

mock_odoo = MagicMock()
mock_odoo.modules.get_module_resource = lambda mod, *args: os.path.join(addon_dir, *args) if mod == 'cabinet_medical' else None

def mock_selection(*args, **kwargs):
    return MagicMock()

mock_fields = MagicMock()
mock_fields.Selection = mock_selection
mock_fields.Char = MagicMock
mock_fields.Text = MagicMock
mock_fields.Date = MagicMock
mock_fields.Datetime = MagicMock
mock_fields.Boolean = MagicMock
mock_fields.Many2one = MagicMock
mock_fields.One2many = MagicMock
mock_fields.Integer = MagicMock
mock_fields.Float = MagicMock
mock_fields.Binary = MagicMock
mock_fields.Html = MagicMock

class MockRecordSet(list):
    def __iter__(self): return super().__iter__()
    def __len__(self): return super().__len__()
    def exists(self): return bool(self)
    def ensure_one(self):
        if len(self) != 1: raise ValueError('Expected singleton')
        return self[0]
    def write(self, vals):
        for r in self: r.write(vals)
        return True
    def unlink(self): return True
    def with_context(self, *args, **kwargs):
        if self: return self[0].with_context(*args, **kwargs)
        return self

class MockSavepoint:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): return False

class MockCursor:
    def savepoint(self):
        return MockSavepoint()

class MockEnv(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cr = MockCursor()
        self.context = {}

class MockModel:
    _name = ''
    def __init__(self, **kwargs):
        self._context = {}
        self.env = MockEnv()
        self.env.context = self._context
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __iter__(self):
        yield self

    def __len__(self):
        return 1

    def __bool__(self):
        return True

    def ensure_one(self):
        return self

    def write(self, vals):
        for k, v in vals.items():
            setattr(self, k, v)
        return True

    def with_context(self, *args, **kwargs):
        return self

def mock_decorator(*args, **kwargs):
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return args[0]
    def wrapper(fn):
        return fn
    return wrapper

mock_api = MagicMock()
mock_api.onchange = mock_decorator
mock_api.constrains = mock_decorator
mock_api.depends = mock_decorator
mock_api.model = mock_decorator
mock_api.model_create_multi = mock_decorator

class ValidationError(Exception): pass
class AccessError(Exception): pass
class UserError(Exception): pass

mock_exceptions = MagicMock()
mock_exceptions.ValidationError = ValidationError
mock_exceptions.AccessError = AccessError
mock_exceptions.UserError = UserError

mock_odoo.fields = mock_fields
mock_odoo.models = MagicMock()
mock_odoo.models.Model = MockModel
mock_odoo.models.TransientModel = MockModel
mock_odoo.api = mock_api
mock_odoo.exceptions = mock_exceptions

sys.modules['odoo'] = mock_odoo
sys.modules['odoo.fields'] = mock_fields
sys.modules['odoo.models'] = mock_odoo.models
sys.modules['odoo.api'] = mock_api
sys.modules['odoo.exceptions'] = mock_exceptions

# Import direct des modules métiers à tester
import importlib.util

def _load_module(rel_path, mod_name):
    full_path = os.path.join(addon_dir, *rel_path.split('/'))
    spec = importlib.util.spec_from_file_location(mod_name, full_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod

mod_patient = _load_module('models/patient.py', 'models.patient')
mod_import = _load_module('models/wizard_import_patients.py', 'models.wizard_import_patients')
mod_creer = _load_module('models/wizard_creer_patient.py', 'models.wizard_creer_patient')

PatientClass = mod_patient.Patient
WizardImportClass = mod_import.WizardImportPatients
WizardCreerClass = mod_creer.WizardCreerPatient


# =========================================================================
# SUITE 1 : TESTS DU MODÈLE PATIENT (cabinet.patient)
# =========================================================================

class TestPatientModel(unittest.TestCase):
    """Tests unitaires isolés pour les contraintes et règles métier de cabinet.patient."""

    def setUp(self):
        self.patient = PatientClass(
            id=1,
            name="BEN SALAH MOHAMED",
            cin="09876543",
            telephone="98123456",
            date_naissance=date(1985, 3, 20),
            genre="homme",
            is_cnam=False,
            is_apci=False,
            has_assurance=False,
        )

    def test_01_check_cin_unique_raises_when_duplicate_found(self):
        """Vérifie que _check_cin_unique lève ValidationError si un autre patient partage le même CIN."""
        self.patient.search_count = MagicMock(return_value=1)
        with self.assertRaises(ValidationError) as ctx:
            self.patient._check_cin_unique()
        self.assertIn("déjà utilisé par un autre patient", str(ctx.exception))

    def test_02_check_cin_unique_passes_when_unique(self):
        """Vérifie que _check_cin_unique s'exécute avec succès lorsque search_count vaut 0."""
        self.patient.search_count = MagicMock(return_value=0)
        try:
            self.patient._check_cin_unique()
        except ValidationError:
            self.fail("_check_cin_unique ne doit pas lever d'exception pour un CIN unique.")

    def test_03_check_cin_unique_empty_ignored(self):
        """Vérifie qu'un CIN vide ou non renseigné n'est pas bloqué par la contrainte python."""
        self.patient.cin = False
        self.patient.search_count = MagicMock()
        self.patient._check_cin_unique()
        self.patient.search_count.assert_not_called()

    def test_04_compute_cin_error_invalid_length(self):
        """Vérifie le message d'erreur si le CIN ne fait pas exactement 8 chiffres."""
        self.patient.cin = "12345"
        self.patient._compute_cin_error()
        self.assertEqual(self.patient.cin_error, "Le CIN doit contenir exactement 8 chiffres")

    def test_05_compute_cin_error_non_digits(self):
        """Vérifie le message d'erreur si le CIN contient des caractères non numériques."""
        self.patient.cin = "1234567A"
        self.patient._compute_cin_error()
        self.assertEqual(self.patient.cin_error, "Le CIN doit contenir exactement 8 chiffres")

    def test_06_compute_cin_error_valid(self):
        """Vérifie qu'aucun message d'erreur n'est positionné pour un CIN valide à 8 chiffres."""
        self.patient.cin = "09876543"
        self.patient._compute_cin_error()
        self.assertFalse(self.patient.cin_error)

    def test_07_compute_telephone_error_invalid_length(self):
        """Vérifie le message d'erreur si le téléphone ne fait pas 8 chiffres."""
        self.patient.telephone = "98123"
        self.patient._compute_telephone_error()
        self.assertEqual(self.patient.telephone_error, "Le numéro de téléphone doit contenir exactement 8 chiffres")

    def test_08_compute_telephone_error_valid(self):
        """Vérifie qu'aucun message d'erreur n'apparaît pour un téléphone valide à 8 chiffres."""
        self.patient.telephone = "98123456"
        self.patient._compute_telephone_error()
        self.assertFalse(self.patient.telephone_error)

    def test_09_compute_date_error_future(self):
        """Vérifie la détection d'une date de naissance dans le futur."""
        self.patient.date_naissance = date.today() + timedelta(days=10)
        self.patient._compute_date_error()
        self.assertEqual(self.patient.date_error, "La date de naissance ne peut pas être dans le futur")

    def test_10_compute_date_error_valid_past(self):
        """Vérifie qu'une date de naissance passée ne déclenche aucune erreur."""
        self.patient.date_naissance = date(1995, 1, 1)
        self.patient._compute_date_error()
        self.assertFalse(self.patient.date_error)

    def test_11_dossier_status_incomplet_missing_field(self):
        """Vérifie que l'absence d'un champ civil de base (ex: genre) marque le dossier incomplet."""
        self.patient.genre = ''
        self.patient._compute_dossier_status()
        self.assertFalse(self.patient.is_dossier_complet)
        self.assertEqual(self.patient.dossier_status, "Incomplet")

    def test_12_dossier_status_complet_sans_cnam(self):
        """Vérifie qu'un dossier avec tous les champs civils remplis et sans CNAM est marqué complet."""
        self.patient.genre = 'homme'
        self.patient.is_cnam = False
        self.patient.is_apci = False
        self.patient.has_assurance = False
        self.patient._compute_dossier_status()
        self.assertTrue(self.patient.is_dossier_complet)
        self.assertEqual(self.patient.dossier_status, "Complet")

    def test_13_dossier_status_cnam_incomplet_sans_filiere(self):
        """Vérifie qu'un patient CNAM sans numéro ou filière reste en statut Incomplet."""
        self.patient.is_cnam = True
        self.patient.numero_cnam = "0123456789"
        self.patient.filiere_cnam = False  # Manquant
        self.patient._compute_dossier_status()
        self.assertFalse(self.patient.is_dossier_complet)
        self.assertEqual(self.patient.dossier_status, "Incomplet")

    def test_14_dossier_status_cnam_complet(self):
        """Vérifie qu'un patient CNAM avec matricule et filière devient complet."""
        self.patient.is_cnam = True
        self.patient.numero_cnam = "0123456789"
        self.patient.filiere_cnam = "privee"
        self.patient._compute_dossier_status()
        self.assertTrue(self.patient.is_dossier_complet)
        self.assertEqual(self.patient.dossier_status, "Complet")

    def test_15_dossier_status_apci_incomplet_sans_decision(self):
        """Vérifie qu'un patient APCI sans numéro de décision formelle est Incomplet."""
        self.patient.is_cnam = True
        self.patient.numero_cnam = "0123456789"
        self.patient.filiere_cnam = "privee"
        self.patient.is_apci = True
        self.patient.numero_decision_apci = False
        self.patient._compute_dossier_status()
        self.assertFalse(self.patient.is_dossier_complet)

    def test_16_dossier_status_apci_complet(self):
        """Vérifie qu'un patient APCI avec numéro de décision est Complet."""
        self.patient.is_cnam = True
        self.patient.numero_cnam = "0123456789"
        self.patient.filiere_cnam = "privee"
        self.patient.is_apci = True
        self.patient.numero_decision_apci = "DEC-2026-999"
        self.patient._compute_dossier_status()
        self.assertTrue(self.patient.is_dossier_complet)

    def test_17_compute_profil_couverture(self):
        """Vérifie la catégorisation du profil de couverture (sans, cnam, apci)."""
        self.patient.is_cnam = False
        self.patient.is_apci = False
        self.patient._compute_profil_couverture()
        self.assertEqual(self.patient.profil_couverture, "sans")

        self.patient.is_cnam = True
        self.patient.is_apci = False
        self.patient._compute_profil_couverture()
        self.assertEqual(self.patient.profil_couverture, "cnam")

        self.patient.is_cnam = True
        self.patient.is_apci = True
        self.patient._compute_profil_couverture()
        self.assertEqual(self.patient.profil_couverture, "apci")

    def test_18_onchange_is_cnam_resets_apci(self):
        """Vérifie que décocher is_cnam réinitialise automatiquement les champs APCI."""
        self.patient.is_cnam = False
        self.patient.is_apci = True
        self.patient.numero_decision_apci = "DEC-001"
        self.patient.date_debut_apci = date.today()
        self.patient.date_fin_apci = date.today()

        self.patient._onchange_is_cnam()
        self.assertFalse(self.patient.is_apci)
        self.assertFalse(self.patient.numero_decision_apci)
        self.assertFalse(self.patient.date_debut_apci)
        self.assertFalse(self.patient.date_fin_apci)

    def test_19_compute_cnam_expired(self):
        """Vérifie la détection de dépassement de validité CNAM."""
        today = date.today()
        self.patient.is_cnam = True

        self.patient.date_validite_cnam = today - timedelta(days=1)
        self.patient._compute_cnam_expired()
        self.assertTrue(self.patient.is_cnam_expired)

        self.patient.date_validite_cnam = today + timedelta(days=30)
        self.patient._compute_cnam_expired()
        self.assertFalse(self.patient.is_cnam_expired)

    def test_20_compute_apci_expired(self):
        """Vérifie la détection de fin de prise en charge APCI échue."""
        today = date.today()
        self.patient.is_cnam = True
        self.patient.is_apci = True

        self.patient.date_fin_apci = today - timedelta(days=5)
        self.patient._compute_apci_expired()
        self.assertTrue(self.patient.is_apci_expired)

        self.patient.date_fin_apci = today + timedelta(days=60)
        self.patient._compute_apci_expired()
        self.assertFalse(self.patient.is_apci_expired)


# =========================================================================
# SUITE 2 : TESTS DE L'IMPORTATION EXCEL (cabinet.wizard.import.patients)
# =========================================================================

class TestWizardImportPatients(unittest.TestCase):
    """Tests unitaires isolés pour l'analyse et l'importation Excel de patients."""

    def setUp(self):
        self.wizard = WizardImportClass()
        self.wizard.id = 1
        self.wizard.resultat = ""
        self.mock_patient_model = MagicMock()
        self.mock_assurance_model = MagicMock()
        self.mock_success_model = MagicMock()

        self.wizard.env = MockEnv({
            'cabinet.patient': self.mock_patient_model,
            'cabinet.assurance': self.mock_assurance_model,
            'cabinet.wizard.import.patients.success': self.mock_success_model,
        })
        self.wizard._name = 'cabinet.wizard.import.patients'

    def _create_excel_data(self, rows):
        """Génère un classeur Excel valide en mémoire avec openpyxl et le retourne encodé en base64."""
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        # En-têtes conformes au dictionnaire COL de wizard_import_patients.py
        headers = [
            'Nom', 'Date Naissance', 'Genre', 'Téléphone', 'CIN', 'Adresse',
            'CNAM', 'N° CNAM', 'Régime CNAM', 'Filière CNAM', 'Validité CNAM',
            'APCI', 'N° Décision APCI', 'Date Fin APCI',
            'Assurance', 'Nom Assurance', 'N° Affiliation'
        ]
        ws.append(headers)
        for r in rows:
            ws.append(r)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return base64.b64encode(buf.read())

    def test_01_helpers_parsing(self):
        """Vérifie le comportement des utilitaires statiques de parsing de cellules."""
        # _safe_str & _to_upper
        self.assertEqual(WizardImportClass._safe_str("  Ali Ben Salah  "), "Ali Ben Salah")
        self.assertIsNone(WizardImportClass._safe_str(None))
        self.assertEqual(WizardImportClass._to_upper("  ben salah  "), "BEN SALAH")

        # _to_bool
        self.assertTrue(WizardImportClass._to_bool(True))
        self.assertTrue(WizardImportClass._to_bool("Oui"))
        self.assertTrue(WizardImportClass._to_bool("1"))
        self.assertTrue(WizardImportClass._to_bool("TRUE"))
        self.assertFalse(WizardImportClass._to_bool("non"))
        self.assertFalse(WizardImportClass._to_bool(False))
        self.assertFalse(WizardImportClass._to_bool(None))

        # _clean_genre
        self.assertEqual(WizardImportClass._clean_genre("H"), "homme")
        self.assertEqual(WizardImportClass._clean_genre("Femme"), "femme")
        self.assertIsNone(WizardImportClass._clean_genre("inconnu"))

        # _clean_regime_cnam
        self.assertEqual(WizardImportClass._clean_regime_cnam("cnss"), "cnss_salarie")
        self.assertEqual(WizardImportClass._clean_regime_cnam("fonctionnaire"), "cnrps_fonctionnaire")
        self.assertEqual(WizardImportClass._clean_regime_cnam("autre_valeur"), "autre")

        # _clean_filiere_cnam
        self.assertEqual(WizardImportClass._clean_filiere_cnam("tiers"), "privee")
        self.assertEqual(WizardImportClass._clean_filiere_cnam("remboursement"), "remboursement")

        # _to_date
        self.assertEqual(WizardImportClass._to_date("15/03/1985"), date(1985, 3, 15))
        self.assertEqual(WizardImportClass._to_date("1985-03-15"), date(1985, 3, 15))
        self.assertIsNone(WizardImportClass._to_date("date_invalide"))

    def test_02_action_importer_no_file_raises_user_error(self):
        """Vérifie qu'exécuter l'import sans fichier sélectionné déclenche une UserError."""
        self.wizard.fichier_excel = False
        with self.assertRaises(UserError) as ctx:
            self.wizard.action_importer()
        self.assertIn("sélectionner un fichier", str(ctx.exception))

    def test_03_action_importer_valid_file_creates_patients(self):
        """Vérifie l'import réussi d'un fichier contenant deux patients valides."""
        rows = [
            ['BEN SALAH ALI', '15/05/1990', 'homme', '98123456', '09876543', 'Tunis', True, '0123456789', 'cnss', 'privee', '31/12/2026', False, None, None, False, None, None],
            ['TRABELSI FATMA', '20/10/1988', 'femme', '22456789', '01234567', 'Ariana', False, None, None, None, None, False, None, None, False, None, None],
        ]
        self.wizard.fichier_excel = self._create_excel_data(rows)

        # Base initiale sans CIN
        self.mock_patient_model.search_read.return_value = []
        self.mock_assurance_model.search.return_value = []
        mock_success = MagicMock(id=42)
        self.mock_success_model.create.return_value = mock_success

        res = self.wizard.action_importer()

        # Doit créer 2 patients
        self.assertEqual(self.mock_patient_model.create.call_count, 2)
        created_vals = [call_args[0][0] for call_args in self.mock_patient_model.create.call_args_list]
        self.assertEqual(created_vals[0]['cin'], '09876543')
        self.assertEqual(created_vals[0]['name'], 'BEN SALAH ALI')
        self.assertEqual(created_vals[1]['cin'], '01234567')

        # Doit ouvrir le wizard de succès
        self.assertEqual(res.get('res_model'), 'cabinet.wizard.import.patients.success')
        self.assertEqual(res.get('res_id'), 42)

    def test_04_action_importer_duplicate_cin_in_db_records_error(self):
        """Vérifie qu'un CIN déjà présent en base est rejeté avec indication de l'erreur."""
        rows = [
            ['NOUVEAU PATIENT', '15/05/1990', 'homme', '98123456', '09876543', 'Tunis', False, None, None, None, None, False, None, None, False, None, None],
        ]
        self.wizard.fichier_excel = self._create_excel_data(rows)

        # Simuler que le CIN 09876543 existe déjà en base
        self.mock_patient_model.search_read.return_value = [{'cin': '09876543'}]
        self.mock_assurance_model.search.return_value = []

        res = self.wizard.action_importer()

        # 0 création
        self.mock_patient_model.create.assert_not_called()
        # Le formulaire reste ouvert avec le rapport d'erreur
        self.assertEqual(res.get('res_model'), 'cabinet.wizard.import.patients')
        self.assertIn("0 patients créés", self.wizard.resultat)
        self.assertIn("CIN 09876543 existe déjà dans la base", self.wizard.resultat)

    def test_05_action_importer_duplicate_cin_in_same_file(self):
        """Vérifie la conservation des lignes valides quand une ligne ultérieure est un doublon intra-fichier."""
        rows = [
            ['PREMIER PATIENT', '15/05/1990', 'homme', '98123456', '09876543', 'Tunis', False, None, None, None, None, False, None, None, False, None, None],
            ['SECOND DOUBLON',  '20/10/1988', 'femme', '22456789', '09876543', 'Ariana', False, None, None, None, None, False, None, None, False, None, None],
        ]
        self.wizard.fichier_excel = self._create_excel_data(rows)

        self.mock_patient_model.search_read.return_value = []
        self.mock_assurance_model.search.return_value = []

        res = self.wizard.action_importer()

        # 1 seul patient créé (la première ligne), la 2e ligne est rejetée en erreur
        self.assertEqual(self.mock_patient_model.create.call_count, 1)
        self.assertIn("1 patients créés", self.wizard.resultat)
        self.assertIn("1 erreur(s) détectée(s)", self.wizard.resultat)
        self.assertIn("CIN 09876543", self.wizard.resultat)

    def test_06_action_importer_invalid_cin_and_missing_name(self):
        """Vérifie la détection d'un CIN avec longueur invalide et d'un nom manquant."""
        rows = [
            ['PATIENT CIN COURT', '15/05/1990', 'homme', '98123456', '123', 'Tunis', False, None, None, None, None, False, None, None, False, None, None],
            ['', '20/10/1988', 'femme', '22456789', '01234567', 'Ariana', False, None, None, None, None, False, None, None, False, None, None],
        ]
        self.wizard.fichier_excel = self._create_excel_data(rows)

        self.mock_patient_model.search_read.return_value = []
        self.mock_assurance_model.search.return_value = []

        res = self.wizard.action_importer()

        self.mock_patient_model.create.assert_not_called()
        self.assertIn("8 chiffres attendus", self.wizard.resultat)
        self.assertIn("Nom obligatoire manquant", self.wizard.resultat)


# =========================================================================
# SUITE 3 : TESTS DU WIZARD CRÉATION RAPIDE (cabinet.rendezvous.creer.patient)
# =========================================================================

class TestWizardCreerPatient(unittest.TestCase):
    """Tests unitaires isolés pour la création d'un dossier depuis un rendez-vous rapide."""

    def setUp(self):
        self.mock_rdv = MagicMock(id=10, patient_name="MOHAMED TEMPORAIRE")
        self.wizard = WizardCreerClass(
            name="MOHAMED TEMPORAIRE",
            telephone="98123456",
            cin="09876543",
            genre="homme",
            date_naissance=date(1990, 1, 1),
            rendezvous_id=self.mock_rdv,
            is_cnam=False,
            is_apci=False,
            has_assurance=False,
        )
        self.mock_patient_model = MagicMock()
        self.wizard.env = MockEnv({
            'cabinet.patient': self.mock_patient_model,
        })

    def test_01_check_telephone_valid_prefixes(self):
        """Vérifie que les numéros tunisiens commençant par 2, 4, 5, 7 ou 9 sont acceptés."""
        for num in ["98123456", "22123456", "55123456", "44123456", "71123456"]:
            self.wizard.telephone = num
            try:
                self.wizard._check_telephone()
            except ValidationError:
                self.fail(f"Le numéro {num} avec préfixe tunisien valide ne doit pas lever d'erreur.")

    def test_02_check_telephone_invalid_prefix_or_length(self):
        """Vérifie qu'un préfixe non tunisien ou une mauvaise longueur lève ValidationError."""
        self.wizard.telephone = "12345678"  # Commence par 1
        with self.assertRaises(ValidationError) as ctx:
            self.wizard._check_telephone()
        self.assertIn("commencer par 2, 4, 5, 7 ou 9", str(ctx.exception))

        self.wizard.telephone = "9812345"  # 7 chiffres
        with self.assertRaises(ValidationError) as ctx:
            self.wizard._check_telephone()
        self.assertIn("exactement 8 chiffres", str(ctx.exception))

    def test_03_check_cin_length(self):
        """Vérifie que le CIN dans le wizard de création doit faire 8 chiffres."""
        self.wizard.cin = "123"
        with self.assertRaises(ValidationError):
            self.wizard._check_cin()

        self.wizard.cin = "09876543"
        self.wizard._check_cin()  # OK

    def test_04_action_confirmer_missing_name_raises(self):
        """Vérifie que la confirmation sans nom renseigné est rejetée."""
        self.wizard.name = "   "
        with self.assertRaises(ValidationError) as ctx:
            self.wizard.action_confirmer()
        self.assertIn("nom du patient est obligatoire", str(ctx.exception))

    def test_05_action_confirmer_creates_patient_and_links_rdv(self):
        """Vérifie la création effective du patient et la mise à jour du rendez-vous."""
        mock_created_patient = MagicMock(id=55, name="MOHAMED TEMPORAIRE")
        self.mock_patient_model.create.return_value = mock_created_patient

        res = self.wizard.action_confirmer()

        # Patient créé avec nom en majuscule
        self.mock_patient_model.create.assert_called_once()
        created_vals = self.mock_patient_model.create.call_args[0][0]
        self.assertEqual(created_vals['name'], "MOHAMED TEMPORAIRE")
        self.assertEqual(created_vals['cin'], "09876543")

        # Rendez-vous lié au nouveau patient et nom temporaire effacé
        self.mock_rdv.write.assert_called_once_with({
            'patient_id': 55,
            'patient_name': False,
        })

        # Notification client retournée
        self.assertEqual(res.get('type'), 'ir.actions.client')
        self.assertEqual(res.get('tag'), 'display_notification')


if __name__ == '__main__':
    unittest.main()
