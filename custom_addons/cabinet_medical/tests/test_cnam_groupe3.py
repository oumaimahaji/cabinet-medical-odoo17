# -*- coding: utf-8 -*-
import unittest

class MockRecord(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, 'active'):
            self.active = True
        if not hasattr(self, 'acte_ids'):
            self.acte_ids = []
        if not hasattr(self, 'assurance_taux'):
            self.assurance_taux = 0.0
        if not hasattr(self, 'has_assurance'):
            self.has_assurance = False
        if not hasattr(self, 'assurance_id'):
            self.assurance_id = None
        if not hasattr(self, 'tarif_conventionnel'):
            self.tarif_conventionnel = 0.0
        if not hasattr(self, 'statut_accord_prealable'):
            self.statut_accord_prealable = 'non_requis'
        if not hasattr(self, 'necessite_accord_prealable'):
            self.necessite_accord_prealable = False
        if not hasattr(self, 'is_acte_apci'):
            self.is_acte_apci = False

    def ensure_one(self):
        return self

    def filtered(self, func):
        return [r for r in self.acte_ids if func(r)]


class MockFacture(object):
    """Simulateur de cabinet.facture intégrant les règles de calcul Groupe 3."""

    def __init__(self, patient, consultation, scenario=None, couverture_depassement_mutuelle=False):
        self.patient_id = patient
        self.consultation_id = consultation
        self.couverture_depassement_mutuelle = couverture_depassement_mutuelle
        self.scenario = scenario or self._compute_scenario()
        self._compute_montant_total()
        self._compute_parts()
        self._compute_parts_display()

    def _compute_scenario(self):
        p = self.patient_id
        if p.is_apci and p.filiere_cnam == 'remboursement':
            return 'apci_remboursement'
        elif p.is_apci:
            return 'apci_tiers_payant'
        elif p.is_cnam and p.filiere_cnam == 'privee' and p.has_assurance:
            return 'cnam_tp_assur'
        elif p.is_cnam and p.filiere_cnam == 'privee':
            return 'cnam_tiers_payant'
        elif p.is_cnam and p.filiere_cnam == 'remboursement' and p.has_assurance:
            return 'cnam_remb_assur'
        elif p.is_cnam and p.filiere_cnam == 'remboursement':
            return 'cnam_remboursement'
        elif not p.is_cnam and p.has_assurance:
            return 'sans_cnam_assur'
        else:
            return 'sans_couverture'

    def _compute_montant_total(self):
        active_actes = [a for a in self.consultation_id.acte_ids if getattr(a, 'active', True)]
        if active_actes:
            self.montant_total = sum(a.montant for a in active_actes)
            tcr_sum = 0.0
            dep_sum = 0.0
            for a in active_actes:
                tcr = a.tarif_conventionnel if getattr(a, 'tarif_conventionnel', 0.0) > 0 else (
                    getattr(getattr(a, 'parametrage_id', None), 'tarif', 0.0) or a.montant
                )
                tcr_sum += tcr
                dep_sum += max(0.0, a.montant - tcr)
            self.montant_conventionnel_total = round(tcr_sum, 2)
            self.depassement_total = round(dep_sum, 2)
        else:
            self.montant_total = 0.0
            self.montant_conventionnel_total = 0.0
            self.depassement_total = 0.0

    def _get_part_cnam_reelle(self):
        p = self.patient_id
        if not p or not p.is_cnam or self.scenario in ('sans_couverture', 'sans_cnam_assur'):
            return 0.0

        part_cnam = 0.0
        active_actes = [a for a in self.consultation_id.acte_ids if getattr(a, 'active', True)]
        has_explicit_apci_acte = any(getattr(a, 'is_acte_apci', False) for a in active_actes)

        for acte in active_actes:
            tcr = acte.tarif_conventionnel if getattr(acte, 'tarif_conventionnel', 0.0) > 0 else (
                getattr(getattr(acte, 'parametrage_id', None), 'tarif', 0.0) or acte.montant
            )

            # Accord préalable non accordé
            if getattr(acte, 'necessite_accord_prealable', False) and getattr(acte, 'statut_accord_prealable', 'non_requis') in ('refuse', 'demande'):
                continue

            # Éligibilité APCI
            is_apci = False
            if p.is_apci:
                if getattr(acte, 'is_acte_apci', False):
                    is_apci = True
                elif has_explicit_apci_acte:
                    is_apci = False
                elif getattr(self.consultation_id, 'is_consultation_apci', False):
                    is_apci = True
                elif getattr(acte, 'force_non_apci', False) or 'non_apci' in getattr(acte, 'description', '').lower():
                    is_apci = False
                else:
                    is_apci = True

            if is_apci:
                part_cnam += tcr * 1.0
                continue

            # Taux de droit commun
            taux = getattr(getattr(acte, 'parametrage_id', None), 'taux_cnam', None)
            if taux is not None:
                taux = taux / 100.0
            else:
                type_a = getattr(acte, 'type_acte', 'consultation')
                if type_a in ('acte_technique', 'chirurgie', 'suture'):
                    taux = 0.80
                elif type_a in ('radiologie', 'biologie'):
                    taux = 0.75
                else:
                    taux = 0.70

            part_cnam += tcr * taux

        return round(part_cnam, 2)

    def _compute_parts(self):
        total = self.montant_total or 0.0
        tcr_total = self.montant_conventionnel_total or total
        depassement = self.depassement_total
        taux_assur = (self.patient_id.assurance_taux or 0.0) / 100.0
        tp_direct = getattr(self.patient_id, 'has_assurance', False) and getattr(getattr(self.patient_id, 'assurance_id', None), 'tiers_payant_direct', False)
        part_cnam_reelle = self._get_part_cnam_reelle()

        ticket_mod_conventionnel = max(0.0, tcr_total - part_cnam_reelle)
        part_mutuelle_tm = ticket_mod_conventionnel * taux_assur
        part_mutuelle_dep = (depassement * taux_assur) if self.couverture_depassement_mutuelle else 0.0
        part_mutuelle_totale = part_mutuelle_tm + part_mutuelle_dep

        if self.scenario == 'sans_couverture':
            self.montant_paye_cabinet = round(total, 2)
            self.montant_cnam_cabinet = 0.0
            self.reste_a_charge_final = round(total, 2)

        elif self.scenario == 'apci_tiers_payant':
            self.montant_cnam_cabinet = round(part_cnam_reelle, 2)
            self.montant_paye_cabinet = round(ticket_mod_conventionnel + depassement, 2)
            self.reste_a_charge_final = round(ticket_mod_conventionnel + depassement, 2)

        elif self.scenario == 'apci_remboursement':
            self.montant_cnam_cabinet = 0.0
            self.montant_paye_cabinet = round(total, 2)
            self.reste_a_charge_final = round(ticket_mod_conventionnel + depassement, 2)

        elif self.scenario in ('cnam_tiers_payant', 'cnam_tp_assur'):
            self.montant_cnam_cabinet = round(part_cnam_reelle, 2)
            if self.scenario == 'cnam_tp_assur':
                if tp_direct:
                    self.montant_paye_cabinet = round((ticket_mod_conventionnel - part_mutuelle_tm) + (depassement - part_mutuelle_dep), 2)
                else:
                    self.montant_paye_cabinet = round(ticket_mod_conventionnel + depassement, 2)
                self.reste_a_charge_final = round((ticket_mod_conventionnel - part_mutuelle_tm) + (depassement - part_mutuelle_dep), 2)
            else:
                self.montant_paye_cabinet = round(ticket_mod_conventionnel + depassement, 2)
                self.reste_a_charge_final = round(ticket_mod_conventionnel + depassement, 2)

        elif self.scenario == 'cnam_remboursement':
            self.montant_paye_cabinet = round(total, 2)
            self.montant_cnam_cabinet = 0.0
            self.reste_a_charge_final = round(ticket_mod_conventionnel + depassement, 2)

        elif self.scenario == 'cnam_remb_assur':
            self.montant_cnam_cabinet = 0.0
            if tp_direct:
                self.montant_paye_cabinet = round(total - part_mutuelle_totale, 2)
            else:
                self.montant_paye_cabinet = round(total, 2)
            self.reste_a_charge_final = round((ticket_mod_conventionnel - part_mutuelle_tm) + (depassement - part_mutuelle_dep), 2)

        elif self.scenario == 'sans_cnam_assur':
            self.montant_cnam_cabinet = 0.0
            part_assur_sans_cnam = total * taux_assur
            if tp_direct:
                self.montant_paye_cabinet = round(total - part_assur_sans_cnam, 2)
            else:
                self.montant_paye_cabinet = round(total, 2)
            self.reste_a_charge_final = round(total - part_assur_sans_cnam, 2)

    def _compute_parts_display(self):
        total = self.montant_total or 0.0
        tcr_total = self.montant_conventionnel_total or total
        depassement = self.depassement_total
        taux_assur = (self.patient_id.assurance_taux or 0.0) / 100.0
        part_cnam_reelle = self._get_part_cnam_reelle()
        ticket_mod = max(0.0, tcr_total - part_cnam_reelle)

        part_cnam = 0.0
        part_assurance = 0.0

        if self.scenario == 'sans_couverture':
            part_cnam = 0.0
            part_assurance = 0.0
        elif self.scenario in ('apci_tiers_payant', 'apci_remboursement'):
            part_cnam = part_cnam_reelle
            part_assurance = 0.0
        elif self.scenario in ('cnam_tiers_payant', 'cnam_tp_assur'):
            part_cnam = part_cnam_reelle
            if self.scenario == 'cnam_tp_assur':
                part_mutuelle_dep = (depassement * taux_assur) if self.couverture_depassement_mutuelle else 0.0
                part_assurance = (ticket_mod * taux_assur) + part_mutuelle_dep
        elif self.scenario == 'cnam_remboursement':
            part_cnam = part_cnam_reelle
            part_assurance = 0.0
        elif self.scenario == 'cnam_remb_assur':
            part_cnam = part_cnam_reelle
            part_mutuelle_dep = (depassement * taux_assur) if self.couverture_depassement_mutuelle else 0.0
            part_assurance = (ticket_mod * taux_assur) + part_mutuelle_dep
        elif self.scenario == 'sans_cnam_assur':
            part_cnam = 0.0
            part_assurance = total * taux_assur

        self.part_cnam_display = round(part_cnam, 2)
        self.part_assurance_display = round(part_assurance, 2)
        self.ticket_moderateur_total = round(ticket_mod, 2)
        self.reste_apres_cnam_seule = round(max(0.0, total - part_cnam), 2)


