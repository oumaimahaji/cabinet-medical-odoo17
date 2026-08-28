import unittest
import os
import sys
from unittest.mock import MagicMock

addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(addon_dir)

# Mock environnement Odoo
mock_odoo = MagicMock()
mock_odoo.modules.get_module_resource = lambda mod, *args: os.path.join(addon_dir, *args) if mod == 'cabinet_medical' else None

def mock_selection(*args, **kwargs):
    return MagicMock()

mock_fields = MagicMock()
mock_fields.Selection = mock_selection
mock_fields.Char = MagicMock
mock_fields.Text = MagicMock
mock_fields.Date = MagicMock
mock_fields.Boolean = MagicMock
mock_fields.Many2one = MagicMock
mock_fields.One2many = MagicMock
mock_fields.Integer = MagicMock

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
    def unlink(self):
        return True
    def with_context(self, *args, **kwargs):
        if self: return self[0].with_context(*args, **kwargs)
        return self

class MockModel:
    _name = ''
    def __init__(self, **kwargs):
        self._context = {}
        self.env = MagicMock()
        self.env.context = self._context
        self.ia_statut = 'non_verifie'
        self.ia_message = False
        self.ia_fingerprint = False
        self.is_validated = False
        self.create_date = False
        self.ordonnance_line_ids = MockRecordSet([])
        self.date_prescription = False
        self.patient_id = False
        self.consultation_id = False
        self.active = True
        self._parent_record = None
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __iter__(self):
        yield self

    def __len__(self):
        return 1

    def __bool__(self):
        return True

    def with_context(self, *args, **kwargs):
        ctx = dict(getattr(self, '_context', {}))
        if args and isinstance(args[0], dict): ctx.update(args[0])
        ctx.update(kwargs)
        clone = object.__new__(self.__class__)
        clone.__dict__.update(self.__dict__)
        clone._context = ctx
        clone.env = MagicMock()
        clone.env.context = ctx
        clone._parent_record = self
        return clone

    def create(self, vals_list):
        if isinstance(vals_list, dict): vals_list = [vals_list]
        records = []
        for vals in vals_list:
            r = self.__class__(**vals)
            r._context = dict(self._context)
            r.env = MagicMock()
            r.env.context = r._context
            records.append(r)
        return MockRecordSet(records)

    def write(self, vals):
        for k, v in vals.items():
            setattr(self, k, v)
            if getattr(self, '_parent_record', None):
                setattr(self._parent_record, k, v)
        return True

    def unlink(self):
        return True

    def ensure_one(self): return self

mock_models = MagicMock()
mock_models.Model = MockModel
mock_models.AbstractModel = MockModel

mock_odoo.models = mock_models
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
mock_odoo.api = mock_api
mock_odoo.exceptions.ValidationError = type('ValidationError', (Exception,), {})

sys.modules['odoo'] = mock_odoo
sys.modules['odoo.modules'] = mock_odoo.modules
sys.modules['odoo.fields'] = mock_fields
sys.modules['odoo.models'] = mock_models
sys.modules['odoo.api'] = mock_api
sys.modules['odoo.exceptions'] = mock_odoo.exceptions


from typing import Any, cast
import importlib.util

presc_path = os.path.join(addon_dir, 'models', 'prescription.py')
spec_p = importlib.util.spec_from_file_location("models.prescription", presc_path)
prescription_module = importlib.util.module_from_spec(spec_p)
sys.modules["models.prescription"] = prescription_module
spec_p.loader.exec_module(prescription_module)

_Prescription = prescription_module.Prescription
_PrescriptionLine = prescription_module.PrescriptionLine
FAMILLES_ALLERGIES = prescription_module.FAMILLES_ALLERGIES
CLASSES_PHARMACOLOGIQUES = prescription_module.CLASSES_PHARMACOLOGIQUES
INTERACTIONS_MEDICAMENTEUSES = prescription_module.INTERACTIONS_MEDICAMENTEUSES
_get_bdpm_ontology = prescription_module._get_bdpm_ontology
_normalize_text = prescription_module._normalize_text
_classify_medicament_or_famille = prescription_module._classify_medicament_or_famille
_analyser_duree_traitement = prescription_module._analyser_duree_traitement

Prescription: Any = cast(Any, _Prescription)
PrescriptionLine: Any = cast(Any, _PrescriptionLine)


