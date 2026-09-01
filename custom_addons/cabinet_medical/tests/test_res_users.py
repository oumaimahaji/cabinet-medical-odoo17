import unittest
import os
import sys
from unittest.mock import MagicMock

addon_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(addon_dir)

# Mock environnement Odoo
mock_odoo = MagicMock()
mock_odoo.modules.get_module_resource = lambda mod, *args: os.path.join(addon_dir, *args) if mod == 'cabinet_medical' else None

def mock_selection(*args, **kwargs):
    return MagicMock()

mock_fields = MagicMock()
mock_fields.Selection = mock_selection
mock_fields.Char = MagicMock
mock_fields.Text = MagicMock
mock_fields.Date = MagicMock
mock_fields.Boolean = MagicMock
mock_fields.Many2one = MagicMock
mock_fields.One2many = MagicMock
mock_fields.Integer = MagicMock
mock_fields.Binary = MagicMock

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
    def unlink(self):
        return True
    def with_context(self, *args, **kwargs):
        if self: return self[0].with_context(*args, **kwargs)
        return self

class MockModel:
    _name = ''
    def __init__(self, **kwargs):
        self._context = {}
        self.env = MagicMock()
        self.env.context = self._context
        self.env.user = self # default to self
        self.env.is_admin = lambda: False
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __iter__(self):
        yield self

    def __len__(self):
        return 1

    def __bool__(self):
        return True

    def sudo(self):
        return self

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
        return True

    def unlink(self):
        return True

    def ensure_one(self): return self

mock_models = MagicMock()
mock_models.Model = MockModel
mock_models.AbstractModel = MockModel

mock_odoo.models = mock_models
def mock_decorator(*args, **kwargs):
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return args[0]
    def wrapper(fn):
        return fn
    return wrapper

mock_api = MagicMock()
mock_api.onchange = mock_decorator
mock_api.constrains = mock_decorator
mock_api.depends = mock_decorator
mock_api.model = mock_decorator
mock_api.model_create_multi = mock_decorator
mock_odoo.api = mock_api

class ValidationError(Exception): pass
class AccessError(Exception): pass
mock_odoo.exceptions.ValidationError = ValidationError
mock_odoo.exceptions.AccessError = AccessError
mock_odoo.exceptions.UserError = type('UserError', (Exception,), {})

sys.modules['odoo'] = mock_odoo
sys.modules['odoo.modules'] = mock_odoo.modules
sys.modules['odoo.fields'] = mock_fields
sys.modules['odoo.models'] = mock_models
sys.modules['odoo.api'] = mock_api
sys.modules['odoo.exceptions'] = mock_odoo.exceptions


import importlib.util

res_users_path = os.path.join(addon_dir, 'models', 'res_users.py')
spec_r = importlib.util.spec_from_file_location("models.res_users", res_users_path)
res_users_module = importlib.util.module_from_spec(spec_r)
sys.modules['models.res_users'] = res_users_module
spec_r.loader.exec_module(res_users_module)

ResUsers = res_users_module.ResUsers


class TestResUsers(unittest.TestCase):
    def setUp(self):
        self.user = ResUsers(id=1, signature_medecin=False, pin_signature_hash=False)
        self.user.env.user = self.user
        
    def test_01_set_signature_pin_valid(self):
        self.assertTrue(self.user.set_signature_pin("1234"))
        self.assertTrue(self.user.pin_signature_hash)
        
    def test_02_set_signature_pin_invalid_length(self):
        with self.assertRaises(ValidationError):
            self.user.set_signature_pin("123")
        with self.assertRaises(ValidationError):
            self.user.set_signature_pin("123456789")
            
    def test_03_set_signature_pin_invalid_chars(self):
        with self.assertRaises(ValidationError):
            self.user.set_signature_pin("12a4")
            
    def test_04_set_signature_pin_access_error(self):
        other_user = ResUsers(id=2)
        other_user.env.user = self.user # I am user 1, trying to change user 2
        with self.assertRaises(AccessError):
            other_user.set_signature_pin("1234")
            
    def test_05_set_signature_pin_admin(self):
        other_user = ResUsers(id=2)
        other_user.env.user = self.user
        other_user.env.is_admin = lambda: True
        self.assertTrue(other_user.set_signature_pin("1234"))
        
    def test_06_verify_signature_pin(self):
        self.user.set_signature_pin("1234")
        self.assertTrue(self.user.verify_signature_pin("1234"))
        self.assertFalse(self.user.verify_signature_pin("4321"))
        self.assertFalse(self.user.verify_signature_pin(None))
        self.assertFalse(self.user.verify_signature_pin(""))
        
    def test_07_verify_signature_pin_no_hash(self):
        self.assertFalse(self.user.verify_signature_pin("1234"))
        
    def test_08_compute_signature_status(self):
        self.user.signature_medecin = b'imgdata'
        self.user.set_signature_pin("1234")
        self.user._compute_signature_status()
        self.assertTrue(self.user.has_signature)
        self.assertTrue(self.user.has_signature_pin)
        
    def test_09_action_clear_signature(self):
        self.user.signature_medecin = b'imgdata'
        self.user.action_clear_signature()
        self.assertFalse(self.user.signature_medecin)

    def test_10_action_clear_signature_access_error(self):
        other_user = ResUsers(id=2)
        other_user.env.user = self.user # I am user 1, trying to change user 2
        with self.assertRaises(AccessError):
            other_user.action_clear_signature()

if __name__ == '__main__':
    unittest.main()