class TestCnamGroupe3(unittest.TestCase):
    """Tests unitaires Groupe 3 : Règles financières CNAM, TCR, Dépassement, Scénarios 9, 10 et 11."""

    def test_01_honoraires_egaux_tcr_sans_depassement(self):
        """Test A : Honoraires = TCR -> aucun dépassement d'honoraires."""
        patient = MockRecord(name="Patient TP", is_cnam=True, filiere_cnam='privee', is_apci=False, has_assurance=False)
        acte = MockRecord(montant=40.0, tarif_conventionnel=40.0, type_acte='consultation')
        consult = MockRecord(patient_id=patient, acte_ids=[acte], is_consultation_apci=False)
        facture = MockFacture(patient, consult)

        self.assertEqual(facture.montant_total, 40.0)
        self.assertEqual(facture.montant_conventionnel_total, 40.0)
        self.assertEqual(facture.depassement_total, 0.0)
        self.assertEqual(facture.montant_cnam_cabinet, 28.0)  # 70% de 40 DT
        self.assertEqual(facture.montant_paye_cabinet, 12.0)  # Ticket modérateur 30%
        self.assertEqual(facture.reste_a_charge_final, 12.0)

    def test_02_honoraires_superieurs_tcr_depassement_isole(self):
        """Test B : Honoraires > TCR -> la CNAM calcule uniquement sur TCR, dépassement à la charge du patient."""
        patient = MockRecord(name="Patient TP", is_cnam=True, filiere_cnam='privee', is_apci=False, has_assurance=False)
        acte = MockRecord(montant=60.0, tarif_conventionnel=40.0, type_acte='consultation')
        consult = MockRecord(patient_id=patient, acte_ids=[acte], is_consultation_apci=False)
        facture = MockFacture(patient, consult)

        self.assertEqual(facture.montant_total, 60.0)
        self.assertEqual(facture.montant_conventionnel_total, 40.0)
        self.assertEqual(facture.depassement_total, 20.0)
        self.assertEqual(facture.montant_cnam_cabinet, 28.0)  # Toujours 28 DT (70% de 40 DT)
        self.assertEqual(facture.montant_paye_cabinet, 32.0)  # 12 DT ticket + 20 DT dépassement

    def test_03_tiers_payant_repartition(self):
        """Test C : Tiers-payant -> part CNAM = créance cabinet, patient = ticket + dépassement."""
        patient = MockRecord(name="Patient TP", is_cnam=True, filiere_cnam='privee', is_apci=False, has_assurance=False)
        acte = MockRecord(montant=55.0, tarif_conventionnel=50.0, type_acte='acte_technique')
        consult = MockRecord(patient_id=patient, acte_ids=[acte], is_consultation_apci=False)
        facture = MockFacture(patient, consult)

        self.assertEqual(facture.scenario, 'cnam_tiers_payant')
        self.assertEqual(facture.montant_cnam_cabinet, 40.0)  # 80% de 50 DT
        self.assertEqual(facture.montant_paye_cabinet, 15.0)  # 10 DT ticket (20%) + 5 DT dépassement
        self.assertEqual(facture.reste_a_charge_final, 15.0)

    def test_04_remboursement_repartition(self):
        """Test D : Remboursement -> patient paie 100% au cabinet, part CNAM informative uniquement (0 au cabinet)."""
        patient = MockRecord(name="Patient Remb", is_cnam=True, filiere_cnam='remboursement', is_apci=False, has_assurance=False)
        acte = MockRecord(montant=60.0, tarif_conventionnel=40.0, type_acte='consultation')
        consult = MockRecord(patient_id=patient, acte_ids=[acte], is_consultation_apci=False)
        facture = MockFacture(patient, consult)

        self.assertEqual(facture.scenario, 'cnam_remboursement')
        self.assertEqual(facture.montant_cnam_cabinet, 0.0)   # Zéro créance cabinet sur la CNAM
        self.assertEqual(facture.montant_paye_cabinet, 60.0)  # Patient règle l'intégralité
        self.assertEqual(facture.part_cnam_display, 28.0)     # Valeur informative (70% du TCR 40 DT)
        self.assertEqual(facture.reste_a_charge_final, 32.0)  # Reste final après remboursement CNAM

    def test_05_apci_liee_exoneree_100(self):
        """Test E : APCI liée -> exonération totale à 100% de la part conventionnelle."""
        patient = MockRecord(name="Patient APCI", is_cnam=True, filiere_cnam='privee', is_apci=True, has_assurance=False)
        acte = MockRecord(montant=40.0, tarif_conventionnel=40.0, is_acte_apci=True, type_acte='consultation')
        consult = MockRecord(patient_id=patient, acte_ids=[acte], is_consultation_apci=True)
        facture = MockFacture(patient, consult)

        self.assertEqual(facture.scenario, 'apci_tiers_payant')
        self.assertEqual(facture.montant_cnam_cabinet, 40.0)  # 100% pris en charge par CNAM
        self.assertEqual(facture.montant_paye_cabinet, 0.0)
        self.assertEqual(facture.reste_a_charge_final, 0.0)

    def test_06_apci_non_liee_taux_droit_commun(self):
        """Test F : APCI non liée -> taux de droit commun (non 100% d'office)."""
        patient = MockRecord(name="Patient APCI", is_cnam=True, filiere_cnam='privee', is_apci=True, has_assurance=False)
        # Acte sans lien APCI explicite dans une consultation avec acte non lié
        acte = MockRecord(montant=50.0, tarif_conventionnel=50.0, is_acte_apci=False, force_non_apci=True, type_acte='acte_technique')
        consult = MockRecord(patient_id=patient, acte_ids=[acte], is_consultation_apci=False)
        facture = MockFacture(patient, consult)

        self.assertEqual(facture.montant_cnam_cabinet, 40.0)  # 80% taux technique ordinaire (et non 100% 50 DT)
        self.assertEqual(facture.montant_paye_cabinet, 10.0)  # Ticket modérateur de 10 DT
        self.assertEqual(facture.reste_a_charge_final, 10.0)

    def test_07_mutuelle_sur_ticket_sans_depassement_automatique(self):
        """Test G : Mutuelle -> application du taux au ticket modérateur sans imputer automatiquement le dépassement."""
        assurance = MockRecord(name="Star", tiers_payant_direct=False)
        patient = MockRecord(
            name="Patient TP Mutuelle", is_cnam=True, filiere_cnam='privee', is_apci=False,
            has_assurance=True, assurance_id=assurance, assurance_taux=80.0
        )
        # 70 DT honoraires, 45 DT TCR -> dépassement 25 DT
        acte = MockRecord(montant=70.0, tarif_conventionnel=45.0, type_acte='consultation')
        consult = MockRecord(patient_id=patient, acte_ids=[acte], is_consultation_apci=False)
        
        # Par défaut : mutuelle ne couvre PAS le dépassement
        facture = MockFacture(patient, consult, couverture_depassement_mutuelle=False)
        self.assertEqual(facture.montant_cnam_cabinet, 31.50)  # 70% de 45 DT
        self.assertEqual(facture.part_assurance_display, 10.80)  # 80% du TM (13.50 DT)
        self.assertEqual(facture.reste_a_charge_final, 27.70)  # Dépassement 25 DT + TM résiduel 2.70 DT
        self.assertEqual(facture.montant_paye_cabinet, 38.50)  # Au guichet (remboursé 10.80 DT a posteriori)

        # Si option couverture dépassement activée
        facture_opt = MockFacture(patient, consult, couverture_depassement_mutuelle=True)
        # Mutuelle couvre 80% du ticket (10.80) + 80% du dépassement (20.0) = 30.80 DT
        self.assertEqual(facture_opt.part_assurance_display, 30.80)
        self.assertEqual(facture_opt.reste_a_charge_final, 7.70)

    def test_08_accord_prealable_coherence(self):
        """Test H : Accord préalable -> statut en attente ou refusé n'ouvre pas droit au tiers-payant CNAM."""
        patient = MockRecord(name="Patient TP", is_cnam=True, filiere_cnam='privee', is_apci=False, has_assurance=False)
        acte_refuse = MockRecord(
            montant=100.0, tarif_conventionnel=100.0, type_acte='acte_technique',
            necessite_accord_prealable=True, statut_accord_prealable='refuse'
        )
        consult = MockRecord(patient_id=patient, acte_ids=[acte_refuse], is_consultation_apci=False)
        facture = MockFacture(patient, consult)

        self.assertEqual(facture.montant_cnam_cabinet, 0.0)  # Refusé -> 0 DT CNAM
        self.assertEqual(facture.montant_paye_cabinet, 100.0)

    def test_09_scenario_9_depassement_tiers_payant(self):
        """Scénario 9 : Honoraires 60 DT, TCR 40 DT, taux 70% -> CNAM 28 DT, ticket 12 DT, dépassement 20 DT, patient 32 DT, total 60 DT."""
        patient = MockRecord(name="Patient Scénario 9", is_cnam=True, filiere_cnam='privee', is_apci=False, has_assurance=False)
        acte = MockRecord(montant=60.0, tarif_conventionnel=40.0, type_acte='consultation')
        consult = MockRecord(patient_id=patient, acte_ids=[acte], is_consultation_apci=False)
        facture = MockFacture(patient, consult)

        self.assertEqual(facture.montant_total, 60.0)
        self.assertEqual(facture.montant_conventionnel_total, 40.0)
        self.assertEqual(facture.depassement_total, 20.0)
        self.assertEqual(facture.montant_cnam_cabinet, 28.0)
        self.assertEqual(facture.montant_paye_cabinet, 32.0)
        self.assertEqual(facture.reste_a_charge_final, 32.0)
        self.assertEqual(facture.montant_cnam_cabinet + facture.montant_paye_cabinet, 60.0)

    def test_10_scenario_10_seance_mixte_apci(self):
        """Scénario 10 : Acte APCI 40 DT (100%) + Acte non APCI 50 DT (80%) -> Total 90 DT, CNAM 80 DT, patient 10 DT."""
        patient = MockRecord(name="Patient Scénario 10", is_cnam=True, filiere_cnam='privee', is_apci=True, has_assurance=False)
        acte_apci = MockRecord(montant=40.0, tarif_conventionnel=40.0, is_acte_apci=True, type_acte='consultation')
        param_80 = MockRecord(tarif=50.0, taux_cnam=80.0)
        acte_non_apci = MockRecord(montant=50.0, tarif_conventionnel=50.0, is_acte_apci=False, parametrage_id=param_80, type_acte='acte_technique')
        consult = MockRecord(patient_id=patient, acte_ids=[acte_apci, acte_non_apci], is_consultation_apci=True)
        facture = MockFacture(patient, consult)

        self.assertEqual(facture.montant_total, 90.0)
        self.assertEqual(facture.montant_conventionnel_total, 90.0)
        self.assertEqual(facture.depassement_total, 0.0)
        self.assertEqual(facture.montant_cnam_cabinet, 80.0)  # 40 DT (100%) + 40 DT (80%)
        self.assertEqual(facture.montant_paye_cabinet, 10.0)  # 0 DT + 10 DT
        self.assertEqual(facture.reste_a_charge_final, 10.0)
        self.assertEqual(facture.montant_cnam_cabinet + facture.montant_paye_cabinet, 90.0)

    def test_11_scenario_11_depassement_mutuelle(self):
        """Scénario 11 : Honoraires 70 DT, TCR 45 DT, taux 70% -> CNAM 31.50 DT, ticket 13.50 DT, mutuelle 80% (10.80 DT), dep 25 DT, patient 27.70 DT, total 70 DT."""
        assurance = MockRecord(name="Star Assurances", tiers_payant_direct=False)
        patient = MockRecord(
            name="Patient Scénario 11", is_cnam=True, filiere_cnam='privee', is_apci=False,
            has_assurance=True, assurance_id=assurance, assurance_taux=80.0
        )
        param_70 = MockRecord(tarif=45.0, taux_cnam=70.0)
        acte = MockRecord(montant=70.0, tarif_conventionnel=45.0, parametrage_id=param_70, type_acte='consultation')
        consult = MockRecord(patient_id=patient, acte_ids=[acte], is_consultation_apci=False)
        facture = MockFacture(patient, consult)

        self.assertEqual(facture.montant_total, 70.0)
        self.assertEqual(facture.montant_conventionnel_total, 45.0)
        self.assertEqual(facture.depassement_total, 25.0)
        self.assertEqual(facture.montant_cnam_cabinet, 31.50)
        self.assertEqual(facture.part_assurance_display, 10.80)  # 80% du ticket modérateur 13.50 DT
        self.assertEqual(facture.reste_a_charge_final, 27.70)   # 2.70 DT résiduel TM + 25.0 DT dépassement
        self.assertEqual(facture.montant_paye_cabinet, 38.50)   # Payé au cabinet avant remboursement mutuelle
        # Total réconcilié
        self.assertAlmostEqual(facture.montant_cnam_cabinet + facture.part_assurance_display + facture.reste_a_charge_final, 70.0, places=2)


if __name__ == '__main__':
    unittest.main()