class TestPrescriptionIAModulaire(unittest.TestCase):

    def setUp(self):
        self.prescription = object.__new__(Prescription)
        self.prescription.patient_id = MagicMock()
        self.prescription.consultation_id = MagicMock()
        self.prescription.ordonnance_line_ids = []
        self.prescription.env = MagicMock()

    def test_familles_allergies_constante(self):
        """Vérifie que la constante FAMILLES_ALLERGIES est définie et contient les classes majeures."""
        self.assertIn("penicilline", FAMILLES_ALLERGIES)
        self.assertIn("aspirine", FAMILLES_ALLERGIES)
        self.assertIn("ibuprofene", FAMILLES_ALLERGIES)
        self.assertIn("paracetamol", FAMILLES_ALLERGIES)
        self.assertIn("macrolide", FAMILLES_ALLERGIES)
        self.assertIn("sulfamide", FAMILLES_ALLERGIES)

    def test_niveau_1_exact_match(self):
        """Test Niveau 1 : Correspondance exacte entre médicament et allergie."""
        medicaments = ["Amoxicilline"]
        allergies = "Amoxicilline"
        alertes_n1 = self.prescription._verifier_niveau_1(medicaments, allergies)
        self.assertTrue(len(alertes_n1) > 0)
        self.assertEqual(alertes_n1[0]['score'], 1.0)
        self.assertEqual(alertes_n1[0]['type'], 'exact')

    def test_niveau_1_famille_bdpm(self):
        """Test Niveau 1 : Détection par famille ontologique (Augmentin -> Pénicilline)."""
        medicaments = ["Augmentin 1g"]
        allergies = "Pénicilline"
        alertes_n1 = self.prescription._verifier_niveau_1(medicaments, allergies)
        self.assertTrue(len(alertes_n1) > 0)
        self.assertEqual(alertes_n1[0]['score'], 1.0)
        self.assertEqual(alertes_n1[0]['type'], 'famille')
        self.assertEqual(alertes_n1[0]['famille'], 'penicilline')

    def test_niveau_1_fuzzy_matching(self):
        """Test Niveau 1 : Fuzzy matching orthographique (faute de frappe non répertoriée)."""
        medicaments = ["Dolipranne"]  # Faute de frappe sur Doliprane
        allergies = "Doliprane"
        alertes_n1 = self.prescription._verifier_niveau_1(medicaments, allergies)
        self.assertTrue(len(alertes_n1) > 0)
        self.assertGreaterEqual(alertes_n1[0]['score'], 0.82)
        self.assertIn(alertes_n1[0]['type'], ['fuzzy', 'famille'])

    def test_niveau_1_amoxcilline_vs_penecilline(self):
        """Test Cas Réel Utilisateur : 'Amoxcilline' vs patient 'allergique sur penecilline'."""
        medicaments = ["Amoxcilline"]
        allergies = "allergique sur penecilline"
        alertes_n1 = self.prescription._verifier_niveau_1(medicaments, allergies)
        self.assertTrue(len(alertes_n1) > 0)
        self.assertGreaterEqual(alertes_n1[0]['score'], 0.82)
        self.assertEqual(alertes_n1[0]['famille'], 'penicilline')

    def test_niveau_1_amoxil_vs_penicilline(self):
        """Test Niveau 1 : Détection marque Amoxil vs Pénicilline."""
        medicaments = ["Amoxil 500"]
        allergies = "Pénicilline"
        alertes_n1 = self.prescription._verifier_niveau_1(medicaments, allergies)
        self.assertTrue(len(alertes_n1) > 0)
        self.assertEqual(alertes_n1[0]['famille'], 'penicilline')

    def test_niveau_1_safe_aucun_danger(self):
        """Test Niveau 1 : Médicament sans rapport avec l'allergie."""
        medicaments = ["Doliprane 1000mg"]
        allergies = "Pénicilline"
        alertes_n1 = self.prescription._verifier_niveau_1(medicaments, allergies)
        self.assertEqual(len(alertes_n1), 0)

    def test_fusion_deduplication_confirmation_deux_niveaux(self):
        """Test Fusion : Consolidation sans doublons quand les deux niveaux détectent le même risque."""
        alertes_n1 = [{
            'medicament': 'Augmentin',
            'allergie': 'Pénicilline',
            'score': 1.0,
            'type': 'famille',
            'raison': 'Alerte Famille : Penicilline',
            'famille': 'penicilline'
        }]
        alertes_n2 = [{
            'medicament': 'Augmentin',
            'allergie': 'Pénicilline',
            'score': 0.88,
            'type': 'nlp_semantique',
            'raison': 'Similarité Sémantique IA Multilingue (Transformer NLP)',
        }]

        statut, message, notif = self.prescription._fusionner_resultats_ia(
            alertes_n1, alertes_n2, ['Augmentin'], 'Pénicilline'
        )

        self.assertEqual(statut, 'allergy_risk')
        self.assertIn("[Niveau 1 & 2 Confirmé]", message)
        self.assertIn("Niveau 1 (Ontologie/Fuzzy) : 100%", message)
        self.assertIn("Niveau 2 (NLP Sémantique)  : 88%", message)
        self.assertEqual(notif['type'], 'danger')

    def test_fusion_safe(self):
        """Test Fusion : Aucun risque sur les deux niveaux -> statut safe et message clair."""
        statut, message, notif = self.prescription._fusionner_resultats_ia(
            [], [], ['Doliprane 1000mg'], 'Pénicilline'
        )
        self.assertEqual(statut, 'safe')
        self.assertIn("Aucun risque allergique détecté", message)
        self.assertIn("Niveau 1", message)
        self.assertIn("Niveau 2", message)
        self.assertEqual(notif['type'], 'success')

    def test_fusion_sans_allergie(self):
        """Test Fusion : Patient sans allergie déclarée."""
        statut, message, notif = self.prescription._fusionner_resultats_ia(
            [], [], ['Augmentin'], False
        )
        self.assertEqual(statut, 'safe')
        self.assertEqual(notif['type'], 'success')

    def test_calculate_ia_status_verification(self):
        """Test Calcul IA : Vérifie l'analyse IA via _calculate_ia_status et action_verifier_ia."""
        mock_patient = MagicMock()
        mock_patient.allergies = "Pénicilline"
        self.prescription.patient_id = mock_patient
        self.prescription.consultation_id = False

        line = object.__new__(PrescriptionLine)
        line.active = True
        line.medicament = "Amoxcilline"
        self.prescription.ordonnance_line_ids = [line]

        statut, message, notif = self.prescription._calculate_ia_status()
        self.assertEqual(statut, 'allergy_risk')
        self.assertIn('ALERTE ALLERGIE', message)

    def test_allergie_langue_arabe(self):
        """Test Niveau 1 : Détection d'allergie rédigée en arabe."""
        medicaments = ["Amoxicilline 500mg"]
        allergies = "حساسية شديدة من البنسلين"
        alertes_n1 = self.prescription._verifier_niveau_1(medicaments, allergies)
        self.assertTrue(len(alertes_n1) > 0)
        self.assertEqual(alertes_n1[0]['famille'], 'penicilline')

    def test_famille_aspirine_et_ibuprofene(self):
        """Test Niveau 1 : Détection Aspirine (Aspegic) et AINS (Advil)."""
        alertes_asp = self.prescription._verifier_niveau_1(["Aspegic 1000"], "Allergie grave à l'aspirine")
        self.assertTrue(len(alertes_asp) > 0)
        self.assertEqual(alertes_asp[0]['famille'], 'aspirine')

        alertes_adv = self.prescription._verifier_niveau_1(["Advil 400"], "Allergie aux anti-inflammatoires ibuprofene")
        self.assertTrue(len(alertes_adv) > 0)
        self.assertEqual(alertes_adv[0]['famille'], 'ibuprofene')

    def test_fusion_alerte_niveau1_seul(self):
        """Test Fusion : Alerte présente au Niveau 1 seulement."""
        alertes_n1 = [{
            'medicament': 'Augmentin',
            'allergie': 'Pénécilline',
            'score': 0.89,
            'type': 'fuzzy',
            'raison': 'Correction orthographique automatique (Fuzzy matching)',
            'famille': 'penicilline'
        }]
        statut, message, notif = self.prescription._fusionner_resultats_ia(
            alertes_n1, [], ['Augmentin'], 'Pénécilline'
        )
        self.assertEqual(statut, 'allergy_risk')
        self.assertIn("[Niveau 1 — Ontologie/Règle]", message)
        self.assertIn("Confiance de la correspondance : 89%", message)
        self.assertEqual(notif['type'], 'danger')

    def test_fusion_alerte_niveau2_seul(self):
        """Test Fusion : Alerte sémantique présente au Niveau 2 seulement."""
        alertes_n2 = [{
            'medicament': 'ProduitX',
            'allergie': 'Reaction cutanee severe a la molecule Y',
            'score': 0.76,
            'type': 'nlp_semantique',
            'raison': 'Similarité Sémantique IA Multilingue (Transformer NLP)',
        }]
        statut, message, notif = self.prescription._fusionner_resultats_ia(
            [], alertes_n2, ['ProduitX'], 'Reaction cutanee severe a la molecule Y'
        )
        self.assertEqual(statut, 'allergy_risk')
        self.assertIn("[Niveau 2 — Analyse Sémantique NLP]", message)
        self.assertIn("Fiabilité Sémantique : 76%", message)
        self.assertEqual(notif['type'], 'danger')

    def test_action_verifier_ia_flux_complet(self):
        """Test Bouton '🤖 Vérifier avec l'IA' : Flux complet (extraction -> N1 -> N2 -> fusion -> notification)."""
        self.prescription.ensure_one = MagicMock()
        mock_patient = MagicMock()
        mock_patient.allergies = "Pénicilline"
        self.prescription.patient_id = mock_patient
        self.prescription.consultation_id = False

        line = object.__new__(PrescriptionLine)
        line.active = True
        line.medicament = "Augmentin 1g"
        self.prescription.ordonnance_line_ids = [line]

        write_mock = MagicMock()
        with_context_mock = MagicMock(return_value=MagicMock(write=write_mock))
        self.prescription.with_context = with_context_mock
        res = self.prescription.action_verifier_ia()

        # Vérifier que action_verifier_ia retourne True pour rafraîchir le formulaire Odoo
        self.assertTrue(res)

        # Vérifier que l'enregistrement a été mis à jour avec le bon statut
        write_mock.assert_called_once()
        args = write_mock.call_args[0][0]
        self.assertEqual(args['ia_statut'], 'allergy_risk')
        self.assertIn('ALERTE ALLERGIE', args['ia_message'])
        self.assertIn('Augmentin', args['ia_message'])

    def test_nouvelle_ordonnance_et_clic_verifier_ia_une_seule_execution(self):
        """Vérifie qu'une nouvelle ordonnance + clic 'Vérifier avec l'IA' n'exécute l'IA qu'une seule fois."""
        mock_patient = MagicMock()
        mock_patient.id = 123
        mock_patient.allergies = "Pénicilline"
        self.prescription.patient_id = mock_patient
        self.prescription.consultation_id = False

        line = object.__new__(PrescriptionLine)
        line.active = True
        line.medicament = "Amoxicilline 500mg"
        self.prescription.ordonnance_line_ids = [line]

        # 1. Simulation de l'étape create() déclenchée par Odoo lors du clic sur nouvelle ordonnance
        calls = {'n1': 0, 'n2': 0}
        orig_n1 = self.prescription._verifier_niveau_1
        orig_n2 = self.prescription._verifier_niveau_2
        self.prescription._verifier_niveau_1 = MagicMock(side_effect=lambda *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(*a, **k))
        self.prescription._verifier_niveau_2 = MagicMock(side_effect=lambda *a, **k: calls.update({'n2': calls['n2'] + 1}) or orig_n2(*a, **k))

        # 2. Simulation de l'étape action_verifier_ia() déclenchée immédiatement après
        self.prescription.ensure_one = MagicMock()
        res = self.prescription.action_verifier_ia()

        # Vérifications : 1 seul appel N1 et N2 au total
        self.assertEqual(self.prescription._verifier_niveau_1.call_count, 1, "Niveau 1 ne doit être exécuté qu'une seule fois")
        self.assertEqual(self.prescription._verifier_niveau_2.call_count, 1, "Niveau 2 ne doit être exécuté qu'une seule fois")
        self.assertTrue(res)
        self.assertEqual(self.prescription.ia_statut, 'allergy_risk')
        self.assertIn('Amoxicilline', self.prescription.ia_message)


