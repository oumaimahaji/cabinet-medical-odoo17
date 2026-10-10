# -*- coding: utf-8 -*-
import sys
import os
import unittest

odoo_dir = r"c:\odoo - Copie\odoo"
if odoo_dir not in sys.path:
    sys.path.insert(0, odoo_dir)

class MockFactureSet(object):
    def __init__(self):
        self.records = []

    def create(self, vals):
        consultation_id = vals.get('consultation_id')
        if consultation_id:
            for r in self.records:
                if r.get('active', True) and r.get('consultation_id') == consultation_id:
                    raise ValueError(f"Une consultation (ID {consultation_id}) ne peut être rattachée qu'à une seule facture.")
        rec = dict(vals)
        rec['id'] = len(self.records) + 1
        rec['active'] = vals.get('active', True)
        self.records.append(rec)
        return rec

    def write(self, rec, vals):
        new_consultation_id = vals.get('consultation_id', rec.get('consultation_id'))
        if new_consultation_id:
            for r in self.records:
                if r['id'] != rec['id'] and r.get('active', True) and r.get('consultation_id') == new_consultation_id:
                    raise ValueError(f"Une consultation (ID {new_consultation_id}) ne peut être rattachée qu'à une seule facture.")
        rec.update(vals)
        return True

class TestUniqueConsultationFacture(unittest.TestCase):
    """Tests unitaires isolés d'unicité Consultation - Facture."""

    def setUp(self):
        self.facture_set = MockFactureSet()

    def test_01_creation_facture_normale(self):
        """Vérifie la création normale d'une facture pour une consultation."""
        f1 = self.facture_set.create({'patient_id': 1, 'consultation_id': 100})
        self.assertEqual(f1['consultation_id'], 100)

    def test_02_modification_consultation_facture(self):
        """Vérifie la réaffectation d'une facture à une consultation libre."""
        f1 = self.facture_set.create({'patient_id': 1, 'consultation_id': 100})
        self.facture_set.write(f1, {'consultation_id': 101})
        self.assertEqual(f1['consultation_id'], 101)

    def test_03_detachement_facture(self):
        """Vérifie le détachement d'une facture (consultation_id = False)."""
        f1 = self.facture_set.create({'patient_id': 1, 'consultation_id': 100})
        self.facture_set.write(f1, {'consultation_id': False})
        self.assertFalse(f1['consultation_id'])

    def test_04_rejet_doublon_creation(self):
        """Vérifie qu'une deuxième facture pour la même consultation est rejetée."""
        self.facture_set.create({'patient_id': 1, 'consultation_id': 100})
        with self.assertRaises(ValueError):
            self.facture_set.create({'patient_id': 1, 'consultation_id': 100})

    def test_05_rejet_doublon_modification(self):
        """Vérifie que l'attribution d'une consultation déjà occupée est rejetée."""
        self.facture_set.create({'patient_id': 1, 'consultation_id': 100})
        f2 = self.facture_set.create({'patient_id': 1, 'consultation_id': 101})
        with self.assertRaises(ValueError):
            self.facture_set.write(f2, {'consultation_id': 100})
