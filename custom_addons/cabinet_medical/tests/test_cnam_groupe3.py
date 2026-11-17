# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'cabinet_cnam')
class TestCnamGroupe3(TransactionCase):
    """Tests d'intégration Groupe 3 : Moteur de facturation CNAM / APCI / Mutuelle / Dépassement."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Patient = cls.env['cabinet.patient']
        cls.Consultation = cls.env['cabinet.consultation']
        cls.Acte = cls.env['cabinet.acte']
        cls.ActeParam = cls.env['cabinet.acte.parametrage']
        cls.Facture = cls.env['cabinet.facture']
        cls.Assurance = cls.env['cabinet.assurance']

        cls.param_c70 = cls.ActeParam.create({
            'name': 'Consultation C 70%',
            'type_acte': 'consultation',
            'tarif': 35.0,
        })
        cls.param_tech80 = cls.ActeParam.create({
            'name': 'Acte technique 80%',
            'type_acte': 'acte_technique',
            'tarif': 100.0,
        })
        cls.param_ap = cls.ActeParam.create({
            'name': 'Acte lourd AP 80%',
            'type_acte': 'acte_technique',
            'tarif': 100.0,
            'necessite_accord_prealable': True,
        })

    def _make_facture(self, patient, actes_vals, is_consultation_apci=False,
                      motif='Consultation médicale standard',
                      couverture_depassement_mutuelle=False):
        consult = self.Consultation.create({
            'patient_id': patient.id,
            'motif': motif,
            'is_consultation_apci': is_consultation_apci,
        })
        for vals in actes_vals:
            v = dict(vals)
            v['consultation_id'] = consult.id
            self.Acte.create(v)
        return self.Facture.create({
            'patient_id': patient.id,
            'consultation_id': consult.id,
            'couverture_depassement_mutuelle': couverture_depassement_mutuelle,
        })

    def test_01_honoraires_egaux_tcr_sans_depassement(self):
        """Test A : Honoraires = TCR -> aucun dépassement d'honoraires."""
        p = self.Patient.create({
            'name': 'Patient Test A',
            'cin': '99002001',
            'is_cnam': True,
            'numero_cnam': '1000000001',
            'filiere_cnam': 'privee',
        })
        f = self._make_facture(p, [{
            'parametrage_id': self.param_c70.id,
            'type_acte': 'consultation',
            'description': 'Consultation C',
            'montant': 35.0,
            'tarif_conventionnel': 35.0,
        }])
        self.assertAlmostEqual(f.montant_total, 35.0, places=2)
        self.assertAlmostEqual(f.montant_conventionnel_total, 35.0, places=2)
        self.assertAlmostEqual(f.depassement_total, 0.0, places=2)
        self.assertAlmostEqual(f.part_cnam_display, 24.5, places=2)
        self.assertAlmostEqual(f.ticket_moderateur_total, 10.5, places=2)

    def test_02_honoraires_superieurs_tcr_depassement_isole(self):
        """Test B : Honoraires > TCR -> CNAM calcule sur TCR, dépassement à la charge du patient."""
        p = self.Patient.create({
            'name': 'Patient Test B',
            'cin': '99002002',
            'is_cnam': True,
            'numero_cnam': '1000000002',
            'filiere_cnam': 'privee',
        })
        f = self._make_facture(p, [{
            'parametrage_id': self.param_c70.id,
            'type_acte': 'consultation',
            'description': 'Consultation avec dépassement',
            'montant': 60.0,
            'tarif_conventionnel': 35.0,
        }])
        self.assertAlmostEqual(f.montant_total, 60.0, places=2)
        self.assertAlmostEqual(f.montant_conventionnel_total, 35.0, places=2)
        self.assertAlmostEqual(f.depassement_total, 25.0, places=2)
        self.assertAlmostEqual(f.part_cnam_display, 24.5, places=2)
        self.assertAlmostEqual(f.ticket_moderateur_total, 10.5, places=2)
        self.assertAlmostEqual(f.montant_paye_cabinet, 35.5, places=2)
        self.assertAlmostEqual(f.reste_a_charge_final, 35.5, places=2)

    def test_03_tiers_payant_repartition(self):
        """Test C : Tiers-payant -> part CNAM = créance cabinet, patient = ticket + dépassement."""
        p = self.Patient.create({
            'name': 'Patient Test C',
            'cin': '99002003',
            'is_cnam': True,
            'numero_cnam': '1000000003',
            'filiere_cnam': 'privee',
        })
        f = self._make_facture(p, [{
            'parametrage_id': self.param_tech80.id,
            'type_acte': 'acte_technique',
            'description': 'Acte technique 80%',
            'montant': 100.0,
            'tarif_conventionnel': 100.0,
        }])
        self.assertEqual(f.scenario, 'cnam_tiers_payant')
        self.assertAlmostEqual(f.montant_cnam_cabinet, 80.0, places=2)
        self.assertAlmostEqual(f.montant_paye_cabinet, 20.0, places=2)
        self.assertAlmostEqual(f.reste_a_charge_final, 20.0, places=2)

    def test_04_remboursement_repartition(self):
        """Test D : Remboursement -> patient paie 100% au cabinet, part CNAM cabinet = 0."""
        p = self.Patient.create({
            'name': 'Patient Test D',
            'cin': '99002004',
            'is_cnam': True,
            'numero_cnam': '1000000004',
            'filiere_cnam': 'remboursement',
        })
        f = self._make_facture(p, [{
            'parametrage_id': self.param_tech80.id,
            'type_acte': 'acte_technique',
            'description': 'Acte technique remboursement',
            'montant': 100.0,
            'tarif_conventionnel': 100.0,
        }])
        self.assertEqual(f.scenario, 'cnam_remboursement')
        self.assertAlmostEqual(f.montant_cnam_cabinet, 0.0, places=2)
        self.assertAlmostEqual(f.montant_paye_cabinet, 100.0, places=2)
        self.assertAlmostEqual(f.part_cnam_display, 80.0, places=2)
        self.assertAlmostEqual(f.reste_a_charge_final, 20.0, places=2)

    def test_05_apci_liee_exoneree_100(self):
        """Test E : APCI liée -> exonération totale à 100% de la part conventionnelle."""
        today = date.today()
        p = self.Patient.create({
            'name': 'Patient Test E',
            'cin': '99002005',
            'is_cnam': True,
            'numero_cnam': '1000000005',
            'filiere_cnam': 'privee',
            'is_apci': True,
            'numero_decision_apci': 'APCI-G3-05',
            'date_fin_apci': today + timedelta(days=90),
        })
        f = self._make_facture(
            p,
            [{
                'parametrage_id': self.param_c70.id,
                'type_acte': 'consultation',
                'description': 'Consultation APCI',
                'montant': 35.0,
                'tarif_conventionnel': 35.0,
                'is_acte_apci': True,
            }],
            is_consultation_apci=True,
        )
        self.assertEqual(f.scenario, 'apci_tiers_payant')
        self.assertAlmostEqual(f.montant_cnam_cabinet, 35.0, places=2)
        self.assertAlmostEqual(f.montant_paye_cabinet, 0.0, places=2)
        self.assertAlmostEqual(f.ticket_moderateur_total, 0.0, places=2)
        self.assertAlmostEqual(f.reste_a_charge_final, 0.0, places=2)

    def test_06_apci_non_liee_taux_droit_commun(self):
        """Test F : APCI non liée -> taux de droit commun (non 100% d'office)."""
        today = date.today()
        p = self.Patient.create({
            'name': 'Patient Test F',
            'cin': '99002006',
            'is_cnam': True,
            'numero_cnam': '1000000006',
            'filiere_cnam': 'privee',
            'is_apci': True,
            'numero_decision_apci': 'APCI-G3-06',
            'date_fin_apci': today + timedelta(days=90),
        })
        f = self._make_facture(
            p,
            [{
                'parametrage_id': self.param_c70.id,
                'type_acte': 'consultation',
                'description': 'Consultation non_apci courante',
                'montant': 35.0,
                'tarif_conventionnel': 35.0,
                'is_acte_apci': False,
            }],
            is_consultation_apci=False,
            motif='Pathologie aiguë non_apci',
        )
        self.assertAlmostEqual(f.montant_cnam_cabinet, 24.5, places=2)
        self.assertAlmostEqual(f.montant_paye_cabinet, 10.5, places=2)
        self.assertAlmostEqual(f.ticket_moderateur_total, 10.5, places=2)

    def test_07_mutuelle_sur_ticket_sans_depassement_automatique(self):
        """Test G : Mutuelle sur ticket modérateur sans imputer le dépassement par défaut."""
        assur = self.Assurance.create({
            'name': 'Mutuelle Test G3 80%',
            'taux': 80.0,
            'tiers_payant_direct': False,
        })
        p = self.Patient.create({
            'name': 'Patient Test G',
            'cin': '99002007',
            'is_cnam': True,
            'numero_cnam': '1000000007',
            'filiere_cnam': 'privee',
            'has_assurance': True,
            'assurance_id': assur.id,
        })
        f = self._make_facture(p, [{
            'parametrage_id': self.param_c70.id,
            'type_acte': 'consultation',
            'description': 'Consultation C + dépassement',
            'montant': 60.0,
            'tarif_conventionnel': 35.0,
        }], couverture_depassement_mutuelle=False)

        self.assertEqual(f.scenario, 'cnam_tp_assur')
        self.assertAlmostEqual(f.montant_cnam_cabinet, 24.5, places=2)
        self.assertAlmostEqual(f.part_assurance_display, 8.4, places=2)  # 80% de 10.5
        self.assertAlmostEqual(f.montant_paye_cabinet, 35.5, places=2)
        self.assertAlmostEqual(f.reste_a_charge_final, 27.1, places=2)  # 2.1 + 25.0

    def test_08_accord_prealable_coherence(self):
        """Test H : Accord préalable demandé/refusé n'ouvre pas droit au tiers-payant CNAM."""
        p = self.Patient.create({
            'name': 'Patient Test H',
            'cin': '99002008',
            'is_cnam': True,
            'numero_cnam': '1000000008',
            'filiere_cnam': 'privee',
        })
        f = self._make_facture(p, [{
            'parametrage_id': self.param_ap.id,
            'type_acte': 'acte_technique',
            'description': 'Acte AP en attente',
            'montant': 100.0,
            'tarif_conventionnel': 100.0,
            'statut_accord_prealable': 'demande',
        }])
        self.assertAlmostEqual(f.montant_cnam_cabinet, 0.0, places=2)
        self.assertAlmostEqual(f.montant_paye_cabinet, 100.0, places=2)

    def test_09_scenario_9_depassement_tiers_payant(self):
        """Scénario 9 : Consultation 60 DT (TCR 35 DT) en Tiers-Payant -> CNAM 24.50, Patient 35.50."""
        p = self.Patient.create({
            'name': 'Patient Test 9',
            'cin': '99002009',
            'is_cnam': True,
            'numero_cnam': '1000000009',
            'filiere_cnam': 'privee',
        })
        f = self._make_facture(p, [{
            'parametrage_id': self.param_c70.id,
            'type_acte': 'consultation',
            'description': 'Consultation spécialiste avec dépassement',
            'montant': 60.0,
            'tarif_conventionnel': 35.0,
        }])
        self.assertAlmostEqual(f.montant_conventionnel_total, 35.0, places=2)
        self.assertAlmostEqual(f.depassement_total, 25.0, places=2)
        self.assertAlmostEqual(f.montant_cnam_cabinet, 24.5, places=2)
        self.assertAlmostEqual(f.montant_paye_cabinet, 35.5, places=2)
        self.assertAlmostEqual(f.reste_a_charge_final, 35.5, places=2)

    def test_10_scenario_10_seance_mixte_apci(self):
        """Scénario 10 : Séance mixte (1 acte APCI 35 DT à 100% + 1 acte non-APCI 50 DT à 70%)."""
        today = date.today()
        p = self.Patient.create({
            'name': 'Patient Test 10',
            'cin': '99002010',
            'is_cnam': True,
            'numero_cnam': '1000000010',
            'filiere_cnam': 'privee',
            'is_apci': True,
            'numero_decision_apci': 'APCI-G3-10',
            'date_fin_apci': today + timedelta(days=90),
        })
        f = self._make_facture(
            p,
            [
                {
                    'parametrage_id': self.param_c70.id,
                    'type_acte': 'consultation',
                    'description': 'Acte APCI suivi',
                    'montant': 35.0,
                    'tarif_conventionnel': 35.0,
                    'is_acte_apci': True,
                },
                {
                    'parametrage_id': self.param_c70.id,
                    'type_acte': 'consultation',
                    'description': 'Acte non-APCI',
                    'montant': 50.0,
                    'tarif_conventionnel': 50.0,
                    'is_acte_apci': False,
                },
            ],
            is_consultation_apci=True,
        )
        self.assertAlmostEqual(f.montant_total, 85.0, places=2)
        self.assertAlmostEqual(f.montant_cnam_cabinet, 70.0, places=2)  # 35 + 35
        self.assertAlmostEqual(f.montant_paye_cabinet, 15.0, places=2)
        self.assertAlmostEqual(f.ticket_moderateur_total, 15.0, places=2)

    def test_11_scenario_11_depassement_mutuelle(self):
        """Scénario 11 : Dépassement + Mutuelle avec couverture explicite du dépassement."""
        assur = self.Assurance.create({
            'name': 'Mutuelle Couverture Dépassement 80%',
            'taux': 80.0,
            'tiers_payant_direct': False,
        })
        p = self.Patient.create({
            'name': 'Patient Test 11',
            'cin': '99002011',
            'is_cnam': True,
            'numero_cnam': '1000000011',
            'filiere_cnam': 'privee',
            'has_assurance': True,
            'assurance_id': assur.id,
        })
        f = self._make_facture(p, [{
            'parametrage_id': self.param_c70.id,
            'type_acte': 'consultation',
            'description': 'Consultation avec couverture dépassement',
            'montant': 60.0,
            'tarif_conventionnel': 35.0,
        }], couverture_depassement_mutuelle=True)

        self.assertAlmostEqual(f.montant_cnam_cabinet, 24.5, places=2)
        self.assertAlmostEqual(f.part_assurance_display, 28.4, places=2)  # 8.4 + 20.0
        self.assertAlmostEqual(f.reste_a_charge_final, 7.1, places=2)