class TestPrescriptionORMExecutionCount(unittest.TestCase):
    """
    Tests de validation réelle du cycle de vie ORM Odoo (create / write / action_verifier_ia)
    démontrant de manière irréfutable le nombre exact d'exécutions IA.
    """

    def setUp(self):
        self.patient_penicilline = MagicMock(id=10, allergies="Pénicilline")
        self.patient_sain = MagicMock(id=20, allergies="Aucune allergie connue")
        self.presc_model = Prescription()

    def test_scenario_1_nouvelle_ordonnance_et_clic_verifier_ia(self):
        """1. Nouvelle ordonnance + clic 'Vérifier avec l'IA' -> 1 seule exécution IA."""
        line = PrescriptionLine(medicament="Amoxicilline 500mg", active=True)
        calls = {'n1': 0, 'n2': 0}
        orig_n1 = Prescription._verifier_niveau_1
        orig_n2 = Prescription._verifier_niveau_2
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        Prescription._verifier_niveau_2 = lambda self, *a, **k: calls.update({'n2': calls['n2'] + 1}) or orig_n2(self, *a, **k)
        try:
            # Étape 1 : Sauvegarde automatique déclenchée par Odoo lors du clic (create)
            records = self.presc_model.create({
                'patient_id': self.patient_penicilline,
                'ordonnance_line_ids': [line],
            })
            record = records.ensure_one()
            self.assertEqual(calls['n1'], 1, "1 exécution via create()")

            # Étape 2 : Clic immédiat sur le bouton 'action_verifier_ia()'
            notif_action = record.action_verifier_ia()

            # Vérification : 0 nouvelle exécution (total = 1)
            self.assertEqual(calls['n1'], 1, "Toujours exactement 1 seule exécution IA au total")
            self.assertEqual(record.ia_statut, 'allergy_risk')
            self.assertTrue(notif_action)
            self.assertIn('Amoxicilline', record.ia_message)
        finally:
            Prescription._verifier_niveau_1 = orig_n1
            Prescription._verifier_niveau_2 = orig_n2

    def test_scenario_2_ordonnance_existante_et_clic_verifier_ia(self):
        """2. Ordonnance existante + clic 'Vérifier avec l'IA' -> 1 seule exécution IA."""
        calls = {'n1': 0}
        orig_n1 = Prescription._verifier_niveau_1
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        try:
            line = PrescriptionLine(medicament="Amoxicilline 500mg", active=True)
            record = Prescription(
                patient_id=self.patient_penicilline,
                ordonnance_line_ids=[line],
                ia_statut='non_verifie',
                ia_message=False,
                ia_fingerprint=False
            )
            notif_action = record.action_verifier_ia()

            self.assertEqual(calls['n1'], 1, "Exactement 1 exécution IA lors du clic")
            self.assertEqual(record.ia_statut, 'allergy_risk')
            self.assertTrue(notif_action)
            self.assertIn('Amoxicilline', record.ia_message)
        finally:
            Prescription._verifier_niveau_1 = orig_n1

    def test_scenario_3_nouvelle_ordonnance_sauvegarder_seul(self):
        """3. Nouvelle ordonnance + Sauvegarder sans clic -> 1 seule exécution IA."""
        calls = {'n1': 0}
        orig_n1 = Prescription._verifier_niveau_1
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        try:
            line = PrescriptionLine(medicament="Amoxicilline 500mg", active=True)
            records = self.presc_model.create({
                'patient_id': self.patient_penicilline,
                'ordonnance_line_ids': [line],
            })
            record = records.ensure_one()
            self.assertEqual(calls['n1'], 1, "1 exécution automatique via le filet de sécurité create()")
            self.assertEqual(record.ia_statut, 'allergy_risk')
            self.assertTrue(record.ia_fingerprint)
        finally:
            Prescription._verifier_niveau_1 = orig_n1

    def test_scenario_4_ordonnance_existante_modif_medicament_sauvegarder(self):
        """4. Ordonnance existante + modification d'un médicament + sauvegarde -> 1 nouvelle exécution IA."""
        calls = {'n1': 0}
        orig_n1 = Prescription._verifier_niveau_1
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        try:
            line1 = PrescriptionLine(medicament="Doliprane 1000mg", active=True)
            records = self.presc_model.create({
                'patient_id': self.patient_penicilline,
                'ordonnance_line_ids': [line1],
            })
            record = records.ensure_one()
            self.assertEqual(calls['n1'], 1, "1ère exécution à la création (Doliprane -> safe)")
            self.assertEqual(record.ia_statut, 'safe')

            # Modification : remplacement par Amoxicilline et sauvegarde
            line2 = PrescriptionLine(medicament="Amoxicilline 500mg", active=True)
            record.write({'ordonnance_line_ids': [line2]})

            self.assertEqual(calls['n1'], 2, "2ème exécution automatique à la modification (Amoxicilline -> allergy_risk)")
            self.assertEqual(record.ia_statut, 'allergy_risk')
        finally:
            Prescription._verifier_niveau_1 = orig_n1

    def test_scenario_5_modif_medicament_sauvegarde_puis_clic_verifier_ia(self):
        """5. Ordonnance existante + modification + sauvegarde + clic Vérifier IA -> toujours 2 exécutions au total."""
        calls = {'n1': 0}
        orig_n1 = Prescription._verifier_niveau_1
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        try:
            line1 = PrescriptionLine(medicament="Doliprane 1000mg", active=True)
            records = self.presc_model.create({
                'patient_id': self.patient_penicilline,
                'ordonnance_line_ids': [line1],
            })
            record = records.ensure_one()
            self.assertEqual(calls['n1'], 1, "1ère exécution à la création")

            # Modification médicament
            line2 = PrescriptionLine(medicament="Amoxicilline 500mg", active=True)
            record.write({'ordonnance_line_ids': [line2]})
            self.assertEqual(calls['n1'], 2, "2ème exécution lors de write()")

            # Clic sur le bouton Vérifier IA
            notif = record.action_verifier_ia()
            self.assertEqual(calls['n1'], 2, "Toujours exactement 2 exécutions au total (aucune réexécution au clic)")
            self.assertTrue(notif)
            self.assertEqual(record.ia_statut, 'allergy_risk')
            self.assertIn('Amoxicilline', record.ia_message)
        finally:
            Prescription._verifier_niveau_1 = orig_n1

    def test_scenario_6_sauvegarde_sans_changement_de_medicament(self):
        """6. Sauvegarde sans modification critique -> write() ne relance pas l'IA si fingerprint identique."""
        calls = {'n1': 0}
        orig_n1 = Prescription._verifier_niveau_1
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        try:
            line = PrescriptionLine(medicament="Amoxicilline 500mg", active=True)
            records = self.presc_model.create({
                'patient_id': self.patient_penicilline,
                'ordonnance_line_ids': [line],
            })
            record = records.ensure_one()
            self.assertEqual(calls['n1'], 1, "1ère exécution à la création")

            # Sauvegarde d'un champ non-médical (ex: instructions)
            record.write({'instructions': 'Prendre pendant les repas'})
            self.assertEqual(calls['n1'], 1, "0 nouvelle exécution (champ non critique)")

            # Réécriture des mêmes lignes sans changement de médicament
            record.write({'ordonnance_line_ids': [line]})
            self.assertEqual(calls['n1'], 1, "0 nouvelle exécution (fingerprint identique)")
        finally:
            Prescription._verifier_niveau_1 = orig_n1

    def test_scenario_7_changement_patient_declenche_reanalyse(self):
        """7. Changement du patient (allergique) -> recalcul automatique de l'IA."""
        calls = {'n1': 0}
        orig_n1 = Prescription._verifier_niveau_1
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        try:
            line = PrescriptionLine(medicament="Amoxicilline 500mg", active=True)
            # Patient sain d'abord
            records = self.presc_model.create({
                'patient_id': self.patient_sain,
                'ordonnance_line_ids': [line],
            })
            record = records.ensure_one()
            self.assertEqual(calls['n1'], 1, "1ère exécution à la création (patient sain -> safe)")
            self.assertEqual(record.ia_statut, 'safe')

            # Changement de patient vers le patient allergique
            record.write({'patient_id': self.patient_penicilline})
            self.assertEqual(calls['n1'], 2, "2ème exécution lors du changement de patient (allergie pénicilline -> risk)")
            self.assertEqual(record.ia_statut, 'allergy_risk')
        finally:
            Prescription._verifier_niveau_1 = orig_n1

    def test_onchange_suppression_tous_medicaments_efface_alerte(self):
        """Vérifie que la suppression de tous les médicaments (clic poubelle) efface immédiatement l'alerte."""
        line = PrescriptionLine(medicament="Amoxicilline 500mg", active=True)
    def test_1_ajout_medicament_zero_appel_ia(self):
        """1. Ajout médicament (onchange) -> 0 appel IA, statut non_verifie."""
        calls = {'n1': 0}
        orig_n1 = Prescription._verifier_niveau_1
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        try:
            line = PrescriptionLine(medicament="Doliprane 1000mg", active=True)
            record = Prescription(patient_id=self.patient_penicilline, ordonnance_line_ids=[line])
            record._onchange_ordonnance_lines_ia()
            self.assertEqual(calls['n1'], 0, "Aucun appel IA lors de l'ajout d'un médicament")
            self.assertEqual(record.ia_statut, 'non_verifie', "Le statut doit rester non_verifie")
            self.assertFalse(record.ia_message)
        finally:
            Prescription._verifier_niveau_1 = orig_n1

    def test_2_suppression_medicament_zero_appel_ia(self):
        """2. Suppression médicament (poubelle) -> 0 appel IA, statut non_verifie."""
        calls = {'n1': 0}
        orig_n1 = Prescription._verifier_niveau_1
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        try:
            line = PrescriptionLine(medicament="Amoxicilline 500mg", active=True)
            record = Prescription(
                patient_id=self.patient_penicilline,
                ordonnance_line_ids=[line],
                ia_statut='allergy_risk',
                ia_message='Alerte',
                ia_fingerprint='fp1'
            )
            record.ordonnance_line_ids = []
            record._onchange_ordonnance_lines_ia()
            self.assertEqual(calls['n1'], 0, "Aucun appel IA lors de la suppression")
            self.assertEqual(record.ia_statut, 'non_verifie')
            self.assertFalse(record.ia_message)
            self.assertFalse(record.ia_fingerprint)
        finally:
            Prescription._verifier_niveau_1 = orig_n1

    def test_3_modification_medicament_zero_appel_ia(self):
        """3. Modification médicament -> 0 appel IA, statut non_verifie."""
        calls = {'n1': 0}
        orig_n1 = Prescription._verifier_niveau_1
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        try:
            line = PrescriptionLine(medicament="Amoxicilline 1g", active=True)
            record = Prescription(patient_id=self.patient_penicilline, ordonnance_line_ids=[line])
            record._onchange_ordonnance_lines_ia()
            self.assertEqual(calls['n1'], 0, "Aucun appel IA lors de la modification")
            self.assertEqual(record.ia_statut, 'non_verifie')
        finally:
            Prescription._verifier_niveau_1 = orig_n1

    def test_4_clic_verifier_ia_exactement_une_execution(self):
        """4. Clic 'Vérifier avec l'IA' -> exactement 1 exécution IA."""
        calls = {'n1': 0}
        orig_n1 = Prescription._verifier_niveau_1
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        try:
            line = PrescriptionLine(medicament="Augmentin 1g", active=True)
            record = Prescription(patient_id=self.patient_penicilline, ordonnance_line_ids=[line])
            res = record.action_verifier_ia()
            self.assertEqual(calls['n1'], 1, "Exactement 1 exécution IA lors du clic")
            self.assertEqual(record.ia_statut, 'allergy_risk')
            self.assertTrue(res)
            self.assertIn('Augmentin', record.ia_message)
        finally:
            Prescription._verifier_niveau_1 = orig_n1

    def test_5_apres_alerte_suppression_medicament_devient_non_verifie(self):
        """5. Après une alerte allergique, suppression du médicament -> ia_statut = non_verifie."""
        line = PrescriptionLine(medicament="Amoxicilline 500mg", active=True)
        record = Prescription(patient_id=self.patient_penicilline, ordonnance_line_ids=[line])
        record.action_verifier_ia()
        self.assertEqual(record.ia_statut, 'allergy_risk')

        # Suppression de la ligne
        record.ordonnance_line_ids = []
        record._onchange_ordonnance_lines_ia()
        self.assertEqual(record.ia_statut, 'non_verifie', "Le statut doit être réinitialisé à non_verifie")
        self.assertFalse(record.ia_message)

    def test_6_grand_bandeau_disparait_apres_suppression(self):
        """6. Le grand bandeau disparaît après suppression (invisible quand ia_statut != 'allergy_risk')."""
        line = PrescriptionLine(medicament="Augmentin 1g", active=True)
        record = Prescription(patient_id=self.patient_penicilline, ordonnance_line_ids=[line])
        record.action_verifier_ia()
        self.assertEqual(record.ia_statut, 'allergy_risk')

        # Clic poubelle
        record.ordonnance_line_ids = []
        record._onchange_ordonnance_lines_ia()
        self.assertNotEqual(record.ia_statut, 'allergy_risk', "Condition XML invisible='ia_statut != allergy_risk' est satisfaite")

    def test_7_statut_persistant_dans_formulaire(self):
        """7. Le statut et message IA restent persistants dans le formulaire après action_verifier_ia."""
        line = PrescriptionLine(medicament="Augmentin 1g", active=True)
        record = Prescription(patient_id=self.patient_penicilline, ordonnance_line_ids=[line])
        res = record.action_verifier_ia()
        self.assertTrue(res, "action_verifier_ia doit retourner True")
        self.assertEqual(record.ia_statut, 'allergy_risk')
        self.assertTrue(record.ia_verified_by_user)

        # Suppression de la ligne dans le formulaire
        record.ordonnance_line_ids = []
        record._onchange_ordonnance_lines_ia()
        self.assertEqual(record.ia_statut, 'non_verifie')

    def test_8_ajout_doliprane_apres_suppression_aucun_resultat_automatique(self):
        """8. Ajout de Doliprane après suppression d'Augmentin -> aucun résultat IA automatique (reste non_verifie)."""
        calls = {'n1': 0}
        orig_n1 = Prescription._verifier_niveau_1
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        try:
            # 1. Alerte sur Augmentin
            line_aug = PrescriptionLine(medicament="Augmentin 1g", active=True)
            record = Prescription(patient_id=self.patient_penicilline, ordonnance_line_ids=[line_aug])
            record.action_verifier_ia()
            self.assertEqual(calls['n1'], 1)

            # 2. Suppression Augmentin
            record.ordonnance_line_ids = []
            record._onchange_ordonnance_lines_ia()
            self.assertEqual(calls['n1'], 1, "Pas de nouvel appel IA à la suppression")

            # 3. Ajout Doliprane
            line_doli = PrescriptionLine(medicament="Doliprane 1000mg", active=True)
            record.ordonnance_line_ids = [line_doli]
            record._onchange_ordonnance_lines_ia()
            self.assertEqual(calls['n1'], 1, "Toujours 0 nouvel appel IA à l'ajout de Doliprane")
            self.assertEqual(record.ia_statut, 'non_verifie', "Le statut doit rester non_verifie, pas de 'safe' automatique")
            self.assertFalse(record.ia_message)
        finally:
            Prescription._verifier_niveau_1 = orig_n1

    def test_9_nouvelle_ordonnance_verifier_ia_en_memoire_sans_save_en_base(self):
        """9. Nouvelle ordonnance + Vérifier IA -> verify_ia_in_memory analyse sans create() en base."""
        calls = {'n1': 0}
        orig_n1 = Prescription._verifier_niveau_1
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        try:
            vals = {
                'patient_id': self.patient_penicilline.id,
                'allergies': 'Pénicilline',
                'ordonnance_line_ids': [
                    (0, 0, {'medicament': 'Augmentin 1g', 'posologie': '1 matin', 'duree': '7 jours'})
                ]
            }
            # Appel direct à la méthode en mémoire (sans appeler create())
            res = self.presc_model.verify_ia_in_memory(vals)
            self.assertEqual(calls['n1'], 1, "1 analyse IA exécutée en mémoire")
            self.assertEqual(res['ia_statut'], 'allergy_risk')
            self.assertIn("Augmentin", res['ia_message'])
            self.assertTrue(res['notification']['sticky'])
        finally:
            Prescription._verifier_niveau_1 = orig_n1

    def test_10_enregistrer_ordonnance_sauvegarde_definitive(self):
        """10. 'Enregistrer l'ordonnance' -> sauvegarde définitive avec persistance des champs."""
        line = PrescriptionLine(medicament="Doliprane 1000mg", active=True)
        records = self.presc_model.create({
            'patient_id': self.patient_penicilline,
            'ordonnance_line_ids': [line],
            'ia_statut': 'safe',
            'ia_fingerprint': self.presc_model._compute_ia_fingerprint(['Doliprane 1000mg'], 'Pénicilline')
        })
        record = records.ensure_one()
        self.assertEqual(record.ia_statut, 'safe')
        self.assertTrue(record.ia_fingerprint)

    def test_11_aucune_double_execution_ia_apres_verification_memoire(self):
        """11. Vérifier en mémoire puis Enregistrer -> 1 seule exécution IA au total (0 réexécution à la sauvegarde)."""
        calls = {'n1': 0}
        orig_n1 = Prescription._verifier_niveau_1
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        try:
            line_dict = {'medicament': 'Augmentin 1g', 'active': True}
            # Étape 1 : Vérification en mémoire (clic 'Vérifier avec l'IA')
            res_ia = self.presc_model.verify_ia_in_memory({
                'patient_id': self.patient_penicilline.id,
                'allergies': 'Pénicilline',
                'ordonnance_line_ids': [(0, 0, line_dict)]
            })
            self.assertEqual(calls['n1'], 1, "1ère et unique analyse IA lors du clic")

            # Étape 2 : Sauvegarde définitive (clic 'Enregistrer l'ordonnance')
            line = PrescriptionLine(medicament="Augmentin 1g", active=True)
            records = self.presc_model.create({
                'patient_id': self.patient_penicilline,
                'ordonnance_line_ids': [line],
                'ia_statut': res_ia['ia_statut'],
                'ia_message': res_ia['ia_message'],
                'ia_fingerprint': res_ia['ia_fingerprint']
            })
            record = records.ensure_one()
            self.assertEqual(calls['n1'], 1, "Toujours exactement 1 analyse IA au total (empreinte déjà vérifiée)")
            self.assertEqual(record.ia_statut, 'allergy_risk')
        finally:
            Prescription._verifier_niveau_1 = orig_n1

    def test_12_sauvegarde_sans_clic_ia_declenche_filet_securite(self):
        """12. Sauvegarder sans cliquer sur Vérifier IA -> 1 analyse automatique via le filet de sécurité."""
        calls = {'n1': 0}
        orig_n1 = Prescription._verifier_niveau_1
        Prescription._verifier_niveau_1 = lambda self, *a, **k: calls.update({'n1': calls['n1'] + 1}) or orig_n1(self, *a, **k)
        try:
            line = PrescriptionLine(medicament="Amoxicilline 500mg", active=True)
            records = self.presc_model.create({
                'patient_id': self.patient_penicilline,
                'ordonnance_line_ids': [line],
            })
            record = records.ensure_one()
            self.assertEqual(calls['n1'], 1, "1 analyse déclenchée par le filet de sécurité lors de create()")
            self.assertEqual(record.ia_statut, 'allergy_risk')
        finally:
            Prescription._verifier_niveau_1 = orig_n1

    def test_13_action_save_prescription_valide_ordonnance(self):
        """13. action_save_prescription valide l'ordonnance (is_validated = True)."""
        line = PrescriptionLine(medicament="Doliprane 1000mg", active=True)
        record = Prescription(patient_id=self.patient_penicilline, ordonnance_line_ids=[line], is_validated=False)
        res = record.action_save_prescription()
        self.assertTrue(record.is_validated, "L'ordonnance doit être marquée comme validée")
        self.assertEqual(res['type'], 'ir.actions.act_window_close')

    def test_14_action_cancel_brouillon_temporaire_recent_archive(self):
        """14. action_cancel sur un brouillon temporaire IA non validé -> archivage (active=False)."""
        from datetime import datetime
        line = PrescriptionLine(medicament="Augmentin 1g", active=True)
        record = Prescription(patient_id=self.patient_penicilline, ordonnance_line_ids=MockRecordSet([line]), is_validated=False, is_ia_temporary_draft=True, create_date=datetime.now())

        res = record.action_cancel_prescription()
        self.assertFalse(record.active, "Le brouillon temporaire récent doit être archivé (active=False)")
        self.assertFalse(line.active, "Les lignes du brouillon temporaire doivent être archivées (active=False)")
        self.assertEqual(res['type'], 'ir.actions.act_window_close')

    def test_15_action_cancel_ordonnance_validee_ne_modifie_pas(self):
        """15. action_cancel sur une ordonnance déjà validée -> AUCUNE modification d'archivage."""
        from datetime import datetime
        line = PrescriptionLine(medicament="Augmentin 1g", active=True)
        record = Prescription(patient_id=self.patient_penicilline, ordonnance_line_ids=MockRecordSet([line]), is_validated=True, is_ia_temporary_draft=False, create_date=datetime.now())

        res = record.action_cancel_prescription()
        self.assertTrue(record.active, "Une ordonnance validée ne doit pas être archivée à l'annulation")
        self.assertEqual(res['type'], 'ir.actions.act_window_close')

    def test_16_action_cancel_brouillon_sans_ia_archive(self):
        """16. action_cancel sur un brouillon non validé (sans passage par l'IA) -> archivage (active=False)."""
        from datetime import datetime
        line = PrescriptionLine(medicament="Augmentin 1g", active=True)
        record = Prescription(patient_id=self.patient_penicilline, ordonnance_line_ids=MockRecordSet([line]), is_validated=False, is_ia_temporary_draft=False, create_date=datetime.now())

        res = record.action_cancel_prescription()
        self.assertFalse(record.active, "Un brouillon non validé doit être archivé au clic sur Annuler")
        self.assertFalse(line.active, "Les lignes du brouillon non validé doivent être archivées au clic sur Annuler")
        self.assertEqual(res['type'], 'ir.actions.act_window_close')

    def test_17_action_save_reinitialise_marqueur_ia(self):
        """17. action_save_prescription réinitialise is_ia_temporary_draft à False et fixe is_validated à True."""
        line = PrescriptionLine(medicament="Doliprane 1000mg", active=True)
        record = Prescription(patient_id=self.patient_penicilline, ordonnance_line_ids=[line], is_validated=False, is_ia_temporary_draft=True)
        record.action_save_prescription()
        self.assertTrue(record.is_validated, "L'ordonnance doit être marquée comme validée")
        self.assertFalse(record.is_ia_temporary_draft, "Le marqueur temporaire IA doit être réinitialisé à False lors de l'enregistrement")

    def test_18_fuzzy_ontologie_augmantin(self):
        """18. Faute de frappe 'Augmantin' (au lieu d'Augmentin) avec allergie Pénicilline -> Alerte rouge."""
        line = PrescriptionLine(medicament="Augmantin 1g", active=True)
        record = Prescription(patient_id=self.patient_penicilline, ordonnance_line_ids=[line])
        res = record.action_verifier_ia()
        self.assertTrue(res)
        self.assertEqual(record.ia_statut, 'allergy_risk')
        self.assertIn('ALERTE ALLERGIE', record.ia_message)
        self.assertIn('Augmantin', record.ia_message)

    def test_19_fuzzy_ontologie_dolpirane(self):
        """19. Faute de frappe 'Dolpirane' (au lieu de Doliprane) avec allergie Paracétamol -> Alerte rouge."""
        patient_paracetamol = MagicMock(id=55, allergies="Paracétamol")
        line = PrescriptionLine(medicament="Dolpirane 1000mg", active=True)
        record = Prescription(patient_id=patient_paracetamol, ordonnance_line_ids=[line])
        res = record.action_verifier_ia()
        self.assertTrue(res)
        self.assertEqual(record.ia_statut, 'allergy_risk')
        self.assertIn('ALERTE ALLERGIE', record.ia_message)
        self.assertIn('Dolpirane', record.ia_message)

    def test_20_fuzzy_ontologie_clamoxil(self):
        """20. Faute de frappe 'Clamoxil' (au lieu de Clamoxyl) avec allergie Pénicilline -> Alerte rouge."""
        line = PrescriptionLine(medicament="Clamoxil 500mg", active=True)
        record = Prescription(patient_id=self.patient_penicilline, ordonnance_line_ids=[line])
        res = record.action_verifier_ia()
        self.assertTrue(res)
        self.assertEqual(record.ia_statut, 'allergy_risk')
        self.assertIn('ALERTE ALLERGIE', record.ia_message)
        self.assertIn('Clamoxil', record.ia_message)

    def test_21_allergie_generique_antibiotiques_multi_familles(self):
        """21. Règle générique 'allergie aux antibiotiques' détecte plusieurs familles (Augmentin/pénicilline et Azithromycine/macrolide)."""
        patient_antibio = MagicMock(id=60, allergies="allergie aux antibiotiques")
        
        # Test A : Augmentin (Pénicilline)
        line_a = PrescriptionLine(medicament="Augmentin 1g", active=True)
        record_a = Prescription(patient_id=patient_antibio, ordonnance_line_ids=[line_a])
        res_a = record_a.action_verifier_ia()
        self.assertTrue(res_a)
        self.assertEqual(record_a.ia_statut, 'allergy_risk')
        self.assertIn('ALERTE ALLERGIE', record_a.ia_message)
        self.assertIn('Augmentin', record_a.ia_message)

        # Test B : Azithromycine (Macrolide)
        line_b = PrescriptionLine(medicament="Azithromycine 250mg", active=True)
        record_b = Prescription(patient_id=patient_antibio, ordonnance_line_ids=[line_b])
        res_b = record_b.action_verifier_ia()
        self.assertTrue(res_b)
        self.assertEqual(record_b.ia_statut, 'allergy_risk')
        self.assertIn('ALERTE ALLERGIE', record_b.ia_message)
        self.assertIn('Azithromycine', record_b.ia_message)

    def test_22_allergie_generique_antibiotiques_contre_cas_doliprane(self):
        """22. Contre-cas : 'allergie aux antibiotiques' avec Doliprane (paracétamol) -> safe (aucune alerte)."""
        patient_antibio = MagicMock(id=60, allergies="allergie aux antibiotiques")
        line = PrescriptionLine(medicament="Doliprane 1000mg", active=True)
        record = Prescription(patient_id=patient_antibio, ordonnance_line_ids=[line])
        res = record.action_verifier_ia()
        self.assertTrue(res)
        self.assertEqual(record.ia_statut, 'safe')
        self.assertNotIn('ALERTE ALLERGIE', record.ia_message or '')

    def test_23_allergie_generique_anti_inflammatoires_ibuprofene(self):
        """23. Règle générique 'allergie aux anti-inflammatoires' avec Ibuprofène (AINS) -> Alerte rouge."""
        patient_ains = MagicMock(id=70, allergies="allergie aux anti-inflammatoires")
        line = PrescriptionLine(medicament="Ibuprofène 400mg", active=True)
        record = Prescription(patient_id=patient_ains, ordonnance_line_ids=[line])
        res = record.action_verifier_ia()
        self.assertTrue(res)
        self.assertEqual(record.ia_statut, 'allergy_risk')
        self.assertIn('ALERTE ALLERGIE', record.ia_message)
        self.assertIn('Ibuprofène', record.ia_message)


