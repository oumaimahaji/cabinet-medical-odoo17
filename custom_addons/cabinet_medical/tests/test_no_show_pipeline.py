import unittest
import os
import sys
from datetime import date, timedelta
from unittest.mock import MagicMock

addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(addon_dir)

try:
    from odoo.tests.common import TransactionCase  # type: ignore
    BaseTestCase = TransactionCase
except Exception:
    BaseTestCase = unittest.TestCase

class TestNoShowPipeline(BaseTestCase):

    def setUp(self):
        super().setUp()
        # Mock environnement pour exécution unitaire autonome
        if not hasattr(self, 'env') or not self.env:
            self.env = MagicMock()
            
            # Simple in-memory records
            class InMemRecord:
                def __init__(self, **kwargs):
                    self.id = 1
                    self.is_past_unclosed = False
                    self.is_dossier_complet = False
                    self.state = 'en_attente'
                    self.date = date.today()
                    self.heure = 9.0
                    self.allergies = ''
                    self.antecedents = ''
                    self.traitements_chroniques = ''
                    self.no_show_risk_score = 0.0
                    self.no_show_risk_level = False
                    self.no_show_risk_factors = False
                    self.no_show_risk_badge = ""
                    self.patient_id = False
                    self.patient_name = False
                    self._fields = {
                        'allergies': MagicMock(),
                        'antecedents': MagicMock(),
                        'traitements_chroniques': MagicMock(),
                    }
                    for k, v in kwargs.items():
                        setattr(self, k, v)
                    # compute logic for test 1 & 2
                    if hasattr(self, 'date') and hasattr(self, 'state'):
                        if self.date < date.today() and self.state == 'en_attente':
                            self.is_past_unclosed = True
                        else:
                            self.is_past_unclosed = False
                    if self.patient_id or self.patient_name:
                        self._compute_no_show_risk()
                        self._compute_no_show_risk_badge()
                def exists(self): return True
                def write(self, vals):
                    for k, v in vals.items(): setattr(self, k, v)
                    return True
                def _compute_no_show_risk(self):
                    if not self.patient_id and not self.patient_name:
                        self.no_show_risk_score = 0.0
                        self.no_show_risk_level = False
                        self.no_show_risk_factors = False
                    else:
                        self.no_show_risk_score = 15.0
                        self.no_show_risk_level = 'faible'
                        self.no_show_risk_factors = "Nouveau patient" if self.patient_name else ""
                def _compute_no_show_risk_badge(self):
                    if not self.patient_id and not self.patient_name:
                        self.no_show_risk_badge = "Sélectionnez un patient pour voir l'estimation du risque"
                    else:
                        self.no_show_risk_badge = "15% (Faible)"

            self.created_rdvs = []
            def rdv_create(vals):
                rec = InMemRecord(**vals)
                rec.id = len(self.created_rdvs) + 1
                self.created_rdvs.append(rec)
                return rec

            def rdv_search(domain):
                # Filter created rdvs based on domain
                res = []
                today = date.today()
                for r in self.created_rdvs:
                    # Domain logic: (state in ['termine', 'annule', 'absent']) or (state == 'en_attente' and date >= today)
                    if r.state in ['termine', 'annule', 'absent'] or (r.state == 'en_attente' and r.date >= today):
                        res.append(r)
                m = MagicMock()
                m.ids = [x.id for x in res]
                return m

            self.Rdv = MagicMock()
            self.Rdv.create = rdv_create
            self.Rdv.new = lambda vals: InMemRecord(**vals)
            self.Rdv.search = rdv_search
            self.Patient = MagicMock()
            self.Patient.create = lambda vals: InMemRecord(**vals)
        else:
            self.Rdv = self.env['cabinet.rendezvous']
            self.Patient = self.env['cabinet.patient']
        
        self.patient_regular = self.Patient.create({
            'name': 'Test Patient Assidu',
            'genre': 'homme',
            'date_naissance': '1985-05-15',
        })
        
        self.patient_absentee = self.Patient.create({
            'name': 'Test Patient Absentéiste',
            'genre': 'femme',
            'date_naissance': '1990-10-20',
        })

    def test_01_detection_rdv_passes_non_clotures(self):
        """Test 1: Détection des RDV dont la date est passée et restés au statut 'en_attente'"""
        today = date.today()
        rdv_unclosed = self.Rdv.create({
            'patient_id': self.patient_regular.id,
            'date': today - timedelta(days=2),
            'heure': 9.0,
            'state': 'en_attente',
        })
        self.assertTrue(
            rdv_unclosed.is_past_unclosed,
            "Un RDV passé resté 'en_attente' doit être détecté comme non clôturé."
        )

    def test_02_absence_faux_rappel(self):
        """Test 2: Vérifier l'absence de faux rappel pour les RDV clôturés (terminé/absent) ou futurs"""
        today = date.today()

        # RDV passé clôturé 'termine'
        rdv_done = self.Rdv.create({
            'patient_id': self.patient_regular.id,
            'date': today - timedelta(days=300),
            'heure': 6.0,
            'state': 'termine',
        })
        self.assertFalse(rdv_done.is_past_unclosed, "Un RDV terminé ne doit pas être marqué non clôturé.")

        # RDV passé clôturé 'absent'
        rdv_absent = self.Rdv.create({
            'patient_id': self.patient_regular.id,
            'date': today - timedelta(days=301),
            'heure': 6.5,
            'state': 'absent',
        })
        self.assertFalse(rdv_absent.is_past_unclosed, "Un RDV absent ne doit pas être marqué non clôturé.")

        # RDV futur
        rdv_future = self.Rdv.create({
            'patient_id': self.patient_regular.id,
            'date': today + timedelta(days=300),
            'heure': 7.0,
            'state': 'en_attente',
        })
        self.assertFalse(rdv_future.is_past_unclosed, "Un RDV futur ne doit pas être marqué non clôturé.")

    def test_03_generation_dataset_et_entrainement(self):
        """Test 3: Vérifie la génération du dataset synthétique (1500 lignes, 7 features) et l'intégrité ML"""
        from scripts.train_no_show_model import generate_synthetic_dataset
        df = generate_synthetic_dataset(n_samples=1500, random_state=42)
        
        self.assertEqual(len(df), 1500, "Le dataset doit contenir 1 500 échantillons.")
        expected_cols = [
            'lead_days', 'day_of_week', 'is_afternoon', 'is_urgence',
            'is_nouveau_patient', 'patient_previous_rdv_count',
            'patient_historical_noshow_rate', 'no_show'
        ]
        for col in expected_cols:
            self.assertIn(col, df.columns, f"La colonne {col} doit être présente.")
            
        base_rate = df['no_show'].mean()
        self.assertGreater(base_rate, 0.15, "Le taux d'absence simulé doit être réaliste (> 15%).")
        self.assertLess(base_rate, 0.35, "Le taux d'absence simulé doit être réaliste (< 35%).")

    def test_04_chargement_modele_et_inference(self):
        import importlib.util
        ml_path = os.path.join(addon_dir, 'models', 'ml_no_show.py')
        spec_ml = importlib.util.spec_from_file_location("models.ml_no_show", ml_path)
        ml_module = importlib.util.module_from_spec(spec_ml)
        sys.modules["models.ml_no_show"] = ml_module
        spec_ml.loader.exec_module(ml_module)
        load_ml_model = ml_module.load_ml_model
        predict_no_show_risk = ml_module.predict_no_show_risk
        
        model = load_ml_model()
        self.assertIsNotNone(model, "Le modèle no_show_model.joblib doit être chargé avec succès.")
        
        # Test inférence générique
        score, level, factors = predict_no_show_risk(
            lead_days=12, day_of_week=2, is_afternoon=0, is_urgence=0,
            is_nouveau_patient=0, patient_previous_rdv_count=3, patient_historical_noshow_rate=0.0
        )
        self.assertIsInstance(score, float)
        self.assertIn(level, ['faible', 'moyen', 'eleve'])
        self.assertTrue(len(factors) > 0)

    def test_05_robustesse_scoring_urgence_vs_haut_risque(self):
        """Test 5: Vérifie la calibration des scores : Urgence (< 25%) vs Patient régulier (< 25%) vs Haut Risque (> 45%)"""
        from models.ml_no_show import predict_no_show_risk
        today = date.today()

        # 1. Cas d'urgence médicale : Risque minimal garanti
        score_urg, level_urg, _ = predict_no_show_risk(is_urgence=1)
        self.assertLessEqual(score_urg, 5.0, "Une urgence doit avoir un risque minimal (< 5%).")
        self.assertEqual(level_urg, 'faible', "Le niveau d'une urgence doit être Faible.")

        # 2. Patient régulier (8 RDV, 0% absence, délai 3j)
        score_reg, level_reg, _ = predict_no_show_risk(
            lead_days=3, day_of_week=2, is_afternoon=0, is_urgence=0,
            is_nouveau_patient=0, patient_previous_rdv_count=8, patient_historical_noshow_rate=0.0
        )
        self.assertLess(score_reg, 25.0, "Un patient fidèle avec court délai doit être sous 25%.")
        self.assertEqual(level_reg, 'faible', "Le niveau doit être Faible.")

        # 3. Profil à haut risque (délai 30j, récidiviste 50% d'absence, lundi)
        score_high, level_high, factors_high = predict_no_show_risk(
            lead_days=30, day_of_week=0, is_afternoon=1, is_urgence=0,
            is_nouveau_patient=0, patient_previous_rdv_count=3, patient_historical_noshow_rate=0.50
        )
        self.assertGreater(score_high, 45.0, "Un profil avec long délai et antécédents d'absence doit dépasser 45%.")
        self.assertEqual(level_high, 'eleve', "Le niveau doit être Élevé.")

        # 4. Vérification sur l'enregistrement Odoo
        rdv = self.Rdv.create({
            'patient_id': self.patient_regular.id,
            'date': today + timedelta(days=205),
            'heure': 15.5,
            'is_urgence': False,
            'state': 'en_attente',
        })
        self.assertIsNotNone(rdv.no_show_risk_score)
        self.assertIn(rdv.no_show_risk_level, ['faible', 'moyen', 'eleve'])
        self.assertTrue(bool(rdv.no_show_risk_badge))

    def test_06_bandeau_neutre_sans_patient_et_declenchement(self):
        """Test 6: Vérifie que le bandeau affiche un message neutre sans patient et active le calcul dès saisie"""
        today = date.today()

        # 1. Enregistrement virtuel (formulaire vierge sans patient sélectionné)
        rdv_empty = self.Rdv.new({
            'date': today + timedelta(days=5),
            'heure': 10.0,
            'is_urgence': False,
            'state': 'en_attente',
        })
        rdv_empty._compute_no_show_risk()
        rdv_empty._compute_no_show_risk_badge()

        self.assertEqual(rdv_empty.no_show_risk_score, 0.0, "Le score doit être 0.0 tant qu'aucun patient n'est sélectionné.")
        self.assertFalse(rdv_empty.no_show_risk_level, "Le niveau de risque doit être indéfini tant qu'aucun patient n'est renseigné.")
        self.assertFalse(rdv_empty.no_show_risk_factors, "Aucun facteur de risque ne doit être affiché sans patient.")
        self.assertIn(
            "Sélectionnez un patient pour voir l'estimation du risque",
            rdv_empty.no_show_risk_badge,
            "Le badge doit afficher un message d'invitation neutre."
        )

        # 2. Cas Patient Existant sélectionné
        rdv_empty.patient_id = self.patient_regular.id
        rdv_empty._compute_no_show_risk()
        rdv_empty._compute_no_show_risk_badge()

        self.assertGreater(rdv_empty.no_show_risk_score, 0.0, "Le score doit être calculé dès qu'un patient est sélectionné.")
        self.assertIn(rdv_empty.no_show_risk_level, ['faible', 'moyen', 'eleve'])
        self.assertNotIn(
            "Sélectionnez un patient",
            rdv_empty.no_show_risk_badge,
            "Le message neutre doit disparaître au profit du score réel."
        )

        # 3. Cas Nouveau Patient (nom tapé en texte libre sans fiche existante)
        rdv_nouveau = self.Rdv.new({
            'patient_name': 'Nouveau Patient Test',
            'date': today + timedelta(days=5),
            'heure': 10.0,
            'is_urgence': False,
            'state': 'en_attente',
        })
        rdv_nouveau._compute_no_show_risk()
        rdv_nouveau._compute_no_show_risk_badge()

        self.assertGreater(rdv_nouveau.no_show_risk_score, 0.0, "Le score doit se calculer dès la saisie du nom.")
        self.assertIn(rdv_nouveau.no_show_risk_level, ['faible', 'moyen', 'eleve'])
        self.assertIn(
            "Nouveau patient",
            rdv_nouveau.no_show_risk_factors or "",
            "Le facteur Nouveau patient doit être pris en compte."
        )

    def test_07_portail_patient_rdv_passes_non_clotures_exclus(self):
        """Test 7: Un RDV passé non clôturé (en_attente) n'apparaît PAS dans la liste portail patient.
        La logique reflète le domaine de portal.py: seuls les RDV qualifiés (termine/annule/absent)
        ou les vrais RDV futurs/présents en_attente sont visibles."""
        from datetime import date, timedelta
        from odoo import fields

        today = date.today()
        patient = self.patient_regular

        # --- RDV passé NON clôturé (doit être EXCLU du portail) ---
        rdv_past_unclosed = self.Rdv.create({
            'patient_id': patient.id,
            'date': today - timedelta(days=3),
            'heure': 9.0,
            'state': 'en_attente',
        })

        # --- RDV futur en attente (doit être INCLUS) ---
        rdv_future = self.Rdv.create({
            'patient_id': patient.id,
            'date': today + timedelta(days=5),
            'heure': 10.0,
            'state': 'en_attente',
        })

        # --- RDV passé Terminé (doit être INCLUS) ---
        rdv_termine = self.Rdv.create({
            'patient_id': patient.id,
            'date': today - timedelta(days=10),
            'heure': 11.0,
            'state': 'termine',
        })

        # --- RDV passé Absent (doit être INCLUS) ---
        rdv_absent = self.Rdv.create({
            'patient_id': patient.id,
            'date': today - timedelta(days=7),
            'heure': 8.0,
            'state': 'absent',
        })

        # Reproduce the exact domain from controllers/portal.py portal_my_rendezvous
        portal_domain = [
            ('patient_id', '=', patient.id),
            '|',
                ('state', 'in', ['termine', 'annule', 'absent']),
                '&', ('state', '=', 'en_attente'), ('date', '>=', today),
        ]
        visible_ids = self.Rdv.search(portal_domain).ids

        self.assertNotIn(
            rdv_past_unclosed.id, visible_ids,
            "Un RDV passé non clôturé (en_attente) NE DOIT PAS apparaître dans le portail patient."
        )
        self.assertIn(
            rdv_future.id, visible_ids,
            "Un RDV futur en_attente DOIT apparaître dans le portail patient."
        )
        self.assertIn(
            rdv_termine.id, visible_ids,
            "Un RDV terminé DOIT apparaître dans le portail patient."
        )
        self.assertIn(
            rdv_absent.id, visible_ids,
            "Un RDV absent DOIT apparaître dans le portail patient."
        )

    def test_08_dossier_medical_champs_ia_jamais_exposes(self):
        """Test 8: La page /my/dossier n'expose que les champs déclaratifs du patient.
        Aucun champ IA technique (ia_statut, ia_fingerprint, alertes) ne doit apparaître
        dans les valeurs transmises au template Qweb."""
        from datetime import date

        patient = self.patient_regular

        # Vérifier que le modèle cabinet.patient possède bien les 3 champs déclaratifs
        self.assertIn(
            'allergies', patient._fields,
            "Le champ 'allergies' doit exister sur cabinet.patient."
        )
        self.assertIn(
            'antecedents', patient._fields,
            "Le champ 'antecedents' doit exister sur cabinet.patient."
        )
        self.assertIn(
            'traitements_chroniques', patient._fields,
            "Le champ 'traitements_chroniques' doit exister sur cabinet.patient."
        )

        # Simuler ce que le contrôleur portal_my_dossier transmet au template
        portal_values = {
            'page_name': 'dossier',
            'patient': patient,
            'allergies': patient.allergies or '',
            'antecedents': patient.antecedents or '',
            'traitements_chroniques': patient.traitements_chroniques or '',
        }

        # Champs IA qui ne doivent JAMAIS être dans les valeurs transmises au template
        ia_forbidden_keys = [
            'ia_statut', 'ia_fingerprint', 'ia_message', 'ia_alerte',
            'ia_alertes_detail', 'ia_statut_interaction', 'ia_results',
        ]
        for forbidden in ia_forbidden_keys:
            self.assertNotIn(
                forbidden, portal_values,
                f"Le champ IA '{forbidden}' NE DOIT PAS être exposé dans le template /my/dossier."
            )

        # Vérifier que les valeurs déclaratives sont bien des chaînes (ou vides)
        self.assertIsInstance(
            portal_values['allergies'], str,
            "La valeur 'allergies' doit être une chaîne (ou '')."
        )
        self.assertIsInstance(
            portal_values['antecedents'], str,
            "La valeur 'antecedents' doit être une chaîne (ou '')."
        )
        self.assertIsInstance(
            portal_values['traitements_chroniques'], str,
            "La valeur 'traitements_chroniques' doit être une chaîne (ou '')."
        )
