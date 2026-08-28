#!/usr/bin/env python
import os
import sys

# Configuration
os.environ['ODOO_CONFIG'] = r'c:\odoo - Copie\odoo\odoo.conf'

# Ajouter le chemin d'Odoo
sys.path.insert(0, r'c:\odoo - Copie\odoo')

import odoo
from odoo.tools import config
from odoo import api, registry

# Charger la configuration
config.parse_config(['-c', r'c:\odoo - Copie\odoo\odoo.conf'])

# Initialiser le registre
db_name = config['db_name']
reg = registry.Registry(db_name)

with api.Environment.manage():
    with reg.cursor() as cr:
        env = api.Environment(cr, 1, {})
        
        # Trouver le module
        module = env['ir.module.module'].search([('name', '=', 'muk_web_theme')])
        if module:
            print(f"Module found: {module.name}, state: {module.state}")
            # Marquer pour suppression
            module.button_uninstall()
            cr.commit()
            print("Module muk_web_theme marked for uninstallation")
        else:
            print("Module muk_web_theme not found")