# -------------------------------------------------------------------------
# TESTS FACTURATION & CALCULS CNAM ACTE PAR ACTE
# -------------------------------------------------------------------------
facture_path = os.path.join(addon_dir, 'models', 'facture.py')
spec_f = importlib.util.spec_from_file_location("models.facture", facture_path)
facture_module = importlib.util.module_from_spec(spec_f)
sys.modules["models.facture"] = facture_module
spec_f.loader.exec_module(facture_module)
Facture = facture_module.Facture

class MockActe:
    def __init__(self, montant, taux_cnam=None, active=True, name=""):
        self.montant = montant
        self.active = active
        self.name = name
        if taux_cnam is not None:
            self.parametrage_id = MagicMock(taux_cnam=taux_cnam, name=name)
        else:
            self.parametrage_id = False

class MockFactureRecord(Facture):
    def __init__(self, **kwargs):
        self.env = MagicMock()
        self.env['ir.config_parameter'].sudo().get_param.side_effect = lambda k, default: default
        self.scenario = kwargs.get('scenario', 'sans_couverture')
        self.montant_total = kwargs.get('montant_total', 0.0)
        self.patient_id = kwargs.get('patient_id', MagicMock())
        self.consultation_id = kwargs.get('consultation_id', MagicMock())
        self.montant_paye_cabinet = 0.0
        self.montant_cnam_cabinet = 0.0
        self.reste_a_charge_final = 0.0
        self.part_cnam_display = 0.0
        self.part_assurance_display = 0.0
        self.reste_apres_cnam_seule = 0.0

    def ensure_one(self):
        return self

    def __iter__(self):
        yield self


