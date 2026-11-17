# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'cabinet_patient_alerts')
class TestPatientCnamAlerts(TransactionCase):
    """Tests d'intégration : Dossier Patient, Cron expiration CNAM, Alertes Secrétaire et Droits d'accès."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Patient = cls.env['cabinet.patient']
        cls.Notification = cls.env['cabinet.notification']

        # Éviter tout appel réseau HTTP vers Ollama pendant _cron_check_cnam_expiration
        cls.env['ir.config_parameter'].sudo().set_param('cabinet_medical.ollama_model', '')

        group_med = cls.env.ref('cabinet_medical.group_medecin')
        group_sec = cls.env.ref('cabinet_medical.group_secretaire')

        cls.user_medecin = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Médecin Lecture Patient',
            'login': 'med_patient_test@cabinet.local',
            'email': 'med_patient_test@cabinet.local',
            'groups_id': [(6, 0, [group_med.id])],
        })
        cls.user_secretaire = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Secrétaire Gestion Patient',
            'login': 'sec_patient_test@cabinet.local',
            'email': 'sec_patient_test@cabinet.local',
            'groups_id': [(6, 0, [group_sec.id])],
        })

        today = date.today()
        # Patient expiré depuis 5 jours
        cls.p_expire = cls.Patient.create({
            'name': 'Patient CNAM Expiré Alertes',
            'cin': '77550001',
            'telephone': '22550001',
            'is_cnam': True,
            'numero_cnam': '3000000001',
            'filiere_cnam': 'privee',
            'date_validite_cnam': today - timedelta(days=5),
        })
        # Patient expirant dans 2 jours (fenêtre alerte imminente cron)
        cls.p_2j = cls.Patient.create({
            'name': 'Patient CNAM 2 Jours',
            'cin': '77550002',
            'telephone': '22550002',
            'is_cnam': True,
            'numero_cnam': '3000000002',
            'filiere_cnam': 'privee',
            'date_validite_cnam': today + timedelta(days=2),
        })
        # Patient expirant dans 7 jours (fenêtre alerte préventive cron)
        cls.p_7j = cls.Patient.create({
            'name': 'Patient CNAM 7 Jours',
            'cin': '77550003',
            'telephone': '22550003',
            'is_cnam': True,
            'numero_cnam': '3000000003',
            'filiere_cnam': 'privee',
            'date_validite_cnam': today + timedelta(days=7),
        })
        # Patient expirant dans 30 jours (couverture encore valide, hors fenêtre 7j/2j)
        cls.p_30j = cls.Patient.create({
            'name': 'Patient CNAM 30 Jours Valide',
            'cin': '77550004',
            'telephone': '22550004',
            'is_cnam': True,
            'numero_cnam': '3000000004',
            'filiere_cnam': 'privee',
            'date_validite_cnam': today + timedelta(days=30),
        })
        # Patient APCI expirée
        cls.p_apci_expire = cls.Patient.create({
            'name': 'Patient APCI Expirée Alertes',
            'cin': '77550005',
            'telephone': '22550005',
            'is_cnam': True,
            'numero_cnam': '3000000005',
            'filiere_cnam': 'privee',
            'date_validite_cnam': today + timedelta(days=60),
            'is_apci': True,
            'apci_pathologie': 'diabete',
            'numero_decision_apci': 'APCI-ALERT-05',
            'date_fin_apci': today - timedelta(days=3),
        })

    def test_01_cron_check_cnam_expiration_thresholds(self):
        """1 & 3. Vérifie _cron_check_cnam_expiration pour expiré, J-2, J-7 et valide (J+30)."""
        self.Patient._cron_check_cnam_expiration()

        notif_exp = self.Notification.search([('patient_id', '=', self.p_expire.id), ('type', '=', 'cnam')])
        self.assertEqual(len(notif_exp), 1)
        self.assertEqual(notif_exp.title, 'Couverture CNAM expirée')

        notif_2j = self.Notification.search([('patient_id', '=', self.p_2j.id), ('type', '=', 'cnam')])
        self.assertEqual(len(notif_2j), 1)
        self.assertIn('2 jours', notif_2j.title)

        notif_7j = self.Notification.search([('patient_id', '=', self.p_7j.id), ('type', '=', 'cnam')])
        self.assertEqual(len(notif_7j), 1)
        self.assertIn('7 jours', notif_7j.title)

        # Un patient valide à +30 jours ne doit recevoir aucune notification d'expiration
        notif_30j = self.Notification.search([('patient_id', '=', self.p_30j.id), ('type', '=', 'cnam')])
        self.assertEqual(len(notif_30j), 0)

    def test_02_cron_no_duplicates_and_new_due_date_triggers_alert(self):
        """4. Exécuter le cron deux fois ne crée aucun doublon, et une nouvelle échéance génère une nouvelle alerte."""
        self.Patient._cron_check_cnam_expiration()
        self.Patient._cron_check_cnam_expiration()

        # Aucune notification en double après deux exécutions
        self.assertEqual(
            self.Notification.search_count([('patient_id', '=', self.p_expire.id), ('type', '=', 'cnam')]),
            1,
        )
        self.assertEqual(
            self.Notification.search_count([('patient_id', '=', self.p_2j.id), ('type', '=', 'cnam')]),
            1,
        )
        self.assertEqual(
            self.Notification.search_count([('patient_id', '=', self.p_7j.id), ('type', '=', 'cnam')]),
            1,
        )

        # Nouvelle échéance : un patient initialement valide (J+30) passe à J+2 -> nouvelle alerte créée
        self.p_30j.write({'date_validite_cnam': date.today() + timedelta(days=2)})
        self.Patient._cron_check_cnam_expiration()
        self.assertEqual(
            self.Notification.search_count([('patient_id', '=', self.p_30j.id), ('type', '=', 'cnam')]),
            1,
        )

    def test_03_get_secretary_cnam_alerts(self):
        """2. Vérifie l'exactitude des alertes retournées par get_secretary_cnam_alerts."""
        res = self.Patient.get_secretary_cnam_alerts()
        self.assertIn('count', res)
        self.assertIn('alerts', res)
        self.assertEqual(res['count'], len(res['alerts']))

        by_key = {(a['id'], a['type']): a for a in res['alerts']}
        # Le patient valide à 30 jours ne doit jamais apparaître dans les alertes
        self.assertFalse(any(a['id'] == self.p_30j.id for a in res['alerts']))

        # Vérifier la présence des types 'expired', 'soon', 'apci' si dans le top limit
        self.assertIn((self.p_expire.id, 'expired'), by_key)
        self.assertEqual(by_key[(self.p_expire.id, 'expired')]['badge_label'], 'Expiré')
        self.assertIn((self.p_2j.id, 'soon'), by_key)
        self.assertIn((self.p_7j.id, 'soon'), by_key)
        self.assertIn((self.p_apci_expire.id, 'apci'), by_key)

    def test_04_notification_create_and_style(self):
        """3. Vérifie create_notification et les champs calculés de style sur cabinet.notification."""
        notif = self.Notification.create_notification(
            patient_id=self.p_30j.id,
            title='Test alerte CNAM',
            message='Message test CNAM',
            notif_type='cnam',
            res_url='/my/couverture',
        )
        self.assertTrue(notif.exists())
        self.assertEqual(notif.icon, 'fa-hospital-o')
        self.assertFalse(notif.is_read)

        # Patient inexistant -> retourne False sans erreur
        res_inexistant = self.Notification.create_notification(
            patient_id=-99999,
            title='Invalide',
            message='Test',
            notif_type='cnam',
        )
        self.assertFalse(res_inexistant)

    def test_05_access_rights_medecin_vs_secretaire(self):
        """5. Vérifie les droits d'accès ir.model.access.csv :
        - Secrétaire : lecture/écriture/création sur cabinet.patient, suppression physique bloquée.
        - Médecin : lecture seule sur cabinet.patient (création et écriture refusées).
        """
        # Secrétaire peut créer et modifier un patient
        p_sec = self.Patient.with_user(self.user_secretaire).create({
            'name': 'Patient Créé Par Secrétaire',
            'cin': '77550006',
        })
        p_sec.with_user(self.user_secretaire).write({'telephone': '22550006'})
        self.assertEqual(p_sec.telephone, '22550006')

        # Suppression physique interdite par Patient.unlink() (ValidationError avant ACL)
        with self.assertRaises(ValidationError):
            p_sec.with_user(self.user_secretaire).unlink()

        # Médecin peut lire le patient
        p_read = self.Patient.with_user(self.user_medecin).browse(p_sec.id)
        self.assertEqual(p_read.name, 'PATIENT CRÉÉ PAR SECRÉTAIRE')

        # Médecin ne peut ni créer ni modifier un dossier patient (perm_create=0, perm_write=0)
        with self.assertRaises(AccessError):
            self.Patient.with_user(self.user_medecin).create({
                'name': 'Patient Refusé Médecin',
                'cin': '77550007',
            })
        with self.assertRaises(AccessError):
            p_read.write({'telephone': '22550008'})
