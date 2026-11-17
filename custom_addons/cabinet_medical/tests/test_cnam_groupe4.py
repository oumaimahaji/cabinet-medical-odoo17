# -*- coding: utf-8 -*-
from datetime import date, timedelta
from unittest.mock import patch
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'cabinet_cnam')
class TestCnamGroupe4(TransactionCase):
    """Tests d'intégration Groupe 4 : Contrôles bloquants Facture, Immutabilité et Bordereaux CNAM."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Patient = cls.env['cabinet.patient']
        cls.Consultation = cls.env['cabinet.consultation']
        cls.Acte = cls.env['cabinet.acte']
        cls.ActeParam = cls.env['cabinet.acte.parametrage']
        cls.Facture = cls.env['cabinet.facture']
        cls.Bordereau = cls.env['cabinet.bordereau']

        cls.param_c = cls.ActeParam.create({
            'name': 'Consultation C G4',
            'type_acte': 'consultation',
            'tarif': 35.0,
        })
        cls.param_ap = cls.ActeParam.create({
            'name': 'Acte AP G4',
            'type_acte': 'acte_technique',
            'tarif': 150.0,
            'necessite_accord_prealable': True,
        })

    def _make_facture(self, patient, param, montant=35.0, date_facture=None,
                      is_acte_apci=False, statut_ap='non_requis', num_ap=False):
        consult = self.Consultation.create({
            'patient_id': patient.id,
            'motif': 'Consultation facturation G4',
        })
        self.Acte.create({
            'consultation_id': consult.id,
            'parametrage_id': param.id,
            'type_acte': param.type_acte,
            'description': param.name,
            'montant': montant,
            'tarif_conventionnel': montant,
            'is_acte_apci': is_acte_apci,
            'statut_accord_prealable': statut_ap,
            'numero_accord_prealable': num_ap,
        })
        vals = {
            'patient_id': patient.id,
            'consultation_id': consult.id,
        }
        if date_facture:
            vals['date_facture'] = date_facture
        return self.Facture.create(vals)

    def test_01_blocage_tiers_payant_droits_cnam_expires(self):
        """Droits CNAM expirés : action_valider() doit bloquer le tiers-payant."""
        today = date.today()
        p = self.Patient.create({
            'name': 'Patient CNAM Expiré G4',
            'cin': '99003001',
            'is_cnam': True,
            'numero_cnam': '2000000001',
            'filiere_cnam': 'privee',
            'date_validite_cnam': today - timedelta(days=5),
        })
        f = self._make_facture(p, self.param_c, date_facture=today)
        with self.assertRaises(ValidationError) as ctx:
            f.action_valider()
        self.assertIn('expirés', str(ctx.exception))
        self.assertEqual(f.state, 'draft')

    def test_02_succes_tiers_payant_droits_cnam_valides(self):
        """Droits CNAM valides : action_valider() passe la facture à 'validated'."""
        today = date.today()
        p = self.Patient.create({
            'name': 'Patient CNAM Valide G4',
            'cin': '99003002',
            'is_cnam': True,
            'numero_cnam': '2000000002',
            'filiere_cnam': 'privee',
            'date_validite_cnam': today + timedelta(days=60),
        })
        f = self._make_facture(p, self.param_c, date_facture=today)
        f.action_valider()
        self.assertEqual(f.state, 'validated')

    def test_03_blocage_apci_date_fin_depassee(self):
        """APCI expirée : action_valider() doit bloquer."""
        today = date.today()
        p = self.Patient.create({
            'name': 'Patient APCI Expiré G4',
            'cin': '99003003',
            'is_cnam': True,
            'numero_cnam': '2000000003',
            'filiere_cnam': 'privee',
            'date_validite_cnam': today + timedelta(days=60),
            'is_apci': True,
            'numero_decision_apci': 'APCI-2025-111',
            'date_fin_apci': today - timedelta(days=1),
        })
        f = self._make_facture(p, self.param_c, date_facture=today, is_acte_apci=True)
        with self.assertRaises(ValidationError) as ctx:
            f.action_valider()
        self.assertIn('expirée', str(ctx.exception))

    def test_04_blocage_apci_sans_decision(self):
        """APCI sans numéro de décision : _check_apci_decision et _validate_apci_rules bloquent."""
        today = date.today()
        p = self.Patient.create({
            'name': 'Patient APCI Sans Décision G4',
            'cin': '99003004',
            'is_cnam': True,
            'numero_cnam': '2000000004',
            'filiere_cnam': 'privee',
            'date_validite_cnam': today + timedelta(days=60),
            'is_apci': True,
            'numero_decision_apci': False,
        })
        with patch.object(type(self.Facture), '_get_llm_alert', return_value='APCI sans décision'):
            with self.assertRaises(ValidationError):
                self._make_facture(p, self.param_c, date_facture=today, is_acte_apci=True)

        # Cas où la décision est retirée après création : action_valider() bloque aussi
        p.numero_decision_apci = 'TEMP-DEC'
        f = self._make_facture(p, self.param_c, date_facture=today, is_acte_apci=True)
        p.numero_decision_apci = False
        with self.assertRaises(ValidationError):
            f.action_valider()

    def test_05_blocage_accord_prealable_requis_non_accorde(self):
        """Acte sous AP en statut 'demande' sans numéro : action_valider() bloque."""
        today = date.today()
        p = self.Patient.create({
            'name': 'Patient AP Manquant G4',
            'cin': '99003005',
            'is_cnam': True,
            'numero_cnam': '2000000005',
            'filiere_cnam': 'privee',
            'date_validite_cnam': today + timedelta(days=60),
        })
        f = self._make_facture(
            p, self.param_ap, montant=150.0, date_facture=today,
            statut_ap='demande', num_ap=False,
        )
        with self.assertRaises(ValidationError) as ctx:
            f.action_valider()
        self.assertIn('accord préalable', str(ctx.exception).lower())

    def test_06_succes_accord_prealable_accorde(self):
        """Acte sous AP accordé avec numéro : action_valider() réussit."""
        today = date.today()
        p = self.Patient.create({
            'name': 'Patient AP Accordé G4',
            'cin': '99003006',
            'is_cnam': True,
            'numero_cnam': '2000000006',
            'filiere_cnam': 'privee',
            'date_validite_cnam': today + timedelta(days=60),
        })
        f = self._make_facture(
            p, self.param_ap, montant=150.0, date_facture=today,
            statut_ap='accorde', num_ap='AP-2026-999',
        )
        f.action_valider()
        self.assertEqual(f.state, 'validated')

    def test_07_immutabilite_facture_validee_unlink_et_write(self):
        """Une facture validée ne peut être ni supprimée ni modifiée sur ses champs verrouillés."""
        today = date.today()
        p = self.Patient.create({
            'name': 'Patient Immutabilité G4',
            'cin': '99003007',
            'is_cnam': True,
            'numero_cnam': '2000000007',
            'filiere_cnam': 'privee',
            'date_validite_cnam': today + timedelta(days=60),
        })
        f = self._make_facture(p, self.param_c, date_facture=today)
        f.action_valider()

        with self.assertRaises(ValidationError):
            f.unlink()

        with self.assertRaises(ValidationError):
            f.write({'date_facture': today + timedelta(days=1)})

    def test_08_bordereau_recuperation_cycle_vie_et_immutabilite(self):
        """BordereauCNAM : récupération exclusive tiers-payant, cycle de vie, rejet et immutabilité."""
        today = date.today()
        debut = today.replace(day=1)
        fin = today

        p_tp = self.Patient.create({
            'name': 'Patient Bordereau TP',
            'cin': '99003008',
            'is_cnam': True,
            'numero_cnam': '2000000008',
            'filiere_cnam': 'privee',
            'date_validite_cnam': today + timedelta(days=60),
        })
        p_remb = self.Patient.create({
            'name': 'Patient Bordereau Remb',
            'cin': '99003009',
            'is_cnam': True,
            'numero_cnam': '2000000009',
            'filiere_cnam': 'remboursement',
            'date_validite_cnam': today + timedelta(days=60),
        })

        f_tp = self._make_facture(p_tp, self.param_c, date_facture=today)
        f_tp.action_valider()
        f_remb = self._make_facture(p_remb, self.param_c, date_facture=today)
        f_remb.action_valider()

        # Dates incohérentes -> ValidationError
        with self.assertRaises(ValidationError):
            self.Bordereau.create({
                'date_debut': today,
                'date_fin': today - timedelta(days=5),
            })

        bord = self.Bordereau.create({
            'date_debut': debut,
            'date_fin': fin,
        })
        # Validation bordereau vide -> ValidationError
        with self.assertRaises(ValidationError):
            bord.action_valider()

        bord.action_recuperer_factures()
        self.assertIn(f_tp, bord.facture_ids)
        self.assertNotIn(f_remb, bord.facture_ids)
        self.assertAlmostEqual(bord.montant_cnam_demande, f_tp.montant_cnam_cabinet, places=2)

        # Validation + Envoi + Paiement
        bord.action_valider()
        self.assertEqual(bord.state, 'done')

        # Immutabilité unlink et modification date_debut sur bordereau non-brouillon
        with self.assertRaises(ValidationError):
            bord.unlink()
        with self.assertRaises(ValidationError):
            bord.write({'date_debut': debut - timedelta(days=1)})

        bord.action_envoyer()
        self.assertEqual(bord.state, 'sent')
        self.assertEqual(f_tp.statut_cnam, 'envoye')

        bord.action_marquer_paye()
        self.assertEqual(bord.state, 'paid')
        self.assertEqual(f_tp.statut_cnam, 'paye')

        # Rejet structuré sur un second bordereau
        f_tp2 = self._make_facture(p_tp, self.param_c, date_facture=today)
        f_tp2.action_valider()
        bord2 = self.Bordereau.create({'date_debut': debut, 'date_fin': fin})
        bord2.action_recuperer_factures()
        bord2.write({'code_motif_rejet': 'droits_expires', 'motif_rejet': 'Test rejet CNAM'})
        bord2.action_rejeter()
        self.assertEqual(bord2.state, 'rejected')
        self.assertEqual(f_tp2.statut_cnam, 'rejete')

        stats = self.Bordereau.get_cnam_dashboard_stats(month=today.month, year=today.year)
        self.assertGreaterEqual(stats['payes']['count'], 1)
        self.assertTrue(any(r['name'] == bord2.name for r in stats['rejetes']))