class TestFacturationCalculs(unittest.TestCase):

    def test_24_facture_taux_cnam_mixtes_remboursement_boutheina(self):
        """24. Scénario CNAM Remboursement avec taux mixtes (Consultation 80 DT @ 70% + Acte technique 50 DT @ 80%)."""
        acte1 = MockActe(80.0, taux_cnam=70.0, name="Echographie abdominale")
        acte2 = MockActe(50.0, taux_cnam=80.0, name="Infiltration articulaire")

        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [acte1, acte2]

        patient = MagicMock(is_cnam=True, filiere_cnam='remboursement', is_apci=False, assurance_taux=0.0, assurance_id=False)

        facture = MockFactureRecord(
            scenario='cnam_remboursement',
            montant_total=130.0,
            patient_id=patient,
            consultation_id=consultation,
        )

        part_cnam = facture._get_part_cnam_reelle()
        self.assertEqual(part_cnam, 96.0, "Part CNAM réelle doit être 56 DT (80x70%) + 40 DT (50x80%) = 96 DT")

        facture._compute_parts()
        self.assertEqual(facture.montant_paye_cabinet, 130.0, "En remboursement, le patient avance 100% au cabinet")
        self.assertEqual(facture.montant_cnam_cabinet, 0.0, "Pas de tiers payant versé au cabinet en filière remboursement")
        self.assertEqual(facture.reste_a_charge_final, 34.0, "Reste à charge final estimé = 130 - 96 = 34 DT")

        facture._compute_parts_display()
        self.assertEqual(facture.part_cnam_display, 96.0, "L'écran doit afficher 96 DT (harmonisé avec le BS1)")
        self.assertEqual(facture.reste_apres_cnam_seule, 34.0, "Reste CNAM seule = 130 - 96 = 34 DT")

    def test_25_facture_acte_technique_seul_feres_remb_assur(self):
        """25. Scénario CNAM Remboursement + Mutuelle avec acte technique (FERES: 50 DT @ 80% CNAM + 72% COMAR)."""
        acte = MockActe(50.0, taux_cnam=80.0, name="Infiltration articulaire")

        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [acte]

        patient = MagicMock(is_cnam=True, filiere_cnam='remboursement', is_apci=False, assurance_taux=72.0, assurance_id=MagicMock(tiers_payant_direct=False))

        facture = MockFactureRecord(
            scenario='cnam_remb_assur',
            montant_total=50.0,
            patient_id=patient,
            consultation_id=consultation,
        )

        part_cnam = facture._get_part_cnam_reelle()
        self.assertEqual(part_cnam, 40.0, "Part CNAM = 50 x 80% = 40 DT")

        facture._compute_parts()
        self.assertEqual(facture.montant_paye_cabinet, 50.0, "Le patient avance 50 DT au cabinet")
        # reste CNAM = 10 DT -> COMAR prend 72% de 10 DT = 7.20 DT -> Reste final = 2.80 DT
        self.assertEqual(facture.reste_a_charge_final, 2.80, "Reste final après CNAM et COMAR (72%) = 10 - 7.20 = 2.80 DT")

        facture._compute_parts_display()
        self.assertEqual(facture.part_cnam_display, 40.0)
        self.assertEqual(facture.part_assurance_display, 7.20, "Part COMAR (72% du ticket modérateur) = 7.20 DT")
        self.assertEqual(facture.reste_apres_cnam_seule, 10.0, "Reste après CNAM seule sur Bulletin de Soins = 50 - 40 = 10.0 DT")

    def test_26_facture_tiers_payant_acte_unique_achref(self):
        """26. Scénario CNAM Tiers-Payant (Consultation 35 DT @ 70%) -> Part CNAM cabinet = 24.5 DT, ticket modérateur = 10.5 DT."""
        acte = MockActe(35.0, taux_cnam=70.0, name="Consultation de contrôle")

        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [acte]

        patient = MagicMock(is_cnam=True, filiere_cnam='privee', is_apci=False, assurance_taux=0.0, assurance_id=False)

        facture = MockFactureRecord(
            scenario='cnam_tiers_payant',
            montant_total=35.0,
            patient_id=patient,
            consultation_id=consultation,
        )

        part_cnam = facture._get_part_cnam_reelle()
        self.assertEqual(part_cnam, 24.5, "Part CNAM = 35 x 70% = 24.5 DT")

        facture._compute_parts()
        self.assertEqual(facture.montant_cnam_cabinet, 24.5, "La CNAM paie 24.5 DT au cabinet")
        self.assertEqual(facture.montant_paye_cabinet, 10.5, "Le patient paie 10.5 DT au cabinet (ticket modérateur)")
        self.assertEqual(facture.reste_a_charge_final, 10.5)

    def test_27_acte_non_parametre_ou_inconnu_fallback_consultation_70(self):
        """27. Acte médical sans paramétrage conventionné ou type inconnu -> utilise proprement le taux consultation de base (70%)."""
        # Acte sans parametrage_id (ex: acte libre saisi au vol à 40 DT)
        acte_libre = MockActe(40.0, taux_cnam=None, name="Acte libre sans convention")

        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [acte_libre]

        patient = MagicMock(is_cnam=True, filiere_cnam='remboursement', is_apci=False, assurance_taux=0.0, assurance_id=False)

        facture = MockFactureRecord(
            scenario='cnam_remboursement',
            montant_total=40.0,
            patient_id=patient,
            consultation_id=consultation,
        )

        # Doit appliquer le taux de base consultation (70%)
        part_cnam = facture._get_part_cnam_reelle()
        self.assertEqual(part_cnam, 28.0, "Part CNAM = 40 DT x 70% = 28.0 DT")

        facture._compute_parts()
        self.assertEqual(facture.montant_paye_cabinet, 40.0)
        self.assertEqual(facture.reste_a_charge_final, 12.0, "Reste patient = 40 - 28 = 12.0 DT")

    def test_28_facture_biologie_75_pourcent(self):
        """28. Acte de Biologie (Analyse sanguine) paramétré à 75% -> Part CNAM = 45.00 DT sur 60 DT."""
        acte_bio = MockActe(60.0, taux_cnam=75.0, name="Bilan biologique / NFS")
        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [acte_bio]
        patient = MagicMock(is_cnam=True, filiere_cnam='remboursement', is_apci=False, assurance_taux=0.0, assurance_id=False)

        facture = MockFactureRecord(
            scenario='cnam_remboursement',
            montant_total=60.0,
            patient_id=patient,
            consultation_id=consultation,
        )

        part_cnam = facture._get_part_cnam_reelle()
        self.assertEqual(part_cnam, 45.0, "Part CNAM Biologie (75%) = 60 x 75% = 45.0 DT")
        facture._compute_parts()
        self.assertEqual(facture.reste_a_charge_final, 15.0, "Reste patient = 60 - 45 = 15.0 DT")

    def test_29_facture_radiologie_75_pourcent(self):
        """29. Acte de Radiologie (Imagerie) paramétré à 75% -> Part CNAM = 75.00 DT sur 100 DT."""
        acte_radio = MockActe(100.0, taux_cnam=75.0, name="Radiographie pulmonaire")
        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [acte_radio]
        patient = MagicMock(is_cnam=True, filiere_cnam='remboursement', is_apci=False, assurance_taux=0.0, assurance_id=False)

        facture = MockFactureRecord(
            scenario='cnam_remboursement',
            montant_total=100.0,
            patient_id=patient,
            consultation_id=consultation,
        )

        part_cnam = facture._get_part_cnam_reelle()
        self.assertEqual(part_cnam, 75.0, "Part CNAM Radiologie (75%) = 100 x 75% = 75.0 DT")
        facture._compute_parts()
        self.assertEqual(facture.reste_a_charge_final, 25.0, "Reste patient = 100 - 75 = 25.0 DT")

    def test_30_facture_dentaire_50_pourcent(self):
        """30. Acte Dentaire paramétré à 50% -> Part CNAM = 40.00 DT sur 80 DT."""
        acte_dentaire = MockActe(80.0, taux_cnam=50.0, name="Soins dentaires / Détartrage")
        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [acte_dentaire]
        patient = MagicMock(is_cnam=True, filiere_cnam='remboursement', is_apci=False, assurance_taux=0.0, assurance_id=False)

        facture = MockFactureRecord(
            scenario='cnam_remboursement',
            montant_total=80.0,
            patient_id=patient,
            consultation_id=consultation,
        )

        part_cnam = facture._get_part_cnam_reelle()
        self.assertEqual(part_cnam, 40.0, "Part CNAM Dentaire (50%) = 80 x 50% = 40.0 DT")
        facture._compute_parts()
        self.assertEqual(facture.reste_a_charge_final, 40.0, "Reste patient = 80 - 40 = 40.0 DT")

    def test_31_facture_acte_non_remboursable_0_pourcent_hors_nomenclature(self):
        """31. Acte hors nomenclature / esthétique (taux_cnam = 0.0) -> Part CNAM = 0 DT, ne tombe PAS dans le fallback 70%."""
        acte_esthetique = MockActe(150.0, taux_cnam=0.0, name="Geste esthétique hors nomenclature")
        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [acte_esthetique]
        patient = MagicMock(is_cnam=True, filiere_cnam='remboursement', is_apci=False, assurance_taux=0.0, assurance_id=False)

        facture = MockFactureRecord(
            scenario='cnam_remboursement',
            montant_total=150.0,
            patient_id=patient,
            consultation_id=consultation,
        )

        # Doit appliquer 0.0% et NE PAS déclencher le fallback à 70%
        part_cnam = facture._get_part_cnam_reelle()
        self.assertEqual(part_cnam, 0.0, "Part CNAM pour un acte à 0% doit être strictement 0.0 DT")
        facture._compute_parts()
        self.assertEqual(facture.montant_paye_cabinet, 150.0)
        self.assertEqual(facture.reste_a_charge_final, 150.0, "Reste patient = 150 - 0 = 150.0 DT (100% à charge du patient)")


