# -*- coding: utf-8 -*-
import unittest
from datetime import date, timedelta

class ValidationError(Exception):
    pass

class MockRecord(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, 'active'):
            self.active = True
        if not hasattr(self, 'acte_ids'):
            self.acte_ids = []
        if not hasattr(self, 'facture_ids'):
            self.facture_ids = []
        if not hasattr(self, 'statut_cnam'):
            self.statut_cnam = 'non_envoye'
        if not hasattr(self, 'bordereau_id'):
            self.bordereau_id = False
        if not hasattr(self, 'code_motif_rejet'):
            self.code_motif_rejet = False
        if not hasattr(self, 'motif_rejet'):
            self.motif_rejet = False
        if not hasattr(self, 'state'):
            self.state = 'draft'

    def ensure_one(self):
        return self

    def filtered(self, func):
        return [r for r in self.acte_ids if func(r)]


class MockFactureGroupe4(MockRecord):
    """Simulateur Facture avec contrôles bloquants et immutabilité Groupe 4."""

    LOCKED_FIELDS = {'patient_id', 'consultation_id', 'date_facture', 'scenario'}

    def action_valider(self):
        self.ensure_one()
        m_tot = getattr(self, 'montant_total', 0.0)
        if m_tot <= 0:
            raise ValidationError("Le montant total doit être supérieur à 0")

        date_ref = getattr(self, 'date_facture', None) or date.today()
        p = getattr(self, 'patient_id', None)

        if self.scenario in ('cnam_tiers_payant', 'apci_tiers_payant', 'cnam_tp_assur'):
            if not p:
                raise ValidationError("Validation impossible : Aucun patient rattaché à la facture.")
            if not getattr(p, 'is_cnam', False):
                raise ValidationError("Validation impossible en Tiers-payant : Le patient n'est pas identifié comme assuré CNAM.")

            # 1. Droits CNAM expirés
            validite_cnam = getattr(p, 'date_validite_cnam', None)
            if validite_cnam and validite_cnam < date_ref:
                raise ValidationError(f"Validation impossible en Tiers-payant : Les droits CNAM de l'assuré {p.name} sont expirés.")

            # 2. Prise en charge APCI
            consult = getattr(self, 'consultation_id', None)
            acte_ids = getattr(consult, 'acte_ids', []) if consult else []
            active_actes = [a for a in acte_ids if getattr(a, 'active', True)]
            has_apci_acte = any(getattr(a, 'is_acte_apci', False) for a in active_actes)

            if self.scenario == 'apci_tiers_payant' or has_apci_acte:
                if not getattr(p, 'is_apci', False):
                    raise ValidationError(f"Validation impossible en APCI : Le patient {p.name} n'est pas enregistré comme bénéficiaire de l'APCI.")
                if not getattr(p, 'numero_decision_apci', False):
                    raise ValidationError(f"Validation impossible : Le patient {p.name} n'a aucun numéro de décision APCI valide.")
                date_fin_apci = getattr(p, 'date_fin_apci', None)
                if date_fin_apci and date_fin_apci < date_ref:
                    raise ValidationError(f"Validation impossible en APCI : La prise en charge APCI de {p.name} est expirée.")

            # 3. Accord préalable obligatoire
            for a in active_actes:
                if getattr(a, 'necessite_accord_prealable', False):
                    statut_ap = getattr(a, 'statut_accord_prealable', 'non_requis')
                    num_ap = getattr(a, 'numero_accord_prealable', False)
                    if statut_ap != 'accorde' and not num_ap:
                        desc = getattr(a, 'description', '') or getattr(a, 'type_acte', 'Acte conventionné')
                        raise ValidationError(f"Validation impossible en Tiers-payant : L'acte '{desc}' requiert un accord préalable obligatoire de la CNAM.")

        self.state = 'validated'

    def unlink(self):
        if self.state == 'validated':
            raise ValidationError(f"Suppression interdite : La facture {self.name} est validée et constitue une pièce comptable immuable.")
        if getattr(self, 'bordereau_id', False):
            raise ValidationError(f"Suppression interdite : La facture {self.name} est rattachée à un bordereau CNAM.")
        return True

    def write(self, vals, bypass_lock=False):
        if self.state == 'validated' and not bypass_lock:
            locked_modified = set(vals.keys()) & self.LOCKED_FIELDS
            if locked_modified:
                raise ValidationError(f"Modification interdite : La facture {self.name} est validée. Les champs suivants sont verrouillés : {', '.join(locked_modified)}.")
            if self.bordereau_id and 'bordereau_id' in vals and vals['bordereau_id'] != self.bordereau_id:
                raise ValidationError(f"Modification interdite : La facture {self.name} est déjà rattachée à un bordereau.")
        for k, v in vals.items():
            setattr(self, k, v)
        return True


