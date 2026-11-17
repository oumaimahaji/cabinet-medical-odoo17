# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.exceptions import ValidationError, AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'cabinet_rdv')
class TestRendezvous(TransactionCase):
    """Tests d'intégration du module Rendez-vous (models/rendezvous.py)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Appointment = cls.env['cabinet.rendezvous']
        cls.Patient = cls.env['cabinet.patient']
        cls.Consultation = cls.env['cabinet.consultation']
        cls.Notification = cls.env['cabinet.notification']
        cls.ConfigParam = cls.env['ir.config_parameter'].sudo()

        # Choisir une date future garantie travaillée et sans RDV préexistant en base
        cls.future_date = date(2099, 1, 15)    # Jeudi (weekday=3)
        cls.future_date_2 = date(2099, 1, 16)  # Vendredi (weekday=4)

        cls.patient_1 = cls.Patient.create({
            'name': 'Patient RDV Test 1',
            'cin': '77990001',
            'telephone': '22990001',
        })
        cls.patient_2 = cls.Patient.create({
            'name': 'Patient RDV Test 2',
            'cin': '77990002',
            'telephone': '22990002',
        })
        cls.patient_3 = cls.Patient.create({
            'name': 'Patient RDV Test 3',
            'cin': '77990003',
            'telephone': '22990003',
        })

        # Utilisateurs pour tester les droits d'accès (secrétaire vs médecin)
        group_sec = cls.env.ref('cabinet_medical.group_secretaire')
        group_med = cls.env.ref('cabinet_medical.group_medecin')
        cls.user_secretaire = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Secrétaire Test RDV',
            'login': 'sec_test_rdv@cabinet.local',
            'email': 'sec_test_rdv@cabinet.local',
            'groups_id': [(6, 0, [group_sec.id])],
        })
        cls.user_medecin = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Médecin Test RDV',
            'login': 'med_test_rdv@cabinet.local',
            'email': 'med_test_rdv@cabinet.local',
            'groups_id': [(6, 0, [group_med.id])],
        })

    def test_01_check_patient_info_and_auto_create_patient(self):
        """Vérifie _check_patient_info et la création automatique de patient depuis patient_name."""
        with self.assertRaises(ValidationError):
            self.Appointment.create({
                'date': self.future_date,
                'heure': 9.0,
            })

        rdv_rapide = self.Appointment.create({
            'patient_name': 'Nouveau Patient Rapide Test',
            'date': self.future_date,
            'heure': 9.5,
        })
        self.assertTrue(rdv_rapide.patient_id)
        self.assertEqual(rdv_rapide.patient_id.name, 'NOUVEAU PATIENT RAPIDE TEST')

    def test_02_duplicate_appointment_and_cancelled_slot_freed(self):
        """Vérifie _check_duplicate_appointment : blocage doublon actif et libération si annulé/absent."""
        rdv1 = self.Appointment.create({
            'patient_id': self.patient_1.id,
            'date': self.future_date,
            'heure': 10.0,
        })

        # Même date et même heure -> ValidationError
        with self.assertRaises(ValidationError):
            self.Appointment.create({
                'patient_id': self.patient_2.id,
                'date': self.future_date,
                'heure': 10.0,
            })

        # Si le premier RDV est annulé, le créneau est libéré
        rdv1.with_user(self.user_secretaire).action_annuler()
        self.assertEqual(rdv1.state, 'annule')
        rdv2 = self.Appointment.create({
            'patient_id': self.patient_2.id,
            'date': self.future_date,
            'heure': 10.0,
        })
        self.assertEqual(rdv2.heure, 10.0)

    def test_03_patient_same_day_constraint(self):
        """Vérifie _check_patient_same_day : un patient ne peut pas avoir 2 RDV actifs le même jour."""
        rdv1 = self.Appointment.create({
            'patient_id': self.patient_1.id,
            'date': self.future_date,
            'heure': 11.0,
        })
        with self.assertRaises(ValidationError):
            self.Appointment.create({
                'patient_id': self.patient_1.id,
                'date': self.future_date,
                'heure': 11.5,
            })

        # Si rdv1 est marqué absent, le patient peut reprendre un RDV le même jour
        rdv1.with_user(self.user_secretaire).action_patient_absent()
        rdv2 = self.Appointment.create({
            'patient_id': self.patient_1.id,
            'date': self.future_date,
            'heure': 11.5,
        })
        self.assertEqual(rdv2.state, 'en_attente')

    def test_04_past_date_constraint_and_past_unclosed(self):
        """Vérifie _check_date_not_in_past et la détection des RDV passés non clôturés."""
        past_date = date.today() - timedelta(days=3)
        with self.assertRaises(ValidationError):
            self.Appointment.create({
                'patient_id': self.patient_1.id,
                'date': past_date,
                'heure': 9.0,
            })

        # Avec skip_past_date_check (ex: migration/données historiques), is_past_unclosed doit être True
        rdv_past = self.Appointment.with_context(skip_past_date_check=True).create({
            'patient_id': self.patient_1.id,
            'date': past_date,
            'heure': 9.0,
        })
        self.assertTrue(rdv_past.is_past_unclosed)
        self.assertGreaterEqual(self.Appointment.get_unclosed_past_count(), 1)
        found = self.Appointment.search([('is_past_unclosed', '=', True), ('id', '=', rdv_past.id)])
        self.assertEqual(found, rdv_past)

    def test_05_limits_normal_and_urgence(self):
        """Vérifie _check_appointments_limit et _check_urgence_limit."""
        self.ConfigParam.set_param('cabinet.max_rdv_normal', '2')
        self.ConfigParam.set_param('cabinet.max_rdv_urgence', '1')

        p4 = self.Patient.create({'name': 'Patient Limite 4', 'cin': '77990004'})
        p5 = self.Patient.create({'name': 'Patient Limite 5', 'cin': '77990005'})

        self.Appointment.create({
            'patient_id': self.patient_1.id,
            'date': self.future_date,
            'heure': 8.0,
            'is_urgence': False,
        })
        self.Appointment.create({
            'patient_id': self.patient_2.id,
            'date': self.future_date,
            'heure': 8.5,
            'is_urgence': False,
        })
        # 3e RDV normal -> bloqué
        with self.assertRaises(ValidationError):
            self.Appointment.create({
                'patient_id': self.patient_3.id,
                'date': self.future_date,
                'heure': 9.0,
                'is_urgence': False,
            })

        # 1er RDV urgence -> autorisé
        self.Appointment.create({
            'patient_id': self.patient_3.id,
            'date': self.future_date,
            'heure': 9.0,
            'is_urgence': True,
        })
        # 2e RDV urgence -> bloqué
        with self.assertRaises(ValidationError):
            self.Appointment.create({
                'patient_id': p4.id,
                'date': self.future_date,
                'heure': 9.5,
                'is_urgence': True,
            })

        # En revanche une date différente reste disponible
        rdv_autre_jour = self.Appointment.create({
            'patient_id': p5.id,
            'date': self.future_date_2,
            'heure': 8.0,
            'is_urgence': False,
        })
        self.assertEqual(rdv_autre_jour.date, self.future_date_2)

    def test_06_slot_availability_status(self):
        """Vérifie _compute_slot_availability_status (hors heures, jour fermé, occupé, disponible)."""
        self.ConfigParam.set_param('cabinet.heure_debut', '8.0')
        self.ConfigParam.set_param('cabinet.heure_fin', '17.0')
        self.ConfigParam.set_param('cabinet.work_days', '0,1,2,3,4,5')

        # Hors heures de travail
        rdv_hors = self.Appointment.new({
            'patient_id': self.patient_1.id,
            'date': self.future_date,
            'heure': 20.0,
        })
        self.assertIn('Hors heures de travail', rdv_hors.slot_availability_status)

        # Jour non travaillé (dimanche = 6)
        dimanche = self.future_date + timedelta(days=(6 - self.future_date.weekday()))
        rdv_dim = self.Appointment.new({
            'patient_id': self.patient_1.id,
            'date': dimanche,
            'heure': 10.0,
        })
        self.assertIn('ne travaille pas ce jour', rdv_dim.slot_availability_status)

        # Créneau disponible puis occupé
        rdv_libre = self.Appointment.new({
            'patient_id': self.patient_1.id,
            'date': self.future_date,
            'heure': 14.0,
        })
        self.assertIn('Créneau disponible', rdv_libre.slot_availability_status)

        self.Appointment.create({
            'patient_id': self.patient_1.id,
            'date': self.future_date,
            'heure': 14.0,
        })
        rdv_occ = self.Appointment.new({
            'patient_id': self.patient_2.id,
            'date': self.future_date,
            'heure': 14.0,
        })
        self.assertIn('Créneau déjà occupé', rdv_occ.slot_availability_status)

    def test_07_no_show_risk_calculation_and_history(self):
        """Vérifie _compute_no_show_risk et _calculate_patient_rdv_history sur le vrai modèle."""
        # Sans patient -> score 0 et niveau False
        rdv_sans_patient = self.Appointment.new({
            'date': self.future_date,
            'heure': 10.0,
        })
        self.assertEqual(rdv_sans_patient.no_show_risk_score, 0.0)
        self.assertFalse(rdv_sans_patient.no_show_risk_level)

        # Historique : 2 RDV passés (1 absent, 1 terminé) -> taux 0.5
        d1 = date.today() - timedelta(days=20)
        d2 = date.today() - timedelta(days=10)
        self.Appointment.with_context(skip_past_date_check=True).create({
            'patient_id': self.patient_1.id,
            'date': d1,
            'heure': 9.0,
            'state': 'absent',
        })
        self.Appointment.with_context(skip_past_date_check=True).create({
            'patient_id': self.patient_1.id,
            'date': d2,
            'heure': 9.0,
            'state': 'termine',
        })

        rdv_futur = self.Appointment.create({
            'patient_id': self.patient_1.id,
            'date': self.future_date,
            'heure': 15.0,
        })
        prev_count, hist_rate = rdv_futur._calculate_patient_rdv_history(rdv_futur)
        self.assertEqual(prev_count, 2)
        self.assertAlmostEqual(hist_rate, 0.5, places=2)
        self.assertGreater(rdv_futur.no_show_risk_score, 0.0)
        self.assertIn(rdv_futur.no_show_risk_level, ('faible', 'moyen', 'eleve'))

    def test_08_state_transitions_consultation_and_access_control(self):
        """Vérifie le workflow complet : en_attente -> present -> en_consultation -> termine,
        la création/association de consultation, annulation, absence et droits d'accès."""
        rdv = self.Appointment.create({
            'patient_id': self.patient_1.id,
            'date': self.future_date,
            'heure': 10.5,
        })
        self.assertEqual(rdv.state, 'en_attente')

        # 1. Patient arrivé -> état 'present' + notification créée
        rdv.action_patient_arrive()
        self.assertEqual(rdv.state, 'present')
        notif_present = self.Notification.search([
            ('patient_id', '=', self.patient_1.id),
            ('type', '=', 'rdv_present'),
        ])
        self.assertTrue(notif_present)

        # 2. Démarrer consultation -> état 'en_consultation' + création consultation liée
        action = rdv.action_demarrer_consultation()
        self.assertEqual(rdv.state, 'en_consultation')
        self.assertEqual(action['res_model'], 'cabinet.consultation')
        consult = self.Consultation.browse(action['res_id'])
        self.assertTrue(consult.exists())
        self.assertEqual(consult.patient_id, self.patient_1)
        self.assertEqual(consult.rdv_id, rdv)

        # Re-cliquer action_ouvrir_consultation retrouve la même consultation
        open_action = rdv.action_ouvrir_consultation()
        self.assertEqual(open_action['res_id'], consult.id)

        # 3. Annulation interdite en état 'en_consultation' (même pour secrétaire)
        with self.assertRaises(ValidationError):
            rdv.with_user(self.user_secretaire).action_annuler()

        # 4. Terminer le RDV
        rdv.action_termine()
        self.assertEqual(rdv.state, 'termine')

        # 5. Contrôle d'accès médecin sur action_annuler et action_patient_absent
        rdv_autre = self.Appointment.create({
            'patient_id': self.patient_2.id,
            'date': self.future_date,
            'heure': 11.0,
        })
        with self.assertRaises(AccessError):
            rdv_autre.with_user(self.user_medecin).action_annuler()
        with self.assertRaises(AccessError):
            rdv_autre.with_user(self.user_medecin).action_patient_absent()

    def test_09_write_reschedule_notification_and_unlink_blocked(self):
        """Vérifie la notification de report lors de write() et le blocage de unlink()."""
        rdv = self.Appointment.create({
            'patient_id': self.patient_1.id,
            'date': self.future_date,
            'heure': 10.0,
        })

        # Report de l'heure -> notification rdv_reporte
        rdv.write({'heure': 16.0})
        notif_report = self.Notification.search([
            ('patient_id', '=', self.patient_1.id),
            ('type', '=', 'rdv_reporte'),
        ])
        self.assertTrue(notif_report)

        # Suppression physique toujours interdite
        with self.assertRaises(ValidationError):
            rdv.unlink()