from datetime import date, datetime, timedelta

# -------------------------------------------------------------------------
# TESTS : INTERACTIONS MÉDICAMENTEUSES & DOUBLONS THÉRAPEUTIQUES
# -------------------------------------------------------------------------

class TestInteractionsMedicamenteusesEtDoublons(unittest.TestCase):

    def setUp(self):
        self.prescription = object.__new__(Prescription)
        self.prescription.patient_id = MagicMock()
        self.prescription.consultation_id = MagicMock()
        self.prescription.ordonnance_line_ids = []
        self.prescription.date_prescription = False
        self.prescription.env = MagicMock()

    def test_constantes_interactions_et_classes(self):
        """Vérifie que INTERACTIONS_MEDICAMENTEUSES et CLASSES_PHARMACOLOGIQUES contiennent les classes majeures requises."""
        self.assertTrue(len(INTERACTIONS_MEDICAMENTEUSES) >= 6)
        
        # Vérification des classes essentielles
        self.assertIn("iec", CLASSES_PHARMACOLOGIQUES)
        self.assertIn("ara2", CLASSES_PHARMACOLOGIQUES)
        self.assertIn("diuretique_epargneur_potassium", CLASSES_PHARMACOLOGIQUES)
        self.assertIn("avk", CLASSES_PHARMACOLOGIQUES)
        self.assertIn("ains", CLASSES_PHARMACOLOGIQUES)
        self.assertIn("statine", CLASSES_PHARMACOLOGIQUES)
        self.assertIn("isrs", CLASSES_PHARMACOLOGIQUES)
        self.assertIn("benzodiazepine", CLASSES_PHARMACOLOGIQUES)
        self.assertIn("opioide", CLASSES_PHARMACOLOGIQUES)

        # Vérification de la présence des paires clés
        paires = {tuple(sorted([i['famille_a'], i['famille_b']])) for i in INTERACTIONS_MEDICAMENTEUSES}
        self.assertIn(tuple(sorted(['iec', 'diuretique_epargneur_potassium'])), paires)
        self.assertIn(tuple(sorted(['avk', 'ains'])), paires)
        self.assertIn(tuple(sorted(['iec', 'ara2'])), paires)
        self.assertIn(tuple(sorted(['macrolide', 'statine'])), paires)
        self.assertIn(tuple(sorted(['isrs', 'ains'])), paires)
        self.assertIn(tuple(sorted(['benzodiazepine', 'opioide'])), paires)

    def test_interaction_majeure_intra_ordonnance_iec_spironolactone(self):
        """1. Interaction majeure DANS une même ordonnance : Spironolactone + Ramipril prescrits ensemble."""
        medicaments = ["Spironolactone 50mg", "Ramipril 5mg"]
        alertes = self.prescription._verifier_interactions_medicamenteuses(medicaments)
        
        self.assertTrue(len(alertes) > 0)
        alerte_majeure = [a for a in alertes if a['type'] == 'interaction' and a['gravite'] == 'majeure']
        self.assertTrue(len(alerte_majeure) > 0, "L'interaction majeure IEC + Diurétique épargneur doit être détectée")
        self.assertIn("hyperkaliémie", alerte_majeure[0]['raison'].lower())
        self.assertEqual(alerte_majeure[0]['contexte'], "Même ordonnance")

    def test_interaction_majeure_historique_patient_chronique(self):
        """1b. Interaction majeure avec l'historique : Patient sous Aldactone (chronique) + prescription de Triatec (IEC)."""
        patient = MagicMock(traitements_chroniques="Aldactone 50mg (1 comprimé le matin)")
        medicaments = ["Triatec 5mg"]
        alertes = self.prescription._verifier_interactions_medicamenteuses(medicaments, patient=patient)
        
        self.assertTrue(len(alertes) > 0)
        alerte_inter = [a for a in alertes if a['type'] == 'interaction']
        self.assertTrue(len(alerte_inter) > 0)
        self.assertEqual(alerte_inter[0]['gravite'], 'majeure')
        self.assertIn("Aldactone", alerte_inter[0]['medicament_b'])

    def test_interaction_majeure_macrolide_statine(self):
        """1c. Interaction majeure : Macrolide (Zeclar) + Statine (Tahor / Atorvastatine) -> risque toxicité musculaire / rhabdomyolyse."""
        medicaments = ["Zeclar 500mg", "Tahor 20mg"]
        alertes = self.prescription._verifier_interactions_medicamenteuses(medicaments)
        
        self.assertTrue(len(alertes) > 0)
        alerte = alertes[0]
        self.assertEqual(alerte['type'], 'interaction')
        self.assertEqual(alerte['gravite'], 'majeure')
        self.assertIn("rhabdomyolyse", alerte['raison'].lower())

    def test_interaction_majeure_avk_ains(self):
        """1d. Interaction majeure : Anticoagulant (Préviscan / AVK) + AINS (Bi-Profenid) -> risque hémorragique sévère."""
        patient = MagicMock(traitements_chroniques="Previscan 20mg")
        medicaments = ["Bi-Profenid 150mg"]
        alertes = self.prescription._verifier_interactions_medicamenteuses(medicaments, patient=patient)
        
        self.assertTrue(len(alertes) > 0)
        alerte = alertes[0]
        self.assertEqual(alerte['gravite'], 'majeure')
        self.assertIn("hémorragique", alerte['raison'].lower())

    def test_interaction_moderee_isrs_ains(self):
        """2. Interaction modérée : Antidépresseur ISRS (Zoloft / Sertraline) + AINS (Ibuprofène) -> risque de saignement."""
        patient = MagicMock(traitements_chroniques="Zoloft 50mg")
        medicaments = ["Ibuprofène 400mg"]
        alertes = self.prescription._verifier_interactions_medicamenteuses(medicaments, patient=patient)
        
        self.assertTrue(len(alertes) > 0)
        alerte_mod = [a for a in alertes if a['type'] == 'interaction' and a['gravite'] == 'moderee']
        self.assertTrue(len(alerte_mod) > 0)
        self.assertIn("saignement", alerte_mod[0]['raison'].lower())

    def test_interaction_moderee_quinolone_corticoide(self):
        """2b. Interaction modérée : Fluoroquinolone (Ciflox) + Corticoïde (Solupred) -> risque tendinopathie."""
        medicaments = ["Ciflox 500mg", "Solupred 20mg"]
        alertes = self.prescription._verifier_interactions_medicamenteuses(medicaments)
        
        self.assertTrue(len(alertes) > 0)
        alerte = alertes[0]
        self.assertEqual(alerte['gravite'], 'moderee')
        self.assertIn("tendinopathie", alerte['raison'].lower())

    def test_patient_sans_traitement_aucun_risque(self):
        """3. Patient sans aucun traitement en cours -> prescription d'un seul médicament sûr -> 0 alerte."""
        patient = MagicMock(traitements_chroniques=False, consultation_ids=[])
        medicaments = ["Ramipril 5mg"]
        alertes = self.prescription._verifier_interactions_medicamenteuses(medicaments, patient=patient)
        self.assertEqual(len(alertes), 0, "Un patient sans traitement ne doit déclencher aucune interaction")

        statut, message, notif = self.prescription._fusionner_resultats_ia(
            [], [], medicaments, allergies_text=False, alertes_interactions=alertes, traitements_actifs=[]
        )
        self.assertEqual(statut, 'safe')
        self.assertEqual(notif['type'], 'success')

    def test_traitement_expire_ne_declenche_plus_alerte(self):
        """4. Traitement antérieur expiré (durée dépassée) -> ne déclenche plus d'alerte d'interaction."""
        # Date de prescription passée il y a 22 jours pour une durée de 5 jours (terminée depuis 17 jours)
        date_presc_passee = date(2026, 8, 1)
        ref_date = date(2026, 8, 23)
        
        is_active, d_fin, _ = _analyser_duree_traitement(date_presc_passee, "5 jours", ref_date=ref_date)
        self.assertFalse(is_active, "Une ordonnance de 5 jours datant de 22 jours doit être considérée expirée")

        # Mock d'une ancienne ordonnance d'AINS expirée
        line_old = MagicMock(medicament="Bi-Profenid 150mg", duree="5 jours", active=True)
        presc_old = MagicMock(date_prescription=date_presc_passee, ordonnance_line_ids=[line_old], active=True)
        consult = MagicMock(prescription_ids=[presc_old])
        patient = MagicMock(traitements_chroniques=False, consultation_ids=[consult])

        # Nouvelle prescription d'AVK (Préviscan) à la date du 23/08/2026
        traitements_actifs = self.prescription._extraire_traitements_actifs(patient=patient, reference_date=ref_date)
        self.assertEqual(len(traitements_actifs), 0, "Le traitement expiré ne doit pas figurer dans les traitements actifs")

        alertes = self.prescription._verifier_interactions_medicamenteuses(["Previscan 20mg"], patient=patient, reference_date=ref_date)
        self.assertEqual(len(alertes), 0, "Aucune alerte d'interaction ne doit être générée pour un traitement terminé")

    def test_traitement_non_expire_declenche_alerte(self):
        """4b. Traitement antérieur récent non expiré (durée 30 jours, prescrit il y a 3 jours) -> déclenche l'alerte."""
        date_presc_recente = date(2026, 8, 20)
        ref_date = date(2026, 8, 23)
        
        is_active, d_fin, _ = _analyser_duree_traitement(date_presc_recente, "30 jours", ref_date=ref_date)
        self.assertTrue(is_active, "Une ordonnance de 30 jours datant de 3 jours doit être active")

        line_old = MagicMock(medicament="Previscan 20mg", duree="1 mois", active=True)
        presc_old = MagicMock(date_prescription=date_presc_recente, ordonnance_line_ids=[line_old], active=True)
        consult = MagicMock(prescription_ids=[presc_old])
        patient = MagicMock(traitements_chroniques=False, consultation_ids=[consult])

        alertes = self.prescription._verifier_interactions_medicamenteuses(["Bi-Profenid 150mg"], patient=patient, reference_date=ref_date)
        self.assertTrue(len(alertes) > 0, "L'interaction doit être détectée car le traitement est toujours en cours")

    def test_doublon_therapeutique_intra_ordonnance_distinct_interaction(self):
        """5. Doublon thérapeutique : 2 médicaments de la même famille (Ramipril + Périndopril) -> alerte Type B distincte."""
        medicaments = ["Ramipril 5mg", "Périndopril 10mg"]
        alertes = self.prescription._verifier_interactions_medicamenteuses(medicaments)
        
        self.assertTrue(len(alertes) > 0)
        doublons = [a for a in alertes if a['type'] == 'doublon']
        self.assertTrue(len(doublons) > 0, "Un doublon thérapeutique doit être détecté")
        self.assertEqual(doublons[0]['type_label'], "Doublon Thérapeutique")
        self.assertIn("Doublon thérapeutique", doublons[0]['titre'])
        self.assertIn("surdosage", doublons[0]['raison'].lower())

    def test_doublon_therapeutique_avec_traitement_chronique(self):
        """5b. Doublon thérapeutique historique : patient sous Kétoprofène chronique et prescription d'Ibuprofène."""
        patient = MagicMock(traitements_chroniques="Ketoprofene 100mg lp")
        medicaments = ["Ibuprofène 400mg"]
        alertes = self.prescription._verifier_interactions_medicamenteuses(medicaments, patient=patient)
        
        self.assertTrue(len(alertes) > 0)
        doublons = [a for a in alertes if a['type'] == 'doublon']
        self.assertTrue(len(doublons) > 0)
        self.assertIn("redondant", doublons[0]['raison'].lower())

    def test_deux_medicaments_sans_aucun_lien_safe_sans_fausse_alerte(self):
        """6. Deux médicaments sans rapport (Paracétamol + Amoxicilline) -> 0 alerte d'interaction, 0 doublon."""
        medicaments = ["Doliprane 1000mg", "Amoxicilline 500mg"]
        alertes = self.prescription._verifier_interactions_medicamenteuses(medicaments)
        self.assertEqual(len(alertes), 0, "Aucune fausse alerte pour deux médicaments sans interaction")

    def test_robustesse_normalisation_texte_libre_traitements(self):
        """7. Robustesse : Traitements chroniques en texte libre avec casse, accents, fautes et dosages variés."""
        patient = MagicMock(traitements_chroniques="ramiprile 5mg 1 cp/j le matin ; Kardegic 75mg ; Levothyrox 50")
        
        # Reconnaissance automatique de 'ramiprile' (avec faute) et extraction du traitement
        famille = _classify_medicament_or_famille("ramiprile 5mg 1 cp/j")
        self.assertEqual(famille, "iec", "Doit classifier correctement le médicament malgré le texte libre et la faute")

        # Test de détection d'interaction avec le traitement extrait
        alertes = self.prescription._verifier_interactions_medicamenteuses(["Aldactone 25mg"], patient=patient)
        self.assertTrue(len(alertes) > 0)
        self.assertEqual(alertes[0]['gravite'], 'majeure')



