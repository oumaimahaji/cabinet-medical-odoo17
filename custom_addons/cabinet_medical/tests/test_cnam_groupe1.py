# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'cabinet_cnam')
class TestCnamGroupe1(TransactionCase):
    """Tests d'intégration Groupe 1 : Référentiel des actes NGAP et Convention Médecin."""

    def test_01_res_company_medecin_convention(self):
        """Vérifie la spécialité du médecin et son statut conventionné sur res.company."""
        company = self.env.company
        company.write({
            'medecin_nom': 'Dr. Oumaima Hajji',
            'medecin_inpe': '12345678',
            'medecin_code_convention': 'CONV-2025-01',
            'medecin_specialite': 'generaliste',
            'medecin_conventionne': True,
        })
        self.assertEqual(company.medecin_specialite, 'generaliste')
        self.assertTrue(company.medecin_conventionne)
        self.assertEqual(company.medecin_code_convention, 'CONV-2025-01')

        company.write({'medecin_specialite': 'specialiste'})
        self.assertEqual(company.medecin_specialite, 'specialiste')

    def test_02_acte_parametrage_ngap_fields(self):
        """Vérifie les attributs NGAP (lettre-clé, coefficient, valeur-clé) et calcul _onchange_ngap."""
        ActeParam = self.env['cabinet.acte.parametrage']

        acte_c = ActeParam.new({
            'name': 'Consultation omnipraticien C',
            'code_cnam': 'C',
            'lettre_cle': 'C',
            'coefficient': 1.0,
            'valeur_cle': 24.0,
            'type_acte': 'consultation',
            'tarif': 0.0,
        })
        acte_c._onchange_ngap()
        self.assertAlmostEqual(acte_c.tarif, 24.0, places=3)

        acte_k10 = ActeParam.new({
            'name': 'Petite chirurgie K10',
            'code_cnam': 'K10',
            'lettre_cle': 'K',
            'coefficient': 10.0,
            'valeur_cle': 2.5,
            'type_acte': 'acte_technique',
            'tarif': 0.0,
        })
        acte_k10._onchange_ngap()
        self.assertAlmostEqual(acte_k10.tarif, 25.0, places=3)

        acte_ke25 = ActeParam.new({
            'name': 'Échographie abdominale KE25',
            'code_cnam': 'KE25',
            'lettre_cle': 'KE',
            'coefficient': 25.0,
            'valeur_cle': 2.0,
            'type_acte': 'acte_technique',
            'tarif': 0.0,
        })
        acte_ke25._onchange_ngap()
        self.assertAlmostEqual(acte_ke25.tarif, 50.0, places=3)

    def test_03_acte_parametrage_temporal_validity(self):
        """Vérifie la gestion de la validité temporelle des tarifs conventionnels."""
        ActeParam = self.env['cabinet.acte.parametrage']
        today = date.today()

        acte = ActeParam.create({
            'name': 'Acte test validité temporelle',
            'type_acte': 'consultation',
            'tarif': 40.0,
            'date_debut_validite': today - timedelta(days=30),
            'date_fin_validite': today + timedelta(days=30),
        })
        self.assertTrue(acte.is_valid_at_date(today))
        self.assertFalse(acte.is_valid_at_date(today - timedelta(days=60)))
        self.assertFalse(acte.is_valid_at_date(today + timedelta(days=60)))
        self.assertTrue(acte.is_valid_at_date(None))

        acte_ouvert = ActeParam.create({
            'name': 'Tarif sans date de fin',
            'type_acte': 'consultation',
            'tarif': 30.0,
            'date_debut_validite': today - timedelta(days=30),
            'date_fin_validite': False,
        })
        self.assertTrue(acte_ouvert.is_valid_at_date(today + timedelta(days=365)))

    def test_04_acte_parametrage_accord_prealable(self):
        """Vérifie l'indicateur d'accord préalable obligatoire (AP)."""
        ActeParam = self.env['cabinet.acte.parametrage']
        acte_ap = ActeParam.create({
            'name': 'Endoscopie digestive interventionnelle',
            'type_acte': 'acte_technique',
            'tarif': 150.0,
            'necessite_accord_prealable': True,
            'conditions_prise_en_charge': 'Accord préalable écrit CNAM requis (art. 22 Convention)',
        })
        self.assertTrue(acte_ap.necessite_accord_prealable)
        self.assertIn('Accord préalable', acte_ap.conditions_prise_en_charge)

        acte_sans_ap = ActeParam.create({
            'name': 'Consultation standard',
            'type_acte': 'consultation',
            'tarif': 35.0,
            'necessite_accord_prealable': False,
        })
        self.assertFalse(acte_sans_ap.necessite_accord_prealable)

    def test_05_preservation_tarifs_existants_et_calcul_parts(self):
        """Vérifie le calcul réel de taux_cnam, tarif_cnam et part_patient."""
        ActeParam = self.env['cabinet.acte.parametrage']
        acte = ActeParam.create({
            'name': 'Consultation directe sans NGAP',
            'type_acte': 'consultation',
            'tarif': 35.0,
        })
        self.assertAlmostEqual(acte.tarif, 35.0, places=3)
        self.assertAlmostEqual(acte.taux_cnam, 70.0, places=2)
        self.assertAlmostEqual(acte.tarif_cnam, 24.5, places=3)
        self.assertAlmostEqual(acte.part_patient, 10.5, places=3)

        acte_tech = ActeParam.create({
            'name': 'Acte technique 80%',
            'type_acte': 'acte_technique',
            'tarif': 100.0,
        })
        self.assertAlmostEqual(acte_tech.taux_cnam, 80.0, places=2)
        self.assertAlmostEqual(acte_tech.tarif_cnam, 80.0, places=3)
        self.assertAlmostEqual(acte_tech.part_patient, 20.0, places=3)
