# -*- coding: utf-8 -*-
import base64
from odoo.exceptions import ValidationError, AccessError
from odoo.tests.common import TransactionCase, tagged


# PNG 1x1 valide minimal encodé en base64 pour l'image de signature médecin
SAMPLE_SIGNATURE_B64 = base64.b64encode(
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00'
    b'\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)


@tagged('post_install', '-at_install', 'cabinet_signature')
class TestSignatureOrdonnance(TransactionCase):
    """Tests d'intégration : Signature électronique des ordonnances, PIN et verrouillage."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Patient = cls.env['cabinet.patient']
        cls.Consultation = cls.env['cabinet.consultation']
        cls.Prescription = cls.env['cabinet.prescription']
        cls.PrescriptionLine = cls.env['cabinet.prescription.line']
        cls.SignWizard = cls.env['cabinet.prescription.sign.wizard']

        group_med = cls.env.ref('cabinet_medical.group_medecin')
        group_sec = cls.env.ref('cabinet_medical.group_secretaire')

        cls.user_medecin = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Dr. Signataire Test',
            'login': 'dr_sign_test@cabinet.local',
            'email': 'dr_sign_test@cabinet.local',
            'groups_id': [(6, 0, [group_med.id])],
        })
        cls.user_medecin.with_user(cls.user_medecin).set_signature_pin('1234')
        cls.user_medecin.sudo().write({'signature_medecin': SAMPLE_SIGNATURE_B64})

        cls.user_medecin_sans_sig = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Dr. Sans Signature',
            'login': 'dr_no_sig_test@cabinet.local',
            'email': 'dr_no_sig_test@cabinet.local',
            'groups_id': [(6, 0, [group_med.id])],
        })
        cls.user_medecin_sans_sig.with_user(cls.user_medecin_sans_sig).set_signature_pin('5678')

        cls.user_medecin_sans_pin = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Dr. Sans PIN',
            'login': 'dr_no_pin_test@cabinet.local',
            'email': 'dr_no_pin_test@cabinet.local',
            'groups_id': [(6, 0, [group_med.id])],
            'signature_medecin': SAMPLE_SIGNATURE_B64,
        })

        cls.user_secretaire = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Secrétaire Non Signataire',
            'login': 'sec_no_sign_test@cabinet.local',
            'email': 'sec_no_sign_test@cabinet.local',
            'groups_id': [(6, 0, [group_sec.id])],
        })

        cls.patient = cls.Patient.create({
            'name': 'Patient Ordonnance Signature',
            'cin': '77998811',
            'telephone': '22665544',
        })
        cls.consultation = cls.Consultation.create({
            'patient_id': cls.patient.id,
            'motif': 'Consultation pour test signature ordonnance',
        })

    def _create_ordonnance(self, with_line=True):
        vals = {
            'consultation_id': self.consultation.id,
            'instructions': 'Prendre après les repas.',
        }
        if with_line:
            vals['ordonnance_line_ids'] = [(0, 0, {
                'medicament': 'Paracétamol',
                'dosage': '500mg',
                'posologie': '1 comprimé 3 fois par jour',
                'duree': '5 jours',
            })]
        else:
            vals['ordonnance_line_ids'] = []
        return self.Prescription.with_user(self.user_medecin).create(vals)

    def test_01_signature_pin_correct_et_verrouillage(self):
        """1 & 5. Signature réussie avec PIN correct : copie signature, état 'signed' et verrouillage."""
        ordo = self._create_ordonnance()
        action = ordo.with_user(self.user_medecin).action_open_sign_wizard()
        self.assertEqual(action['res_model'], 'cabinet.prescription.sign.wizard')

        wizard = self.SignWizard.with_user(self.user_medecin).create({
            'prescription_id': ordo.id,
            'pin': '1234',
        })
        res = wizard.action_confirm_signature()
        self.assertEqual(res['type'], 'ir.actions.client')
        self.assertEqual(res['tag'], 'display_notification')

        self.assertEqual(ordo.state, 'signed')
        self.assertTrue(ordo.is_signed)
        self.assertTrue(ordo.is_validated)
        self.assertEqual(ordo.medecin_signataire_id, self.user_medecin)
        self.assertTrue(ordo.date_signature)
        self.assertEqual(ordo.signature_image, self.user_medecin.signature_medecin)

        # Une ordonnance déjà signée ne peut pas être re-signée
        with self.assertRaises(ValidationError):
            ordo.action_apply_signature(self.user_medecin)

    def test_02_rejet_pin_incorrect(self):
        """2. Le wizard refuse la signature si le PIN saisi est incorrect."""
        ordo = self._create_ordonnance()
        wizard = self.SignWizard.with_user(self.user_medecin).create({
            'prescription_id': ordo.id,
            'pin': '9999',
        })
        with self.assertRaises(ValidationError) as ctx:
            wizard.action_confirm_signature()
        self.assertIn('incorrect', str(ctx.exception).lower())
        self.assertEqual(ordo.state, 'draft')
        self.assertFalse(ordo.is_signed)

    def test_03_refus_pin_absent_ou_invalide(self):
        """3. Refus si PIN non configuré sur le profil médecin ou format PIN invalide."""
        # Format invalide lors de set_signature_pin
        with self.assertRaises(ValidationError):
            self.user_medecin_sans_pin.with_user(self.user_medecin_sans_pin).set_signature_pin('12')
        with self.assertRaises(ValidationError):
            self.user_medecin_sans_pin.with_user(self.user_medecin_sans_pin).set_signature_pin('abcd')

        # Médecin sans PIN configuré
        ordo = self._create_ordonnance()
        with self.assertRaises(ValidationError):
            ordo.with_user(self.user_medecin_sans_pin).action_open_sign_wizard()

        wizard = self.SignWizard.with_user(self.user_medecin_sans_pin).create({
            'prescription_id': ordo.id,
            'pin': '1234',
        })
        with self.assertRaises(ValidationError):
            wizard.action_confirm_signature()
        self.assertEqual(ordo.state, 'draft')

    def test_04_refus_sans_signature_medecin_configuree(self):
        """4. Refus de signer si l'image de signature du médecin n'est pas configurée."""
        ordo = self._create_ordonnance()
        with self.assertRaises(ValidationError):
            ordo.with_user(self.user_medecin_sans_sig).action_open_sign_wizard()

        wizard = self.SignWizard.with_user(self.user_medecin_sans_sig).create({
            'prescription_id': ordo.id,
            'pin': '5678',
        })
        with self.assertRaises(ValidationError):
            wizard.action_confirm_signature()

        with self.assertRaises(ValidationError):
            ordo.action_apply_signature(self.user_medecin_sans_sig)

    def test_05_refus_signature_ordonnance_vide(self):
        """Impossible d'ouvrir le wizard de signature sur une ordonnance sans médicament."""
        ordo_vide = self._create_ordonnance(with_line=False)
        with self.assertRaises(ValidationError):
            ordo_vide.with_user(self.user_medecin).action_open_sign_wizard()

    def test_06_immutabilite_ordonnance_signee_write_unlink_lignes(self):
        """6. Une ordonnance signée ne peut être ni modifiée ni supprimée (lignes incluses)."""
        ordo = self._create_ordonnance()
        wizard = self.SignWizard.with_user(self.user_medecin).create({
            'prescription_id': ordo.id,
            'pin': '1234',
        })
        wizard.action_confirm_signature()

        # Modification des champs interdite
        with self.assertRaises(ValidationError):
            ordo.with_user(self.user_medecin).write({'instructions': 'Tentative modification'})

        # Suppression et annulation interdites
        with self.assertRaises(ValidationError):
            ordo.with_user(self.user_medecin).unlink()
        with self.assertRaises(ValidationError):
            ordo.with_user(self.user_medecin).action_cancel_prescription()

        # Ajout / modification / suppression / archivage de ligne interdits
        line = ordo.ordonnance_line_ids[0]
        with self.assertRaises(ValidationError):
            self.PrescriptionLine.with_user(self.user_medecin).create({
                'prescription_id': ordo.id,
                'medicament': 'Ibuprofène',
                'dosage': '400mg',
                'posologie': '1 comprimé si douleur',
            })
        with self.assertRaises(ValidationError):
            line.with_user(self.user_medecin).write({'dosage': '1000mg'})
        with self.assertRaises(ValidationError):
            line.with_user(self.user_medecin).unlink()
        with self.assertRaises(ValidationError):
            line.with_user(self.user_medecin).action_archive()

        # Seul l'archivage global (active=False) de l'ordonnance est autorisé
        ordo.with_user(self.user_medecin).write({'active': False})
        self.assertFalse(ordo.active)

    def test_07_droits_acces_seul_medecin_autorise(self):
        """7. Une secrétaire (non médecin) ne peut ni ouvrir le wizard ni confirmer la signature."""
        ordo = self._create_ordonnance()

        with self.assertRaises(AccessError):
            ordo.with_user(self.user_secretaire).action_open_sign_wizard()

        # Même si le wizard est instancié, action_confirm_signature bloque en AccessError
        wizard = self.SignWizard.sudo().create({
            'prescription_id': ordo.id,
            'pin': '1234',
        })
        with self.assertRaises(AccessError):
            wizard.with_user(self.user_secretaire).action_confirm_signature()
        self.assertEqual(ordo.state, 'draft')
