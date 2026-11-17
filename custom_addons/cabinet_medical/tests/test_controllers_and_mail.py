# -*- coding: utf-8 -*-
import base64
import io
import json
from datetime import date, timedelta
from PIL import Image
from odoo.exceptions import AccessError
from odoo.tests.common import HttpCase, TransactionCase, tagged


def _make_valid_png_b64():
    buf = io.BytesIO()
    Image.new('RGB', (2, 2), color='blue').save(buf, format='PNG')
    return base64.b64encode(buf.getvalue())


SAMPLE_PNG_B64 = _make_valid_png_b64()


@tagged('post_install', '-at_install', 'cabinet_controllers')
class TestControllersWebAndPortal(HttpCase):
    """Tests HTTP / JSON-RPC réels des contrôleurs main.py et portal.py."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Patient = cls.env['cabinet.patient']
        cls.Appointment = cls.env['cabinet.rendezvous']
        cls.Consultation = cls.env['cabinet.consultation']
        cls.Prescription = cls.env['cabinet.prescription']
        cls.Facture = cls.env['cabinet.facture']

        group_sec = cls.env.ref('cabinet_medical.group_secretaire')
        group_med = cls.env.ref('cabinet_medical.group_medecin')
        group_portal = cls.env.ref('base.group_portal')

        cls.pwd = 'TestPass123!'

        cls.user_sec = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Secrétaire Controller Test',
            'login': 'sec_ctrl_test@cabinet.local',
            'email': 'sec_ctrl_test@cabinet.local',
            'password': cls.pwd,
            'groups_id': [(6, 0, [group_sec.id])],
        })
        cls.user_med = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Médecin Controller Test',
            'login': 'med_ctrl_test@cabinet.local',
            'email': 'med_ctrl_test@cabinet.local',
            'password': cls.pwd,
            'groups_id': [(6, 0, [group_med.id])],
            'signature_medecin': SAMPLE_PNG_B64,
        })
        cls.user_portal_a = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Patient Portail A',
            'login': 'portal_a_test@cabinet.local',
            'email': 'portal_a_test@cabinet.local',
            'password': cls.pwd,
            'groups_id': [(6, 0, [group_portal.id])],
        })
        cls.user_portal_b = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Patient Portail B',
            'login': 'portal_b_test@cabinet.local',
            'email': 'portal_b_test@cabinet.local',
            'password': cls.pwd,
            'groups_id': [(6, 0, [group_portal.id])],
        })

        cls.patient_a = cls.Patient.create({
            'name': 'PATIENT PORTAIL ALPHA',
            'cin': '77330001',
            'telephone': '22330001',
            'user_id': cls.user_portal_a.id,
            'allergies': 'ALLERGIE_UNIQUE_ALPHA',
            'antecedents': 'ANTECEDENT_ALPHA',
            'traitements_chroniques': 'TRAITEMENT_ALPHA',
        })
        cls.patient_b = cls.Patient.create({
            'name': 'PATIENT PORTAIL BETA',
            'cin': '77330002',
            'telephone': '22330002',
            'user_id': cls.user_portal_b.id,
            'allergies': 'ALLERGIE_SECRETE_BETA',
        })

        cls.future_date = date(2099, 2, 12)  # Jeudi
        cls.rdv_a = cls.Appointment.create({
            'patient_id': cls.patient_a.id,
            'date': cls.future_date,
            'heure': 10.0,
            'motif_rapide': 'MOTIF_RDV_ALPHA',
        })
        cls.rdv_b = cls.Appointment.create({
            'patient_id': cls.patient_b.id,
            'date': cls.future_date,
            'heure': 11.0,
            'motif_rapide': 'MOTIF_RDV_BETA',
        })

        cls.consult_a = cls.Consultation.create({
            'patient_id': cls.patient_a.id,
            'motif': 'Consultation Portail Alpha',
        })
        cls.consult_b = cls.Consultation.create({
            'patient_id': cls.patient_b.id,
            'motif': 'Consultation Portail Beta',
        })

        # Ordonnance signée de A, brouillon de A, signée de B
        cls.ordo_a_signed = cls.Prescription.create({
            'consultation_id': cls.consult_a.id,
            'ordonnance_line_ids': [(0, 0, {
                'medicament': 'DOLIPRANE_ALPHA',
                'dosage': '500mg',
                'posologie': '1 comprimé matin et soir',
            })],
        })
        cls.ordo_a_signed.action_apply_signature(cls.user_med)

        cls.ordo_a_draft = cls.Prescription.create({
            'consultation_id': cls.consult_a.id,
            'ordonnance_line_ids': [(0, 0, {
                'medicament': 'BROUILLON_INVISIBLE_ALPHA',
                'dosage': '200mg',
                'posologie': '1 comprimé par jour',
            })],
        })

        cls.ordo_b_signed = cls.Prescription.create({
            'consultation_id': cls.consult_b.id,
            'ordonnance_line_ids': [(0, 0, {
                'medicament': 'MEDICAMENT_SECRET_BETA',
                'dosage': '1g',
                'posologie': '1 comprimé par jour',
            })],
        })
        cls.ordo_b_signed.action_apply_signature(cls.user_med)

        cls.facture_a = cls.Facture.create({
            'patient_id': cls.patient_a.id,
            'consultation_id': cls.consult_a.id,
        })
        cls.facture_b = cls.Facture.create({
            'patient_id': cls.patient_b.id,
            'consultation_id': cls.consult_b.id,
        })

    def _json_rpc(self, url, params):
        resp = self.url_open(
            url,
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': params}),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 200)
        return resp.json()

    def test_01_main_calendar_and_banner_routes(self):
        """Vérifie /cabinet_medical/get_calendar_data et /cabinet_medical/appointment_banner."""
        self.authenticate(self.user_sec.login, self.pwd)

        res_cal = self._json_rpc('/cabinet_medical/get_calendar_data', {
            'month': '2099-02',
            'selected_date': '2099-02-12',
        })
        result = res_cal.get('result', {})
        self.assertEqual(result.get('month'), '2099-02')
        self.assertIn('2099-02-12', result.get('month_data', {}))
        # Un dimanche (2099-02-15) doit être fermé
        self.assertEqual(result['month_data']['2099-02-15']['status'], 'closed')

        day_slots = {d['heure']: d for d in result.get('day_data', [])}
        self.assertFalse(day_slots[10.0]['is_free'])
        self.assertFalse(day_slots[11.0]['is_free'])
        self.assertTrue(day_slots[9.0]['is_free'])

        res_banner = self._json_rpc('/cabinet_medical/appointment_banner', {})
        self.assertIn('cabinet_calendar_app', res_banner.get('result', {}).get('html', ''))

    def test_02_main_auth_signup_and_reset_password_routes(self):
        """Vérifie l'accessibilité publique des routes /web/reset_password et /web/signup."""
        resp_reset = self.url_open('/web/reset_password')
        self.assertIn(resp_reset.status_code, (200, 404))

        resp_signup = self.url_open('/web/signup')
        self.assertIn(resp_signup.status_code, (200, 303))

    def test_03_portal_isolation_patient_a_vs_patient_b(self):
        """Vérifie que Patient A ne voit que ses propres données sur /my/rendezvous, /my/ordonnances, /my/factures et /my/dossier."""
        self.authenticate(self.user_portal_a.login, self.pwd)

        # 1. /my/rendezvous
        r_rdv = self.url_open('/my/rendezvous')
        self.assertEqual(r_rdv.status_code, 200)
        body_rdv = r_rdv.text
        self.assertIn('12/02/2099', body_rdv)
        self.assertNotIn('PATIENT PORTAIL BETA', body_rdv)

        # 2. /my/ordonnances : uniquement les ordonnances signées de A
        r_ordo = self.url_open('/my/ordonnances')
        self.assertEqual(r_ordo.status_code, 200)
        body_ordo = r_ordo.text
        self.assertIn('DOLIPRANE_ALPHA', body_ordo)
        self.assertNotIn('BROUILLON_INVISIBLE_ALPHA', body_ordo)
        self.assertNotIn('MEDICAMENT_SECRET_BETA', body_ordo)

        # 3. /my/ordonnances/download/<ordo_b> -> redirigé vers /my/ordonnances (pas de PDF)
        r_dl_b = self.url_open(f'/my/ordonnances/download/{self.ordo_b_signed.id}', allow_redirects=False)
        self.assertIn(r_dl_b.status_code, (302, 303))
        self.assertIn('/my/ordonnances', r_dl_b.headers.get('Location', ''))

        # 4. /my/factures : uniquement la facture de A
        r_fac = self.url_open('/my/factures')
        self.assertEqual(r_fac.status_code, 200)
        body_fac = r_fac.text
        self.assertIn(self.facture_a.name, body_fac)
        self.assertNotIn(self.facture_b.name, body_fac)

        # 5. /my/dossier : données déclaratives de A uniquement, aucun champ IA exposé
        r_dos = self.url_open('/my/dossier')
        self.assertEqual(r_dos.status_code, 200)
        body_dos = r_dos.text
        self.assertIn('ALLERGIE_UNIQUE_ALPHA', body_dos)
        self.assertNotIn('ALLERGIE_SECRETE_BETA', body_dos)
        self.assertNotIn('ia_fingerprint', body_dos)

    def test_04_portal_orm_isolation_and_role_access(self):
        """Vérifie les record rules portail et les droits médecin/secrétaire."""
        # Portail A ne peut pas lire les enregistrements de Patient B via l'ORM
        p_b_search = self.Patient.with_user(self.user_portal_a).search([('id', '=', self.patient_b.id)])
        self.assertFalse(p_b_search)

        f_b_search = self.Facture.with_user(self.user_portal_a).search([('id', '=', self.facture_b.id)])
        self.assertFalse(f_b_search)

        # Portail A ne peut pas créer une facture
        with self.assertRaises(AccessError):
            self.Facture.with_user(self.user_portal_a).create({'patient_id': self.patient_a.id})

        # Médecin peut lire les factures mais ne peut pas créer de facture (perm_create=0)
        self.assertTrue(self.Facture.with_user(self.user_med).browse(self.facture_a.id).name)
        with self.assertRaises(AccessError):
            self.Facture.with_user(self.user_med).create({'patient_id': self.patient_a.id})