class MockBordereauGroupe4(MockRecord):
    """Simulateur Bordereau M5 avec consolidation, immutabilité et rejets structurés."""

    def action_recuperer_factures(self, all_factures):
        if self.state != 'draft':
            raise ValidationError("Vous ne pouvez récupérer les factures que si le bordereau est en brouillon.")
        
        eligible = [
            f for f in all_factures
            if f.state == 'validated'
            and self.date_debut <= f.date_facture <= self.date_fin
            and f.scenario in ('cnam_tiers_payant', 'apci_tiers_payant', 'cnam_tp_assur')
            and getattr(f, 'montant_cnam_cabinet', 0.0) > 0
            and not getattr(f, 'bordereau_id', False)
        ]
        for f in eligible:
            f.bordereau_id = self
            f.statut_cnam = 'non_envoye'
            self.facture_ids.append(f)
        self._compute_totaux()

    def _compute_totaux(self):
        self.nb_factures = len(self.facture_ids)
        self.montant_total = sum(getattr(f, 'montant_total', 0.0) for f in self.facture_ids)
        self.montant_cnam_demande = sum(getattr(f, 'montant_cnam_cabinet', 0.0) for f in self.facture_ids)

    def action_valider(self):
        if not self.facture_ids:
            raise ValidationError("Impossible de valider un bordereau vide.")
        self.state = 'done'

    def action_envoyer(self):
        self.state = 'sent'
        self.date_envoi = date.today()
        for f in self.facture_ids:
            f.statut_cnam = 'envoye'

    def action_marquer_paye(self):
        self.state = 'paid'
        for f in self.facture_ids:
            f.statut_cnam = 'paye'

    def action_rejeter(self, code_motif='autre', motif_text=None):
        self.code_motif_rejet = code_motif
        self.motif_rejet = motif_text or "Motif réglementaire de rejet"
        self.state = 'rejected'
        for f in self.facture_ids:
            f.statut_cnam = 'rejete'

    def unlink(self):
        if self.state != 'draft':
            raise ValidationError(f"Suppression interdite : Le bordereau {self.name} est dans l'état '{self.state}' et ne peut pas être supprimé.")
        return True

    def write(self, vals, bypass_lock=False):
        if self.state != 'draft' and not bypass_lock:
            if 'date_debut' in vals and vals['date_debut'] != self.date_debut:
                raise ValidationError("Modification interdite : Impossible de modifier la date de début d'un bordereau non-brouillon.")
            if 'date_fin' in vals and vals['date_fin'] != self.date_fin:
                raise ValidationError("Modification interdite : Impossible de modifier la date de fin d'un bordereau non-brouillon.")
        for k, v in vals.items():
            setattr(self, k, v)
        return True


