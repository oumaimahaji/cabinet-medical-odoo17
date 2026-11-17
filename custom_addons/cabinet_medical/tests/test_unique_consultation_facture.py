# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'cabinet_cnam')
class TestUniqueConsultationFacture(TransactionCase):
    """Tests d'intégration d'unicité Consultation - Facture (cardinalité 0..1)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Patient = cls.env['cabinet.patient']
        cls.Consultation = cls.env['cabinet.consultation']
        cls.Facture = cls.env['cabinet.facture']

        cls.patient = cls.Patient.create({
            'name': 'Patient Unicité Facture',
            'cin': '99004001',
        })
        cls.consult1 = cls.Consultation.create({
            'patient_id': cls.patient.id,
            'motif': 'Consultation 1 pour test unicité',
        })
        cls.consult2 = cls.Consultation.create({
            'patient_id': cls.patient.id,
            'motif': 'Consultation 2 pour test unicité',
        })

    def test_01_creation_facture_normale(self):
        """Vérifie la création normale d'une facture pour une consultation."""
        f1 = self.Facture.create({
            'patient_id': self.patient.id,
            'consultation_id': self.consult1.id,
        })
        self.assertEqual(f1.consultation_id, self.consult1)

    def test_02_modification_consultation_facture(self):
        """Vérifie la réaffectation d'une facture à une consultation libre."""
        f1 = self.Facture.create({
            'patient_id': self.patient.id,
            'consultation_id': self.consult1.id,
        })
        f1.write({'consultation_id': self.consult2.id})
        self.assertEqual(f1.consultation_id, self.consult2)

    def test_03_detachement_facture(self):
        """Vérifie le détachement d'une facture (consultation_id = False)."""
        f1 = self.Facture.create({
            'patient_id': self.patient.id,
            'consultation_id': self.consult1.id,
        })
        f1.write({'consultation_id': False})
        self.assertFalse(f1.consultation_id)

    def test_04_rejet_doublon_creation(self):
        """Vérifie qu'une deuxième facture pour la même consultation est rejetée."""
        self.Facture.create({
            'patient_id': self.patient.id,
            'consultation_id': self.consult1.id,
        })
        with self.env.cr.savepoint():
            with self.assertRaises(Exception):
                self.Facture.create({
                    'patient_id': self.patient.id,
                    'consultation_id': self.consult1.id,
                })

    def test_05_rejet_doublon_modification(self):
        """Vérifie que l'attribution d'une consultation déjà occupée est rejetée."""
        self.Facture.create({
            'patient_id': self.patient.id,
            'consultation_id': self.consult1.id,
        })
        f2 = self.Facture.create({
            'patient_id': self.patient.id,
            'consultation_id': self.consult2.id,
        })
        with self.env.cr.savepoint():
            with self.assertRaises(Exception):
                f2.write({'consultation_id': self.consult1.id})
