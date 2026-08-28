#!/usr/bin/env python
import sys
import os

# Ajouter le chemin d'Odoo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'odoo'))

import odoo
from odoo.tools import config as tools_config

# Charger la configuration
tools_config.parse_config(['-c', os.path.join(os.path.dirname(__file__), 'odoo', 'odoo.conf')])

# Importer après la configuration
from odoo import registry

# Initialiser le registre
db_name = tools_config['db_name']
reg = registry.Registry(db_name)

with reg.cursor() as cr:
    # Marquer le module pour suppression
    cr.execute("UPDATE ir_module_module SET state='to remove' WHERE name='muk_web_theme'")
    cr.commit()
    print("Module muk_web_theme marqué pour suppression")

    # Vérifier
    cr.execute("SELECT name, state FROM ir_module_module WHERE name='muk_web_theme'")
    result = cr.fetchone()
    if result:
        print(f"Module {result[0]} est maintenant en état: {result[1]}")
    else:
        print("Module muk_web_theme non trouvé")
