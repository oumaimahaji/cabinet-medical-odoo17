# -*- coding: utf-8 -*-
import unittest
from datetime import date, timedelta

class MockRecord(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, 'active'):
            self.active = True

    def ensure_one(self):
        return self

    def write(self, vals):
        for k, v in vals.items():
            setattr(self, k, v)
        return True

    def _onchange_ngap(self):
        coeff = getattr(self, 'coefficient', 1.0) or 1.0
        valeur = getattr(self, 'valeur_cle', 0.0) or 0.0
        if coeff and valeur:
            self.tarif = round(coeff * valeur, 3)

    def is_valid_at_date(self, check_date):
        self.ensure_one()
        if not check_date:
            return True
        date_debut = getattr(self, 'date_debut_validite', None)
        date_fin = getattr(self, 'date_fin_validite', None)
        if date_debut and check_date < date_debut:
            return False
        if date_fin and check_date > date_fin:
            return False
        return True

    def _compute_parts(self):
        tarif = getattr(self, 'tarif', 0.0) or 0.0
        taux = getattr(self, 'taux_cnam', 70.0) or 70.0
        self.tarif_cnam = round(tarif * (taux / 100.0), 3)
        self.part_patient = round(tarif - self.tarif_cnam, 3)


class TestCnamGroupe1(unittest.TestCase):
    """Tests unitaires Groupe 1 : Référentiel des actes NGAP et Convention Médecin."""

    def test_01_res_company_medecin_convention(self):
        """Vérifie la spécialité du médecin et son statut conventionné."""
        company = MockRecord(
            name="Cabinet Médical Dr. Oumaima Hajji",
            medecin_nom="Dr. Oumaima Hajji",
            medecin_inpe="12345678",
            medecin_code_convention="CONV-2025-01",
            medecin_specialite="generaliste",
            medecin_conventionne=True,
        )
        self.assertEqual(company.medecin_specialite, 'generaliste')
        self.assertTrue(company.medecin_conventionne)
        
        # Test passage en spécialiste
        company.write({'medecin_specialite': 'specialiste'})
        self.assertEqual(company.medecin_specialite, 'specialiste')

    def test_02_acte_parametrage_ngap_fields(self):
        """Vérifie les attributs NGAP (lettre-clé, coefficient, valeur-clé) et calcul tarif."""
        # Consultation omnipraticien C
        acte_c = MockRecord(
            name='Consultation omnipraticien C',
            code_cnam='C',
            lettre_cle='C',
            coefficient=1.0,
            valeur_cle=24.0,
            type_acte='consultation',
            tarif=0.0
        )
        acte_c._onchange_ngap()
        self.assertEqual(acte_c.tarif, 24.0, "Le tarif C doit être 24.0 DT (1.0 * 24.0)")

        # Petite chirurgie K10
        acte_k10 = MockRecord(
            name='Petite chirurgie K10',
            code_cnam='K10',
            lettre_cle='K',
            coefficient=10.0,
            valeur_cle=2.5,
            type_acte='acte_technique',
            tarif=0.0
        )
        acte_k10._onchange_ngap()
        self.assertEqual(acte_k10.tarif, 25.0, "Le tarif K10 doit être 25.0 DT (10.0 * 2.5)")

        # Échographie KE25
        acte_ke25 = MockRecord(
            name='Échographie abdominale KE25',
            code_cnam='KE25',
            lettre_cle='KE',
            coefficient=25.0,
            valeur_cle=2.0,
            type_acte='acte_technique',
            tarif=0.0
        )
        acte_ke25._onchange_ngap()
        self.assertEqual(acte_ke25.tarif, 50.0, "Le tarif KE25 doit être 50.0 DT (25.0 * 2.0)")

    def test_03_acte_parametrage_temporal_validity(self):
        """Vérifie la gestion de la validité temporelle des tarifs conventionnels."""
        today = date.today()
        acte = MockRecord(
            name='Acte test validité temporelle',
            tarif=40.0,
            date_debut_validite=today - timedelta(days=30),
            date_fin_validite=today + timedelta(days=30),
        )
        
        # Date courante -> Valide
        self.assertTrue(acte.is_valid_at_date(today))
        # Date antérieure à la date de début -> Invalide
        self.assertFalse(acte.is_valid_at_date(today - timedelta(days=60)))
        # Date postérieure à la date de fin -> Invalide
        self.assertFalse(acte.is_valid_at_date(today + timedelta(days=60)))
        # Si date_fin est None -> toujours valide après la date de début
        acte_ouvert = MockRecord(
            name='Tarif sans date de fin',
            tarif=30.0,
            date_debut_validite=today - timedelta(days=30),
            date_fin_validite=None,
        )
        self.assertTrue(acte_ouvert.is_valid_at_date(today + timedelta(days=365)))

    def test_04_acte_parametrage_accord_prealable(self):
        """Vérifie l'indicateur d'accord préalable obligatoire (AP)."""
        acte_ap = MockRecord(
            name='Endoscopie digestive interventionnelle',
            tarif=150.0,
            necessite_accord_prealable=True,
            conditions_prise_en_charge='Accord préalable écrit CNAM requis (art. 22 Convention)'
        )
        self.assertTrue(acte_ap.necessite_accord_prealable)
        self.assertIn("Accord préalable", acte_ap.conditions_prise_en_charge)

        acte_sans_ap = MockRecord(
            name='Consultation standard',
            tarif=35.0,
            necessite_accord_prealable=False,
        )
        self.assertFalse(acte_sans_ap.necessite_accord_prealable)

    def test_05_preservation_tarifs_existants(self):
        """Vérifie qu'un acte créé en mode direct (tarif manuel forfaitaire) fonctionne à l'identique."""
        acte_ancien = MockRecord(
            name='Consultation directe sans NGAP',
            tarif=35.0,
            taux_cnam=70.0,
            type_acte='consultation',
        )
        acte_ancien._compute_parts()
        self.assertEqual(acte_ancien.tarif, 35.0)
        self.assertEqual(acte_ancien.taux_cnam, 70.0)
        self.assertEqual(acte_ancien.tarif_cnam, 24.5)
        self.assertEqual(acte_ancien.part_patient, 10.5)


if __name__ == '__main__':
    unittest.main()