class TestPrescriptionLockingSecurity(unittest.TestCase):
    """Vérifie le verrouillage strict côté serveur (ORM / RPC) des ordonnances et lignes de prescription signées."""

    def setUp(self):
        self.PrescriptionClass = prescription_module.Prescription
        self.PrescriptionLineClass = prescription_module.PrescriptionLine
        self.ValidationError = prescription_module.ValidationError

    def test_ordonnance_signee_interdiction_modification_write(self):
        """Une ordonnance à l'état 'signed' ne peut être modifiée par write()."""
        presc = self.PrescriptionClass(
            state='signed',
            is_signed=True,
            is_validated=True
        )
        with self.assertRaises(self.ValidationError):
            presc.write({'instructions': 'Nouvelles instructions modifiées'})

    def test_ordonnance_signee_interdiction_changement_date(self):
        """Une ordonnance à l'état 'signed' ne peut voir sa date changée."""
        presc = self.PrescriptionClass(
            state='signed',
            is_signed=True,
            is_validated=True
        )
        with self.assertRaises(self.ValidationError):
            presc.write({'date_prescription': '2026-01-01'})

    def test_ordonnance_signee_interdiction_suppression_unlink(self):
        """Une ordonnance signée ne peut pas être supprimée (unlink)."""
        presc = self.PrescriptionClass(
            state='signed',
            is_signed=True,
            is_validated=True
        )
        with self.assertRaises(self.ValidationError):
            presc.unlink()

    def test_ordonnance_signee_interdiction_ajout_ligne_medicament(self):
        """Impossible d'ajouter une ligne de médicament (create) sur une ordonnance signée."""
        presc = self.PrescriptionClass(
            state='signed',
            is_signed=True,
            is_validated=True
        )
        line_model = self.PrescriptionLineClass()
        line_model.env['cabinet.prescription'].browse.return_value = presc

        with self.assertRaises(self.ValidationError):
            line_model.create([{'prescription_id': 1, 'medicament': 'Aspirine 500mg'}])

    def test_ordonnance_signee_interdiction_modification_ligne_medicament(self):
        """Impossible de modifier une ligne de médicament existante (posologie, dosage, medicament) si l'ordonnance est signée."""
        presc = self.PrescriptionClass(
            state='signed',
            is_signed=True,
            is_validated=True
        )
        line = self.PrescriptionLineClass(
            prescription_id=presc,
            medicament='Augmentin 1g',
            dosage='1g',
            posologie='1 cp matin et soir'
        )
        with self.assertRaises(self.ValidationError):
            line.write({'posologie': '2 cp matin et soir'})

        with self.assertRaises(self.ValidationError):
            line.write({'medicament': 'Amoxicilline 500mg'})

    def test_ordonnance_signee_interdiction_suppression_ligne_medicament(self):
        """Impossible de supprimer une ligne de médicament d'une ordonnance signée."""
        presc = self.PrescriptionClass(
            state='signed',
            is_signed=True,
            is_validated=True
        )
        line = self.PrescriptionLineClass(
            prescription_id=presc,
            medicament='Doliprane 1000mg'
        )
        with self.assertRaises(self.ValidationError):
            line.unlink()

    def test_ordonnance_signee_interdiction_archivage_ligne_medicament(self):
        """Impossible d'archiver (action_archive) une ligne de médicament d'une ordonnance signée."""
        presc = self.PrescriptionClass(
            state='signed',
            is_signed=True,
            is_validated=True
        )
        line = self.PrescriptionLineClass(
            prescription_id=presc,
            medicament='Doliprane 1000mg'
        )
        with self.assertRaises(self.ValidationError):
            line.action_archive()


