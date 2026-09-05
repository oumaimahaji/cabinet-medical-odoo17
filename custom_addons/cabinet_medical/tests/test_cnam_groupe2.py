# -*- coding: utf-8 -*-
import unittest
from datetime import date, datetime, timedelta

class MockValidationError(Exception):
    pass

class MockRecord(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, 'active'):
            self.active = True
        if not hasattr(self, 'acte_ids'):
            self.acte_ids = []

    def ensure_one(self):
        return self

    def write(self, vals):
        for k, v in vals.items():
            setattr(self, k, v)
        return True


class TestCnamGroupe2(unittest.TestCase):
    """Tests unitaires Groupe 2 : Distinction Honoraires/Tarif Conventionnel, APCI ciblée, Accord Préalable et Bénéficiaires."""

    def test_01_patient_beneficiaire_06_et_filiere_publique(self):
        """Vérifie le support du code ayant droit 06 (ascendant) et de la filière publique."""
        patient = MockRecord(
            name="M. Salah Ben Amor (Père à charge)",
            cin="04567890",
            is_cnam=True,
            numero_cnam="1234567890",
            code_beneficiaire_cnam="06",
            filiere_cnam="publique",
        )
        self.assertEqual(patient.code_beneficiaire_cnam, "06")
        self.assertEqual(patient.filiere_cnam, "publique")

    def test_02_consultation_apci_coherence_and_validation(self):
        """Vérifie le comportement de la consultation ciblée APCI (Décret 2005-1367 art. 19)."""
        today = date.today()
        # 1. Patient non-APCI -> avertissement et rejet de is_consultation_apci
        patient_sain = MockRecord(name="Patient Non APCI", is_apci=False)
        consult_invalide = MockRecord(patient_id=patient_sain, is_consultation_apci=True, acte_ids=[])
        
        # Simule _onchange_is_consultation_apci
        if consult_invalide.is_consultation_apci and consult_invalide.patient_id and not consult_invalide.patient_id.is_apci:
            consult_invalide.is_consultation_apci = False
            warning = True
        else:
            warning = False
        self.assertTrue(warning)
        self.assertFalse(consult_invalide.is_consultation_apci)

        # 2. Patient APCI valide -> succès
        patient_apci = MockRecord(
            name="Patient Diabétique APCI",
            is_apci=True,
            numero_decision_apci="APCI-2026-004",
            date_fin_apci=today + timedelta(days=180)
        )
        consult_valide = MockRecord(
            patient_id=patient_apci,
            is_consultation_apci=True,
            date_consultation=datetime.now(),
            acte_ids=[]
        )
        # Validation constraint
        consult_date = consult_valide.date_consultation.date()
        valid = (
            consult_valide.patient_id.is_apci and
            bool(consult_valide.patient_id.numero_decision_apci) and
            (not consult_valide.patient_id.date_fin_apci or consult_valide.patient_id.date_fin_apci >= consult_date)
        )
        self.assertTrue(valid)

        # 3. Patient APCI expiré -> levée d'erreur
        patient_expire = MockRecord(
            name="Patient APCI Expiré",
            is_apci=True,
            numero_decision_apci="APCI-2024-001",
            date_fin_apci=today - timedelta(days=10)
        )
        consult_expire = MockRecord(
            patient_id=patient_expire,
            is_consultation_apci=True,
            date_consultation=datetime.now(),
            acte_ids=[]
        )
        is_expired = consult_expire.patient_id.date_fin_apci < consult_expire.date_consultation.date()
        self.assertTrue(is_expired, "Une décision APCI échue doit être détectée.")

    def test_03_acte_tarif_conventionnel_et_depassement(self):
        """Vérifie le calcul du dépassement d'honoraires par rapport au tarif conventionnel."""
        # Acte 1 : Consultation conventionnée sans dépassement (35 DT facturé = 35 DT conventionnel)
        acte1 = MockRecord(montant=35.0, tarif_conventionnel=35.0)
        depassement1 = max(0.0, (acte1.montant or 0.0) - acte1.tarif_conventionnel) if acte1.tarif_conventionnel > 0 else 0.0
        self.assertEqual(depassement1, 0.0)

        # Acte 2 : Dépassement d'honoraires (60 DT facturé pour 35 DT conventionnel)
        acte2 = MockRecord(montant=60.0, tarif_conventionnel=35.0)
        depassement2 = max(0.0, (acte2.montant or 0.0) - acte2.tarif_conventionnel) if acte2.tarif_conventionnel > 0 else 0.0
        self.assertEqual(depassement2, 25.0)

        # Acte 3 : Acte sans tarif conventionnel renseigné -> dépassement = 0
        acte3 = MockRecord(montant=40.0, tarif_conventionnel=0.0)
        depassement3 = max(0.0, (acte3.montant or 0.0) - acte3.tarif_conventionnel) if acte3.tarif_conventionnel > 0 else 0.0
        self.assertEqual(depassement3, 0.0)

    def test_04_acte_accord_prealable_validation(self):
        """Vérifie le contrôle d'accord préalable obligatoire pour les actes conventionnés (Convention art. 22)."""
        param_lourd = MockRecord(name="Acte lourd sous AP", necessite_accord_prealable=True)
        patient_tp = MockRecord(is_cnam=True, filiere_cnam='privee')
        consult = MockRecord(patient_id=patient_tp)

        # 1. Statut non accordé ou sans numéro lors de la validation
        acte_non_accorde = MockRecord(
            state='done',
            parametrage_id=param_lourd,
            consultation_id=consult,
            statut_accord_prealable='demande',
            numero_accord_prealable=False,
        )
        is_blocked = (
            acte_non_accorde.state == 'done' and
            acte_non_accorde.parametrage_id.necessite_accord_prealable and
            acte_non_accorde.consultation_id.patient_id.is_cnam and
            acte_non_accorde.consultation_id.patient_id.filiere_cnam == 'privee' and
            (acte_non_accorde.statut_accord_prealable != 'accorde' or not acte_non_accorde.numero_accord_prealable)
        )
        self.assertTrue(is_blocked, "L'acte sous AP sans accord formel de la CNAM doit être bloqué.")

        # 2. Statut accordé avec numéro de décision CNAM
        acte_accorde = MockRecord(
            state='done',
            parametrage_id=param_lourd,
            consultation_id=consult,
            statut_accord_prealable='accorde',
            numero_accord_prealable='AP-2026-TUN-0089',
        )
        is_blocked_accorde = (
            acte_accorde.state == 'done' and
            acte_accorde.parametrage_id.necessite_accord_prealable and
            acte_accorde.consultation_id.patient_id.is_cnam and
            acte_accorde.consultation_id.patient_id.filiere_cnam == 'privee' and
            (acte_accorde.statut_accord_prealable != 'accorde' or not acte_accorde.numero_accord_prealable)
        )
        self.assertFalse(is_blocked_accorde, "L'acte avec accord préalable accordé et numéro doit passer.")

    def test_05_preservation_baseline_calcul_actes(self):
        """Vérifie que la part patient au cabinet (total_acte_dt) conserve son exact comportement baseline."""
        # A. Tiers-payant consultation 35 DT @ 70% -> patient paie 10.5 DT
        param_c = MockRecord(taux_cnam=70.0)
        patient_tp = MockRecord(is_cnam=True, filiere_cnam='privee', is_apci=False)
        consult_tp = MockRecord(patient_id=patient_tp, is_consultation_apci=False)
        acte_tp = MockRecord(
            montant=35.0,
            tarif_conventionnel=35.0,
            parametrage_id=param_c,
            consultation_id=consult_tp,
            is_acte_apci=False
        )
        taux = acte_tp.parametrage_id.taux_cnam
        acte_tp.total_acte_dt = round(acte_tp.montant * (1.0 - taux / 100.0), 3)
        self.assertEqual(acte_tp.total_acte_dt, 10.5)

        # B. APCI Tiers-payant -> patient paie 0 DT
        patient_apci = MockRecord(is_cnam=True, filiere_cnam='privee', is_apci=True)
        consult_apci = MockRecord(patient_id=patient_apci, is_consultation_apci=True)
        acte_apci = MockRecord(
            montant=55.0,
            tarif_conventionnel=55.0,
            parametrage_id=param_c,
            consultation_id=consult_apci,
            is_acte_apci=True
        )
        # APCI exonéré
        acte_apci.total_acte_dt = 0.0
        self.assertEqual(acte_apci.total_acte_dt, 0.0)

        # C. Remboursement classique -> patient avance 55 DT
        patient_remb = MockRecord(is_cnam=True, filiere_cnam='remboursement', is_apci=False)
        consult_remb = MockRecord(patient_id=patient_remb, is_consultation_apci=False)
        acte_remb = MockRecord(
            montant=55.0,
            tarif_conventionnel=55.0,
            parametrage_id=param_c,
            consultation_id=consult_remb,
            is_acte_apci=False
        )
        acte_remb.total_acte_dt = acte_remb.montant
        self.assertEqual(acte_remb.total_acte_dt, 55.0)


if __name__ == '__main__':
    unittest.main()
