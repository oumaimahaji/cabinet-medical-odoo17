# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'cabinet_cnam')
class TestCnamGroupe2(TransactionCase):
    """Tests d'intégration Groupe 2 : Bénéficiaires, APCI ciblée, Dépassement et Accord Préalable."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Patient = cls.env['cabinet.patient']
        cls.Consultation = cls.env['cabinet.consultation']
        cls.Acte = cls.env['cabinet.acte']
        cls.ActeParam = cls.env['cabinet.acte.parametrage']

    def test_01_patient_beneficiaire_06_et_filiere_publique(self):
        """Vérifie le support du code ayant droit 06 (ascendant) et de la filière publique."""
        patient = self.Patient.create({
            'name': 'M. Salah Ben Amor (Père à charge)',
            'cin': '77881122',
            'telephone': '22112233',
            'is_cnam': True,
            'numero_cnam': '1234567890',
            'code_beneficiaire_cnam': '06',
            'filiere_cnam': 'publique',
        })
        self.assertEqual(patient.code_beneficiaire_cnam, '06')
        self.assertEqual(patient.filiere_cnam, 'publique')

    def test_02_consultation_apci_coherence_and_validation(self):
        """Vérifie le comportement réel de la consultation ciblée APCI (Décret 2005-1367 art. 19)."""
        today = date.today()

        # 1. Patient non-APCI : onchange remet is_consultation_apci à False et avertit
        patient_sain = self.Patient.create({
            'name': 'Patient Non APCI G2',
            'cin': '77881123',
            'is_apci': False,
        })
        consult_tmp = self.Consultation.new({
            'patient_id': patient_sain.id,
            'motif': 'Consultation standard de contrôle',
            'is_consultation_apci': True,
        })
        res = consult_tmp._onchange_is_consultation_apci()
        self.assertFalse(consult_tmp.is_consultation_apci)
        self.assertIsInstance(res, dict)
        self.assertIn('warning', res)

        # Création forcée en base avec is_consultation_apci=True -> ValidationError
        with self.assertRaises(ValidationError):
            self.Consultation.create({
                'patient_id': patient_sain.id,
                'motif': 'Tentative APCI non autorisée',
                'is_consultation_apci': True,
            })

        # 2. Patient APCI valide -> création réussie
        patient_apci = self.Patient.create({
            'name': 'Patient Diabétique APCI G2',
            'cin': '77881124',
            'is_cnam': True,
            'numero_cnam': '2234567890',
            'filiere_cnam': 'privee',
            'date_validite_cnam': today + timedelta(days=180),
            'is_apci': True,
            'numero_decision_apci': 'APCI-2026-004',
            'date_fin_apci': today + timedelta(days=180),
        })
        consult_valide = self.Consultation.create({
            'patient_id': patient_apci.id,
            'motif': 'Suivi diabète APCI trimestriel',
            'is_consultation_apci': True,
            'date_consultation': datetime.now(),
        })
        self.assertTrue(consult_valide.is_consultation_apci)

        # 3. Patient APCI expiré -> ValidationError
        patient_expire = self.Patient.create({
            'name': 'Patient APCI Expiré G2',
            'cin': '77881125',
            'is_cnam': True,
            'numero_cnam': '3234567890',
            'is_apci': True,
            'numero_decision_apci': 'APCI-2024-001',
            'date_fin_apci': today - timedelta(days=10),
        })
        with self.assertRaises(ValidationError):
            self.Consultation.create({
                'patient_id': patient_expire.id,
                'motif': 'Suivi APCI avec décision expirée',
                'is_consultation_apci': True,
                'date_consultation': datetime.now(),
            })

    def test_03_acte_tarif_conventionnel_et_depassement(self):
        """Vérifie le calcul réel de depassement_honoraire sur cabinet.acte."""
        patient = self.Patient.create({
            'name': 'Patient Dépassement G2',
            'cin': '77881126',
            'is_cnam': True,
            'numero_cnam': '4234567890',
            'filiere_cnam': 'privee',
        })
        consult = self.Consultation.create({
            'patient_id': patient.id,
            'motif': 'Consultation avec actes multiples',
        })

        # Acte 1 : sans dépassement
        acte1 = self.Acte.create({
            'consultation_id': consult.id,
            'type_acte': 'consultation',
            'description': 'Consultation conventionnée',
            'montant': 35.0,
            'tarif_conventionnel': 35.0,
        })
        self.assertAlmostEqual(acte1.depassement_honoraire, 0.0, places=2)

        # Acte 2 : avec dépassement (60 - 35 = 25)
        acte2 = self.Acte.create({
            'consultation_id': consult.id,
            'type_acte': 'consultation',
            'description': 'Consultation avec dépassement',
            'montant': 60.0,
            'tarif_conventionnel': 35.0,
        })
        self.assertAlmostEqual(acte2.depassement_honoraire, 25.0, places=2)

        # Acte 3 : sans tarif conventionnel -> dépassement = 0
        acte3 = self.Acte.create({
            'consultation_id': consult.id,
            'type_acte': 'autre',
            'description': 'Acte hors nomenclature',
            'montant': 40.0,
            'tarif_conventionnel': 0.0,
        })
        self.assertAlmostEqual(acte3.depassement_honoraire, 0.0, places=2)

    def test_04_acte_accord_prealable_validation(self):
        """Vérifie le contrôle réel d'accord préalable obligatoire (Convention art. 22)."""
        param_lourd = self.ActeParam.create({
            'name': 'Acte lourd sous AP',
            'type_acte': 'acte_technique',
            'tarif': 120.0,
            'necessite_accord_prealable': True,
        })
        patient_tp = self.Patient.create({
            'name': 'Patient Tiers-Payant AP G2',
            'cin': '77881127',
            'is_cnam': True,
            'numero_cnam': '5234567890',
            'filiere_cnam': 'privee',
        })
        consult = self.Consultation.create({
            'patient_id': patient_tp.id,
            'motif': 'Acte nécessitant accord préalable',
        })

        acte_non_accorde = self.Acte.create({
            'consultation_id': consult.id,
            'parametrage_id': param_lourd.id,
            'type_acte': 'acte_technique',
            'description': 'Acte lourd sans AP',
            'montant': 120.0,
            'tarif_conventionnel': 120.0,
            'statut_accord_prealable': 'demande',
            'numero_accord_prealable': False,
        })
        with self.assertRaises(ValidationError):
            acte_non_accorde.action_valider()

        acte_non_accorde.write({
            'statut_accord_prealable': 'accorde',
            'numero_accord_prealable': 'AP-2026-TUN-0089',
        })
        acte_non_accorde.action_valider()
        self.assertEqual(acte_non_accorde.state, 'done')

    def test_05_preservation_baseline_calcul_actes(self):
        """Vérifie le calcul réel de total_acte_dt sur cabinet.acte."""
        today = date.today()
        param_c = self.ActeParam.create({
            'name': 'Consultation C G2',
            'type_acte': 'consultation',
            'tarif': 35.0,
        })

        # A. Tiers-payant 35 DT @ 70% -> patient paie 10.5 DT
        patient_tp = self.Patient.create({
            'name': 'Patient TP G2',
            'cin': '77881128',
            'is_cnam': True,
            'numero_cnam': '6234567890',
            'filiere_cnam': 'privee',
        })
        consult_tp = self.Consultation.create({
            'patient_id': patient_tp.id,
            'motif': 'Consultation TP standard',
        })
        acte_tp = self.Acte.create({
            'consultation_id': consult_tp.id,
            'parametrage_id': param_c.id,
            'type_acte': 'consultation',
            'description': 'Consultation TP',
            'montant': 35.0,
            'tarif_conventionnel': 35.0,
        })
        self.assertAlmostEqual(acte_tp.total_acte_dt, 10.5, places=2)

        # B. APCI Tiers-payant -> patient paie 0 DT
        patient_apci = self.Patient.create({
            'name': 'Patient APCI G2',
            'cin': '77881129',
            'is_cnam': True,
            'numero_cnam': '7234567890',
            'filiere_cnam': 'privee',
            'is_apci': True,
            'numero_decision_apci': 'APCI-G2-05',
            'date_fin_apci': today + timedelta(days=90),
        })
        consult_apci = self.Consultation.create({
            'patient_id': patient_apci.id,
            'motif': 'Consultation APCI exonérée',
            'is_consultation_apci': True,
        })
        acte_apci = self.Acte.create({
            'consultation_id': consult_apci.id,
            'parametrage_id': param_c.id,
            'type_acte': 'consultation',
            'description': 'Acte APCI',
            'montant': 55.0,
            'tarif_conventionnel': 55.0,
            'is_acte_apci': True,
        })
        self.assertAlmostEqual(acte_apci.total_acte_dt, 0.0, places=2)

        # C. Remboursement classique -> patient avance 55 DT
        patient_remb = self.Patient.create({
            'name': 'Patient Remb G2',
            'cin': '77881130',
            'is_cnam': True,
            'numero_cnam': '8234567890',
            'filiere_cnam': 'remboursement',
        })
        consult_remb = self.Consultation.create({
            'patient_id': patient_remb.id,
            'motif': 'Consultation remboursement',
        })
        acte_remb = self.Acte.create({
            'consultation_id': consult_remb.id,
            'parametrage_id': param_c.id,
            'type_acte': 'consultation',
            'description': 'Acte remboursement',
            'montant': 55.0,
            'tarif_conventionnel': 55.0,
        })
        self.assertAlmostEqual(acte_remb.total_acte_dt, 55.0, places=2)