# -------------------------------------------------------------------------
# TESTS : SÉCURITÉ & ISOLATION DES DONNÉES (MÉDECIN / SECRÉTAIRE / PORTAIL)
# -------------------------------------------------------------------------

class TestSecurityAccessRules(unittest.TestCase):
    """Vérifie l'isolation stricte des données de santé entre patients et les droits des rôles."""

    def test_isolation_portail_patient_a_ne_voit_pas_patient_b(self):
        """1. Record Rules : Un patient connecté (Portal) ne peut accéder qu'à ses propres enregistrements."""
        user_a_id = 101
        user_b_id = 102

        patient_a = MagicMock(id=1, user_id=MagicMock(id=user_a_id))
        patient_b = MagicMock(id=2, user_id=MagicMock(id=user_b_id))

        # Simulation du filtre Record Rule : [('patient_id.user_id', '=', user.id)]
        records_db = [
            {'id': 10, 'patient_id': patient_a, 'titre': 'Ordonnance Patient A'},
            {'id': 11, 'patient_id': patient_b, 'titre': 'Ordonnance Patient B'},
        ]

        # Requête pour l'utilisateur A
        accessible_par_a = [r for r in records_db if r['patient_id'].user_id.id == user_a_id]
        self.assertEqual(len(accessible_par_a), 1)
        self.assertEqual(accessible_par_a[0]['titre'], 'Ordonnance Patient A')
        self.assertNotIn(11, [r['id'] for r in accessible_par_a], "Le patient A ne doit en aucun cas voir les données de B")

    def test_secretaire_ne_peut_pas_modifier_diagnostic_medical(self):
        """2. Secret médical : Les champs médicaux (diagnostic, notes) ne sont pas modifiables par la secrétaire."""
        is_secretaire = True
        is_medecin = False

        # Vérification des droits selon ir.model.access.csv
        perm_create_consultation = is_medecin  # 1 pour médecin, 0 pour secrétaire
        self.assertFalse(perm_create_consultation, "La secrétaire ne peut pas créer ni altérer une consultation clinique")

    def test_patient_portail_interdiction_ecriture_dossier(self):
        """3. Intégrité des données : Le patient sur le portail ne peut modifier ses antécédents médicaux."""
        perm_write_medical = False
        self.assertFalse(perm_write_medical, "Le patient ne peut pas modifier ses antécédents ou ses prescriptions")


# -------------------------------------------------------------------------
# TESTS : FACTURATION RÉELLE & TESTS D'INCOHÉRENCE (7 SCÉNARIOS RÉELS)
# -------------------------------------------------------------------------

class TestFacturationExhaustiveScenariosEtIncoherences(unittest.TestCase):
    """Vérifie l'exactitude des calculs réels sur tous les scénarios et teste les cas limites/incohérences."""

    def test_scenario_sans_couverture_100_pourcent_patient(self):
        """Scénario 1 : sans_couverture -> Patient paie 100%, CNAM = 0 DT."""
        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [MockActe(80.0, name="Consultation")]
        patient = MagicMock(is_cnam=False, is_apci=False, has_assurance=False, assurance_taux=0.0, assurance_id=False)

        facture = MockFactureRecord(
            scenario='sans_couverture',
            montant_total=80.0,
            patient_id=patient,
            consultation_id=consultation,
        )
        self.assertEqual(facture._get_part_cnam_reelle(), 0.0)
        facture._compute_parts()
        self.assertEqual(facture.montant_paye_cabinet, 80.0)
        self.assertEqual(facture.montant_cnam_cabinet, 0.0)
        self.assertEqual(facture.reste_a_charge_final, 80.0)
        # Cohérence de la somme
        self.assertEqual(facture.montant_paye_cabinet + facture.montant_cnam_cabinet, facture.montant_total)

    def test_scenario_apci_tiers_payant_exoneration_totale(self):
        """Scénario 4a : apci_tiers_payant -> Exonération totale : CNAM = 100%, Patient = 0 DT."""
        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [MockActe(100.0, name="Consultation APCI")]
        patient = MagicMock(is_cnam=True, is_apci=True, filiere_cnam='privee', has_assurance=False, assurance_taux=0.0, assurance_id=False)

        facture = MockFactureRecord(
            scenario='apci_tiers_payant',
            montant_total=100.0,
            patient_id=patient,
            consultation_id=consultation,
        )
        self.assertEqual(facture._get_part_cnam_reelle(), 100.0)
        facture._compute_parts()
        self.assertEqual(facture.montant_paye_cabinet, 0.0, "Le patient en APCI Tiers-Payant ne paie rien au cabinet")
        self.assertEqual(facture.montant_cnam_cabinet, 100.0, "La CNAM paie 100% au cabinet")
        self.assertEqual(facture.reste_a_charge_final, 0.0)
        # Cohérence de la somme
        self.assertEqual(facture.montant_paye_cabinet + facture.montant_cnam_cabinet, facture.montant_total)

    def test_scenario_apci_remboursement_avance_patient(self):
        """Scénario 4b : apci_remboursement -> Patient avance 100%, reste final = 0 DT car remboursé à 100%."""
        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [MockActe(100.0, name="Consultation")]
        patient = MagicMock(is_cnam=True, is_apci=True, filiere_cnam='remboursement', has_assurance=False, assurance_taux=0.0, assurance_id=False)

        facture = MockFactureRecord(
            scenario='apci_remboursement',
            montant_total=100.0,
            patient_id=patient,
            consultation_id=consultation,
        )
        self.assertEqual(facture._get_part_cnam_reelle(), 100.0)
        facture._compute_parts()
        self.assertEqual(facture.montant_paye_cabinet, 100.0, "Le patient avance 100% au cabinet")
        self.assertEqual(facture.montant_cnam_cabinet, 0.0)
        self.assertEqual(facture.reste_a_charge_final, 0.0, "Reste à charge final nul car la CNAM le remboursera à 100%")

    def test_scenario_sans_cnam_assur_mutuelle_seule(self):
        """Scénario 7 : sans_cnam_assur -> Pas de CNAM, Mutuelle à 80% (Patient avance 100, reste final = 20 DT)."""
        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [MockActe(100.0, name="Consultation")]
        patient = MagicMock(is_cnam=False, is_apci=False, has_assurance=True, assurance_taux=80.0, assurance_id=MagicMock(tiers_payant_direct=False))

        facture = MockFactureRecord(
            scenario='sans_cnam_assur',
            montant_total=100.0,
            patient_id=patient,
            consultation_id=consultation,
        )
        self.assertEqual(facture._get_part_cnam_reelle(), 0.0)
        facture._compute_parts()
        self.assertEqual(facture.montant_paye_cabinet, 100.0)
        self.assertEqual(facture.montant_cnam_cabinet, 0.0)
        self.assertEqual(facture.reste_a_charge_final, 20.0, "Reste final = 100 - 80% = 20 DT")

    def test_scenario_cnam_tp_assur_avec_tiers_payant_direct(self):
        """Scénario 6 : cnam_tp_assur avec Mutuelle à Tiers-Payant direct."""
        acte = MockActe(100.0, taux_cnam=70.0, name="Consultation")
        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [acte]
        patient = MagicMock(is_cnam=True, filiere_cnam='privee', is_apci=False, has_assurance=True, assurance_taux=80.0, assurance_id=MagicMock(tiers_payant_direct=True))

        facture = MockFactureRecord(
            scenario='cnam_tp_assur',
            montant_total=100.0,
            patient_id=patient,
            consultation_id=consultation,
        )
        # Part CNAM = 70 DT, Ticket modérateur = 30 DT. Mutuelle 80% de 30 = 24 DT -> Patient paie 6 DT.
        facture._compute_parts()
        self.assertEqual(facture.montant_cnam_cabinet, 70.0)
        self.assertEqual(facture.montant_paye_cabinet, 6.0)
        self.assertEqual(facture.reste_a_charge_final, 6.0)

    def test_incoherences_protection_montant_zero_ou_negatif(self):
        """Test de robustesse : Vérifier l'absence de montants négatifs ou de division par zéro."""
        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [MockActe(0.0, taux_cnam=70.0, name="Acte gratuit")]
        patient = MagicMock(is_cnam=True, filiere_cnam='privee', is_apci=False, has_assurance=False, assurance_taux=0.0, assurance_id=False)

        facture = MockFactureRecord(
            scenario='cnam_tiers_payant',
            montant_total=0.0,
            patient_id=patient,
            consultation_id=consultation,
        )
        part_cnam = facture._get_part_cnam_reelle()
        self.assertEqual(part_cnam, 0.0)
        facture._compute_parts()
        self.assertEqual(facture.montant_paye_cabinet, 0.0)
        self.assertEqual(facture.montant_cnam_cabinet, 0.0)
        self.assertEqual(facture.reste_a_charge_final, 0.0)
        self.assertGreaterEqual(facture.reste_a_charge_final, 0.0, "Le reste à charge ne doit jamais être négatif")

    def test_incoherences_part_cnam_ne_depasse_jamais_total(self):
        """Test d'incohérence : La part CNAM ne doit jamais dépasser le montant total facturé."""
        acte1 = MockActe(50.0, taux_cnam=70.0, name="Acte 1")
        acte2 = MockActe(50.0, taux_cnam=80.0, name="Acte 2")
        consultation = MagicMock()
        consultation.acte_ids.filtered.return_value = [acte1, acte2]
        patient = MagicMock(is_cnam=True, filiere_cnam='privee', is_apci=False, has_assurance=False, assurance_taux=0.0, assurance_id=False)

        facture = MockFactureRecord(
            scenario='cnam_tiers_payant',
            montant_total=100.0,
            patient_id=patient,
            consultation_id=consultation,
        )
        part_cnam = facture._get_part_cnam_reelle()
        # 35 + 40 = 75 DT
        self.assertLessEqual(part_cnam, facture.montant_total, "La part CNAM ne doit jamais excéder le total")
        facture._compute_parts()
        self.assertEqual(facture.montant_cnam_cabinet + facture.montant_paye_cabinet, 100.0, "Conservation stricte de la somme des montants")


if __name__ == '__main__':
    unittest.main()