@tagged('post_install', '-at_install', 'cabinet_controllers')
class TestIrMailServerLogo(TransactionCase):
    """Tests d'intégration pour models/ir_mail_server.py (build_email cid:logo_cabinet)."""

    def test_01_build_email_attaches_inline_logo_cid(self):
        """Vérifie que build_email attache le logo société en inline CID quand cid:logo_cabinet est référencé."""
        self.env.company.sudo().write({'logo': SAMPLE_PNG_B64})
        mail_server = self.env['ir.mail_server']

        msg_with_cid = mail_server.build_email(
            email_from='cabinet@example.com',
            email_to=['patient@example.com'],
            subject='Test Logo CID',
            body='<p>Bonjour <img src="cid:logo_cabinet"/></p>',
            subtype='html',
        )
        cids = [part.get('Content-ID') for part in msg_with_cid.walk() if part.get('Content-ID')]
        self.assertEqual(cids.count('<logo_cabinet>'), 1)

        # Sans référence cid:logo_cabinet, aucune pièce jointe logo_cabinet n'est ajoutée
        msg_without_cid = mail_server.build_email(
            email_from='cabinet@example.com',
            email_to=['patient@example.com'],
            subject='Test Sans Logo',
            body='<p>Bonjour sans logo</p>',
            subtype='html',
        )
        cids_none = [part.get('Content-ID') for part in msg_without_cid.walk() if part.get('Content-ID')]
        self.assertNotIn('<logo_cabinet>', cids_none)

