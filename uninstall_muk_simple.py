#!/usr/bin/env python
# -*- coding: utf-8 -*-
import psycopg2
import sys

# Configuration de la base de données (à partir de odoo.conf)
db_name = 'odoo'
db_user = 'odoo'
db_password = 'odoo123'
db_host = 'localhost'
db_port = '5432'

try:
    # Connexion à la base de données
    conn = psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port
    )
    cursor = conn.cursor()

    # Marquer le module pour suppression
    cursor.execute("UPDATE ir_module_module SET state='to remove' WHERE name='muk_web_theme'")
    conn.commit()
    print("Module muk_web_theme marked for removal")

    # Vérifier
    cursor.execute("SELECT name, state FROM ir_module_module WHERE name='muk_web_theme'")
    result = cursor.fetchone()
    if result:
        print(f"Module {result[0]} is now in state: {result[1]}")
    else:
        print("Module muk_web_theme not found")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