class TestCnamGroupe4(unittest.TestCase):
    """
    Tests Unitaires Groupe 4 : Contrôles bloquants CNAM, Immutabilité et Bordereaux CNAM (M5)
    """

    def setUp(self):
        self.today = date.today()
        self.yesterday = self.today - timedelta(days=1)
        self.tomorrow = self.today + timedelta(days=30)

    def test_01_blocage_tiers_payant_droits_cnam_expires(self):
        """1. Contrôle bloquant : Droits CNAM expirés à la date de soins -> validation bloquée en tiers-payant."""
        patient = MockRecord(
            name="Patient Droits Expirés",
            is_cnam=True,
            filiere_cnam='privee',
            date_validite_cnam=self.yesterday,
            is_apci=False
        )
        facture = MockFactureGroupe4(
            name="FAC-TEST-01",
            montant_total=60.0,
            date_facture=self.today,
            patient_id=patient,
            consultation_id=MockRecord(acte_ids=[]),
            scenario='cnam_tiers_payant'
        )

        with self.assertRaises(ValidationError) as ctx:
            facture.action_valider()
        self.assertIn("expirés", str(ctx.exception))

    def test_02_succes_tiers_payant_droits_cnam_valides(self):
        """2. Validation autorisée : Droits CNAM en cours de validité -> validation tiers-payant OK."""
        patient = MockRecord(
            name="Patient Droits Valides",
            is_cnam=True,
            filiere_cnam='privee',
            date_validite_cnam=self.tomorrow,
            is_apci=False
        )
        facture = MockFactureGroupe4(
            name="FAC-TEST-02",
            montant_total=60.0,
            date_facture=self.today,
            patient_id=patient,
            consultation_id=MockRecord(acte_ids=[]),
            scenario='cnam_tiers_payant'
        )

        facture.action_valider()
        self.assertEqual(facture.state, 'validated')

    def test_03_blocage_apci_date_fin_depassee(self):
        """3. Contrôle bloquant : Prise en charge APCI échue -> validation bloquée."""
        patient = MockRecord(
            name="Patient APCI Échue",
            is_cnam=True,
            filiere_cnam='privee',
            date_validite_cnam=self.tomorrow,
            is_apci=True,
            numero_decision_apci="APCI-12345",
            date_fin_apci=self.yesterday
        )
        facture = MockFactureGroupe4(
            name="FAC-TEST-03",
            montant_total=50.0,
            date_facture=self.today,
            patient_id=patient,
            consultation_id=MockRecord(acte_ids=[]),
            scenario='apci_tiers_payant'
        )

        with self.assertRaises(ValidationError) as ctx:
            facture.action_valider()
        self.assertIn("expirée", str(ctx.exception))

    def test_04_blocage_apci_sans_decision(self):
        """4. Contrôle bloquant : Patient APCI sans numéro de décision formelle."""
        patient = MockRecord(
            name="Patient APCI Sans Décision",
            is_cnam=True,
            filiere_cnam='privee',
            date_validite_cnam=self.tomorrow,
            is_apci=True,
            numero_decision_apci=False,
            date_fin_apci=self.tomorrow
        )
        facture = MockFactureGroupe4(
            name="FAC-TEST-04",
            montant_total=50.0,
            date_facture=self.today,
            patient_id=patient,
            consultation_id=MockRecord(acte_ids=[]),
            scenario='apci_tiers_payant'
        )

        with self.assertRaises(ValidationError) as ctx:
            facture.action_valider()
        self.assertIn("numéro de décision APCI", str(ctx.exception))

    def test_05_blocage_accord_prealable_requis_non_accorde(self):
        """5. Contrôle bloquant : Acte nécessitant accord préalable sans accord accordé."""
        patient = MockRecord(
            name="Patient AP Requis",
            is_cnam=True,
            filiere_cnam='privee',
            date_validite_cnam=self.tomorrow,
            is_apci=False
        )
        acte_ap = MockRecord(
            description="Acte lourd sous AP",
            active=True,
            necessite_accord_prealable=True,
            statut_accord_prealable='demande',
            numero_accord_prealable=False,
            is_acte_apci=False
        )
        facture = MockFactureGroupe4(
            name="FAC-TEST-05",
            montant_total=120.0,
            date_facture=self.today,
            patient_id=patient,
            consultation_id=MockRecord(acte_ids=[acte_ap]),
            scenario='cnam_tiers_payant'
        )

        with self.assertRaises(ValidationError) as ctx:
            facture.action_valider()
        self.assertIn("accord préalable obligatoire", str(ctx.exception))

    def test_06_succes_accord_prealable_accorde(self):
        """6. Validation autorisée : Acte avec accord préalable validé et accordé."""
        patient = MockRecord(
            name="Patient AP Accordé",
            is_cnam=True,
            filiere_cnam='privee',
            date_validite_cnam=self.tomorrow,
            is_apci=False
        )
        acte_ap = MockRecord(
            description="Acte sous AP accordé",
            active=True,
            necessite_accord_prealable=True,
            statut_accord_prealable='accorde',
            numero_accord_prealable="AP-CNAM-2026-99",
            is_acte_apci=False
        )
        facture = MockFactureGroupe4(
            name="FAC-TEST-06",
            montant_total=120.0,
            date_facture=self.today,
            patient_id=patient,
            consultation_id=MockRecord(acte_ids=[acte_ap]),
            scenario='cnam_tiers_payant'
        )

        facture.action_valider()
        self.assertEqual(facture.state, 'validated')

    def test_07_immutabilite_facture_validee_unlink_interdit(self):
        """7. Immutabilité : Interdiction absolue de supprimer une facture validée."""
        facture = MockFactureGroupe4(
            name="FAC-TEST-07",
            state='validated',
            bordereau_id=False
        )

        with self.assertRaises(ValidationError) as ctx:
            facture.unlink()
        self.assertIn("Suppression interdite", str(ctx.exception))

    def test_08_immutabilite_facture_bordereau_unlink_interdit(self):
        """8. Immutabilité : Interdiction absolue de supprimer une facture liée à un bordereau."""
        bordereau = MockRecord(name="BOR/2026/001")
        facture = MockFactureGroupe4(
            name="FAC-TEST-08",
            state='draft',
            bordereau_id=bordereau
        )

        with self.assertRaises(ValidationError) as ctx:
            facture.unlink()
        self.assertIn("rattachée à un bordereau", str(ctx.exception))

    def test_09_immutabilite_facture_champs_sensibles_write_interdit(self):
        """9. Immutabilité : Interdiction de modifier patient_id ou scenario sur facture validée."""
        facture = MockFactureGroupe4(
            name="FAC-TEST-09",
            state='validated',
            bordereau_id=False
        )

        with self.assertRaises(ValidationError) as ctx:
            facture.write({'patient_id': 999})
        self.assertIn("Modification interdite", str(ctx.exception))

    def test_10_bordereau_recuperation_exclusive_factures_tiers_payant(self):
        """10. Bordereau : Récupération exclusive des factures tiers-payant validées avec part CNAM > 0."""
        bordereau = MockBordereauGroupe4(
            name="BOR-TEST-10",
            state='draft',
            date_debut=self.yesterday,
            date_fin=self.tomorrow,
            facture_ids=[]
        )

        # F1 : Éligible tiers-payant
        f1 = MockRecord(
            name="F1", state='validated', date_facture=self.today,
            scenario='cnam_tiers_payant', montant_total=55.0, montant_cnam_cabinet=44.0, bordereau_id=False
        )
        # F2 : Remboursement (doit être exclue)
        f2 = MockRecord(
            name="F2", state='validated', date_facture=self.today,
            scenario='cnam_remboursement', montant_total=55.0, montant_cnam_cabinet=0.0, bordereau_id=False
        )
        # F3 : Brouillon (doit être exclue)
        f3 = MockRecord(
            name="F3", state='draft', date_facture=self.today,
            scenario='cnam_tiers_payant', montant_total=55.0, montant_cnam_cabinet=44.0, bordereau_id=False
        )
        # F4 : Déjà bordereautée (doit être exclue)
        f4 = MockRecord(
            name="F4", state='validated', date_facture=self.today,
            scenario='cnam_tiers_payant', montant_total=55.0, montant_cnam_cabinet=44.0, bordereau_id="ANCIEN_BOR"
        )

        bordereau.action_recuperer_factures([f1, f2, f3, f4])
        self.assertEqual(len(bordereau.facture_ids), 1)
        self.assertEqual(bordereau.facture_ids[0].name, "F1")
        self.assertEqual(f1.statut_cnam, 'non_envoye')
        self.assertEqual(f1.bordereau_id, bordereau)
        self.assertEqual(bordereau.montant_cnam_demande, 44.0)

    def test_11_bordereau_cycle_de_vie_synchro_factures(self):
        """11. Synchronisation bordereau -> factures : Passage de envoyé à payé."""
        f1 = MockRecord(statut_cnam='non_envoye')
        f2 = MockRecord(statut_cnam='non_envoye')
        bordereau = MockBordereauGroupe4(
            name="BOR-TEST-11",
            state='draft',
            facture_ids=[f1, f2]
        )

        # Validation
        bordereau.action_valider()
        self.assertEqual(bordereau.state, 'done')

        # Envoi
        bordereau.action_envoyer()
        self.assertEqual(bordereau.state, 'sent')
        self.assertEqual(f1.statut_cnam, 'envoye')
        self.assertEqual(f2.statut_cnam, 'envoye')

        # Paiement
        bordereau.action_marquer_paye()
        self.assertEqual(bordereau.state, 'paid')
        self.assertEqual(f1.statut_cnam, 'paye')
        self.assertEqual(f2.statut_cnam, 'paye')

    def test_12_bordereau_gestion_structuree_motif_rejet(self):
        """12. Gestion des rejets : Enregistrement du code motif réglementaire lors du rejet."""
        f1 = MockRecord(statut_cnam='envoye')
        bordereau = MockBordereauGroupe4(
            name="BOR-TEST-12",
            state='sent',
            facture_ids=[f1]
        )

        bordereau.action_rejeter(code_motif='droits_expires', motif_text="Assuré sans couverture à la date des soins")
        self.assertEqual(bordereau.state, 'rejected')
        self.assertEqual(f1.statut_cnam, 'rejete')
        self.assertEqual(bordereau.code_motif_rejet, 'droits_expires')

    def test_13_immutabilite_bordereau_non_brouillon_unlink_et_dates_interdit(self):
        """13. Immutabilité bordereau : Interdiction de supprimer ou changer dates d'un bordereau validé."""
        bordereau = MockBordereauGroupe4(
            name="BOR-TEST-13",
            state='sent',
            date_debut=self.yesterday,
            date_fin=self.today
        )

        with self.assertRaises(ValidationError) as ctx:
            bordereau.unlink()
        self.assertIn("Suppression interdite", str(ctx.exception))

        with self.assertRaises(ValidationError) as ctx2:
            bordereau.write({'date_debut': self.tomorrow})
        self.assertIn("Modification interdite", str(ctx2.exception))


if __name__ == '__main__':
    unittest.main()
