# -*- coding: utf-8 -*-
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
import requests
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'cabinet_dashboard_ai')
class TestDashboardAI(TransactionCase):
    """Tests d'intégration du Dashboard IA (models/dashboard_ai.py)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DashboardAI = cls.env['cabinet.dashboard.ai']
        cls.Patient = cls.env['cabinet.patient']
        cls.Consultation = cls.env['cabinet.consultation']
        cls.Acte = cls.env['cabinet.acte']
        cls.Facture = cls.env['cabinet.facture']
        cls.Prescription = cls.env['cabinet.prescription']
        cls.ConfigParam = cls.env['ir.config_parameter'].sudo()

        group_med = cls.env.ref('cabinet_medical.group_medecin')
        group_sec = cls.env.ref('cabinet_medical.group_secretaire')
        cls.user_medecin = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Dr. Dashboard AI',
            'login': 'dr_dash_ai@cabinet.local',
            'email': 'dr_dash_ai@cabinet.local',
            'groups_id': [(6, 0, [group_med.id])],
        })
        cls.user_secretaire = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Secrétaire Dashboard AI',
            'login': 'sec_dash_ai@cabinet.local',
            'email': 'sec_dash_ai@cabinet.local',
            'groups_id': [(6, 0, [group_sec.id])],
        })

        cls.patient = cls.Patient.create({
            'name': 'Patient Dashboard AI',
            'cin': '77440001',
            'telephone': '22440001',
            'allergies': 'Pénicilline',
            'is_cnam': True,
            'numero_cnam': '4000000001',
            'filiere_cnam': 'privee',
            'date_validite_cnam': date.today() + timedelta(days=90),
        })
        cls.consult = cls.Consultation.create({
            'patient_id': cls.patient.id,
            'motif': 'Consultation pour test Dashboard IA',
        })
        cls.Acte.create({
            'consultation_id': cls.consult.id,
            'type_acte': 'consultation',
            'description': 'Consultation Dashboard',
            'montant': 50.0,
            'tarif_conventionnel': 35.0,
        })
        cls.facture = cls.Facture.create({
            'patient_id': cls.patient.id,
            'consultation_id': cls.consult.id,
        })
        cls.facture.action_valider()

        cls.ordo = cls.Prescription.create({
            'consultation_id': cls.consult.id,
            'ia_statut': 'allergy_risk',
            'ia_message': 'Alerte critique 100% allergie pénicilline',
            'ordonnance_line_ids': [(0, 0, {
                'medicament': 'Amoxicilline',
                'dosage': '1g',
                'posologie': '1 comprimé matin et soir',
            })],
        })

    def test_01_collect_base_and_medical_metrics(self):
        """Vérifie _collect_base_metrics, _collect_medical_metrics et _prepare_chart_data."""
        today = date.today()
        first_day_month = today.replace(day=1)
        first_day_last_month = (first_day_month - timedelta(days=1)).replace(day=1)
        last_day_last_month = first_day_month - timedelta(days=1)

        base = self.DashboardAI._collect_base_metrics(
            today, first_day_month, first_day_last_month, last_day_last_month
        )
        self.assertGreaterEqual(base['consults_ce_mois'], 1)
        self.assertGreaterEqual(base['nb_factures_impayees'], 1)
        self.assertGreater(base['impayes_patients'], 0.0)
        self.assertEqual(len(base['us35_labels']), 6)
        self.assertEqual(len(base['us36_data']), 4)
        self.assertEqual(len(base['us39_data']), 3)

        med = self.DashboardAI._collect_medical_metrics(first_day_month)
        self.assertGreaterEqual(med['nb_alertes_allergies'], 1)
        self.assertGreaterEqual(med['nb_alertes_critiques'], 1)
        self.assertGreaterEqual(med['patients_allergiques'], 1)
        self.assertIn('Amoxicilline', med['top_medicaments'])

    def test_02_collect_secretaire_metrics(self):
        """Vérifie _collect_secretaire_metrics et le rendu HTML secrétariat."""
        today = date.today()
        first_day_month = today.replace(day=1)
        first_day_last_month = (first_day_month - timedelta(days=1)).replace(day=1)
        last_day_last_month = first_day_month - timedelta(days=1)

        sec = self.DashboardAI._collect_secretaire_metrics(
            today, first_day_month, first_day_last_month, last_day_last_month
        )
        self.assertFalse(sec['isMedecin'])
        for key in (
            'consults_semaine', 'impayes_montant', 'taux_cnam',
            'patients_crees_mois', 'rdv_confirmes', 'rdv_annules',
            'montant_encaisse_mois', 'dossiers_incomplets_count',
            'rdvs_today', '_insights_html',
        ):
            self.assertIn(key, sec)

    def test_03_calculate_health_index_and_detect_anomalies(self):
        """Vérifie _calculate_health_index et _detect_anomalies."""
        metrics_sain = {
            'tendance_consults': 5,
            'nb_factures_impayees': 0,
            'nb_alertes_critiques': 0,
            'nb_alertes_allergies': 0,
        }
        self.DashboardAI._calculate_health_index(metrics_sain)
        self.DashboardAI._detect_anomalies(metrics_sain)
        self.assertEqual(metrics_sain['health_score'], 100)
        self.assertIn('Aucune anomalie critique', metrics_sain['ai_anomalies'])

        metrics_critique = {
            'tendance_consults': -10,
            'nb_factures_impayees': 6,
            'nb_alertes_critiques': 3,
            'nb_alertes_allergies': 7,
        }
        self.DashboardAI._calculate_health_index(metrics_critique)
        self.DashboardAI._detect_anomalies(metrics_critique)
        # Pénalités : 20 (tendance) + 30 (impayés) + 10 (critiques) = 60 -> score 40
        self.assertEqual(metrics_critique['health_score'], 40)
        self.assertIn('Chute de 10 consultations', metrics_critique['ai_anomalies'])
        self.assertIn("Pic d'alertes allergies", metrics_critique['ai_anomalies'])
        self.assertIn('Hausse des impayés', metrics_critique['ai_anomalies'])

    def test_04_clean_ai_text(self):
        """Vérifie _clean_ai_text (suppression markdown et troncature sur phrase complète)."""
        raw = "# Titre ignoré\n**Résumé :**\n- Première phrase complète.\nDeuxième phrase tronquée"
        cleaned = self.DashboardAI._clean_ai_text(raw, truncated=True)
        self.assertNotIn('#', cleaned)
        self.assertNotIn('**', cleaned)
        self.assertEqual(cleaned, 'Première phrase complète.')

        self.assertEqual(self.DashboardAI._clean_ai_text(''), '')

    def test_05_generate_ai_analysis_ollama_success_and_cache_hit(self):
        """Vérifie _generate_ai_analysis avec réponse Ollama mockée puis réutilisation via get_ai_insights."""
        self.ConfigParam.set_param('cabinet_medical.ai_generation_lock', '0')
        self.ConfigParam.set_param('cabinet_medical.ai_analysis_hash', '')
        self.ConfigParam.set_param('cabinet_medical.ai_analysis_text', '')

        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {
            'response': (
                'Le cabinet maintient une activité régulière ce mois. '
                'Une alerte allergie a été interceptée avec succès.\n'
                'Recommandations :\n'
                '1. Relancer les factures impayées.'
            ),
            'done_reason': 'stop',
            'eval_count': 42,
        }

        with patch('requests.post', return_value=fake_resp):
            res = self.DashboardAI.with_user(self.user_medecin)._generate_ai_analysis()

        self.assertEqual(res['status'], 'success')
        self.assertEqual(self.ConfigParam.get_param('cabinet_medical.ai_generation_lock'), '0')

        # get_ai_insights en médecin doit maintenant utiliser le texte Ollama stocké
        insights = self.DashboardAI.with_user(self.user_medecin).get_ai_insights()
        self.assertFalse(insights['stats']['is_fallback'])
        self.assertIn('Analyse générée par Ollama', insights['html'])

        # Un second appel avec les mêmes métriques est ignoré (hash inchangé)
        res_skip = self.DashboardAI.with_user(self.user_medecin)._generate_ai_analysis()
        self.assertEqual(res_skip['status'], 'skipped')

    def test_06_ollama_unavailable_fallback_and_secretaire_view(self):
        """Vérifie le comportement lorsque Ollama est indisponible et le fallback local."""
        self.ConfigParam.set_param('cabinet_medical.ai_generation_lock', '0')
        self.ConfigParam.set_param('cabinet_medical.ai_analysis_hash', 'stale_hash')
        self.ConfigParam.set_param('cabinet_medical.ai_analysis_text', '')

        with patch('requests.post', side_effect=requests.exceptions.ConnectionError('Ollama offline')):
            res = self.DashboardAI.with_user(self.user_medecin)._generate_ai_analysis()

        self.assertEqual(res['status'], 'error')
        self.assertEqual(self.ConfigParam.get_param('cabinet_medical.ai_generation_lock'), '0')

        # Le dashboard médecin bascule proprement sur _generate_local_fallback
        insights_med = self.DashboardAI.with_user(self.user_medecin).get_ai_insights()
        self.assertTrue(insights_med['stats']['is_fallback'])
        self.assertIn('Analyse locale', insights_med['html'])

        # Le dashboard secrétaire fonctionne sans Ollama
        insights_sec = self.DashboardAI.with_user(self.user_secretaire).get_ai_insights()
        self.assertFalse(insights_sec['stats']['is_fallback'])
        self.assertIn('Agenda du jour', insights_sec['html'])

