import unittest
import os
import sys
from unittest.mock import MagicMock

addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(addon_dir)

# Simulation des imports Odoo
def mock_decorator(*args, **kwargs):
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return args[0]
    def wrapper(fn):
        return fn
    return wrapper

mock_odoo = MagicMock()
mock_odoo.modules.get_module_resource = lambda mod, *args: os.path.join(addon_dir, *args) if mod == 'cabinet_medical' else None

class MockRecordSet(list):
    def __iter__(self): return super().__iter__()
    def __len__(self): return super().__len__()
    def exists(self): return bool(self)
    def ensure_one(self):
        if len(self) != 1: raise ValueError('Expected singleton')
        return self[0]
    def write(self, vals):
        for r in self: r.write(vals)
        return True
    def unlink(self): return True
    def with_context(self, *args, **kwargs):
        if self: return self[0].with_context(*args, **kwargs)
        return self

class MockModel:
    _name = ''
    def __init__(self, **kwargs):
        self._context = {}
        self.env = MagicMock()
        self.env.context = self._context
        self.ia_statut = 'non_verifie'
        self.ia_message = False
        self.ia_fingerprint = False
        self.is_validated = False
        self.create_date = False
        self.ordonnance_line_ids = MockRecordSet([])
        self.date_prescription = False
        self.patient_id = False
        self.consultation_id = False
        self.active = True
        self._parent_record = None
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __iter__(self): yield self
    def __len__(self): return 1
    def __bool__(self): return True

    def with_context(self, *args, **kwargs):
        ctx = dict(getattr(self, '_context', {}))
        if args and isinstance(args[0], dict): ctx.update(args[0])
        ctx.update(kwargs)
        clone = object.__new__(self.__class__)
        clone.__dict__.update(self.__dict__)
        clone._context = ctx
        clone.env = MagicMock()
        clone.env.context = ctx
        clone._parent_record = self
        return clone

    def create(self, vals_list):
        if isinstance(vals_list, dict): vals_list = [vals_list]
        records = []
        for vals in vals_list:
            r = self.__class__(**vals)
            r._context = dict(self._context)
            r.env = MagicMock()
            r.env.context = r._context
            records.append(r)
        return MockRecordSet(records)

    def write(self, vals):
        for k, v in vals.items():
            setattr(self, k, v)
            if getattr(self, '_parent_record', None):
                setattr(self._parent_record, k, v)
        return True

    def unlink(self): return True
    def ensure_one(self): return self

mock_models = MagicMock()
mock_models.Model = MockModel
mock_models.AbstractModel = MockModel
mock_odoo.models = mock_models

mock_api = MagicMock()
mock_api.onchange = mock_decorator
mock_api.constrains = mock_decorator
mock_api.depends = mock_decorator
mock_api.model = mock_decorator
mock_api.model_create_multi = mock_decorator
mock_odoo.api = mock_api

def mock_selection(*args, **kwargs): return MagicMock()
mock_fields = MagicMock()
mock_fields.Selection = mock_selection
mock_fields.Char = MagicMock
mock_fields.Text = MagicMock
mock_fields.Date = MagicMock
mock_fields.Boolean = MagicMock
mock_fields.Many2one = MagicMock
mock_fields.One2many = MagicMock
mock_fields.Integer = MagicMock

sys.modules['odoo'] = mock_odoo
sys.modules['odoo.modules'] = mock_odoo.modules
sys.modules['odoo.fields'] = mock_fields
sys.modules['odoo.models'] = mock_models
sys.modules['odoo.api'] = mock_api
sys.modules['odoo.exceptions'] = MagicMock()
sys.modules['odoo.exceptions'].ValidationError = type('ValidationError', (Exception,), {})

import importlib.util
presc_path = os.path.join(addon_dir, 'models', 'prescription.py')
spec = importlib.util.spec_from_file_location("models.prescription", presc_path)
prescription_module = importlib.util.module_from_spec(spec)
sys.modules["models.prescription"] = prescription_module
spec.loader.exec_module(prescription_module)

_get_bdpm_ontology = prescription_module._get_bdpm_ontology


class TestBDPMOntology(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Initialise le cache BDPM une seule fois pour tous les tests
        cls.med_to_family = _get_bdpm_ontology()

    def test_penicillines(self):
        # Vérification des cas critiques de pénicillines
        self.assertEqual(self.med_to_family.get("amoxicilline"), "penicilline")
        self.assertEqual(self.med_to_family.get("augmentin"), "penicilline")
        # Les DCI complètes
        self.assertEqual(self.med_to_family.get("amoxicilline trihydratee"), "penicilline")
        self.assertEqual(self.med_to_family.get("cloxacilline sodique"), "penicilline")
        
    def test_macrolides(self):
        self.assertEqual(self.med_to_family.get("azithromycine"), "macrolide")
        self.assertEqual(self.med_to_family.get("clarithromycine"), "macrolide")
        self.assertEqual(self.med_to_family.get("erythromycine"), "macrolide")
        self.assertEqual(self.med_to_family.get("josamycine"), "macrolide")

    def test_faux_positifs_macrolides(self):
        # Ces médicaments se terminent par "MYCINE" mais NE SONT PAS des macrolides
        self.assertNotEqual(self.med_to_family.get("vancomycine"), "macrolide")
        self.assertNotEqual(self.med_to_family.get("clindamycine"), "macrolide")
        self.assertNotEqual(self.med_to_family.get("daptomycine"), "macrolide")

    def test_sulfamides(self):
        self.assertEqual(self.med_to_family.get("sulfamethoxazole"), "sulfamide")
        self.assertEqual(self.med_to_family.get("sulfadiazine"), "sulfamide")
        
    def test_faux_positifs_sulfamides(self):
        # Ces médicaments contiennent "SULFA" (SULFATE/SULFITE) mais ne sont pas des antibiotiques sulfamides
        self.assertNotEqual(self.med_to_family.get("sulfate de fer"), "sulfamide")
        self.assertNotEqual(self.med_to_family.get("ferreux (sulfate) desseche"), "sulfamide")
        self.assertNotEqual(self.med_to_family.get("atropine (sulfate d')"), "sulfamide")

    def test_base_compatible(self):
        # S'assurer que les définitions en dur (compatibilité) sont toujours là
        self.assertEqual(self.med_to_family.get("doliprane"), "paracetamol")
        self.assertEqual(self.med_to_family.get("advil"), "ibuprofene")
        self.assertEqual(self.med_to_family.get("aspegic"), "aspirine")

    def test_complementaires(self):
        self.assertEqual(self.med_to_family.get("augmentin"), "penicilline")
        self.assertEqual(self.med_to_family.get("zithromax"), "macrolide")
        self.assertEqual(self.med_to_family.get("ceftriaxone"), "cephalosporine")
        self.assertEqual(self.med_to_family.get("ciprofloxacine"), "quinolone")
        self.assertIsNone(self.med_to_family.get("medicamentinconnu"))

if __name__ == '__main__':
    unittest.main()
