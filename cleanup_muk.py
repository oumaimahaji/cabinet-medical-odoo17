#!/usr/bin/env python3
"""
Script pour nettoyer les références aux modules Muk dans la base de données
"""

import psycopg2
import sys

def cleanup_muk_modules():
    try:
        # Connexion à la base de données
        conn = psycopg2.connect(
            dbname="cabinet_medical",
            user="odoo",
            password="odoo",
            host="localhost",
            port="5432"
        )
        cursor = conn.cursor()
        
        print("Nettoyage des modules Muk dans la base de données...")
        
        # Supprimer les enregistrements des modules Muk dans ir_module_module
        cursor.execute("""
            DELETE FROM ir_module_module 
            WHERE name IN ('muk_web_theme', 'muk_web_appsbar', 'muk_web_chatter', 'muk_web_colors', 'muk_web_dialog')
        """)
        
        # Supprimer les dépendances dans ir_module_module_dependency
        cursor.execute("""
            DELETE FROM ir_module_module_dependency 
            WHERE name IN ('muk_web_theme', 'muk_web_appsbar', 'muk_web_chatter', 'muk_web_colors', 'muk_web_dialog')
        """)
        
        # Nettoyer les paramètres système
        cursor.execute("""
            DELETE FROM ir_config_parameter 
            WHERE key LIKE '%muk_%'
        """)
        
        # Nettoyer les vues qui référencent Muk
        cursor.execute("""
            DELETE FROM ir_ui_view 
            WHERE key LIKE '%muk_%' OR arch LIKE '%muk_%'
        """)
        
        # Nettoyer les menus
        cursor.execute("""
            DELETE FROM ir_ui_menu 
            WHERE name LIKE '%MuK%' OR key LIKE '%muk_%'
        """)
        
        conn.commit()
        print("Nettoyage terminé avec succès!")
        
    except Exception as e:
        print(f"Erreur: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    cleanup_muk_modules()
