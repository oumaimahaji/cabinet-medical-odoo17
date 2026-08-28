#!/usr/bin/env python3
"""
Script pour créer une nouvelle base de données propre sans les références Muk
"""

import subprocess
import sys

def reset_database():
    print("Création d'une nouvelle base de données propre...")
    
    # Commandes pour créer une nouvelle base de données
    commands = [
        # Arrêter Odoo s'il est en cours d'exécution
        "taskkill /F /IM python.exe 2>nul || echo 'No Python processes found'",
        
        # Instructions pour l'utilisateur
        "echo '=== INSTRUCTIONS POUR RÉINITIALISER ==='",
        "echo '1. Ouvrez pgAdmin'",
        "echo '2. Connectez-vous à PostgreSQL',",
        "echo '3. Supprimez la base de données cabinet_medical'",
        "echo '4. Créez une nouvelle base de données cabinet_medical'",
        "echo '5. Relancez Odoo avec:'",
        "echo '   python odoo-bin --addons-path=..\\custom_addons,addons -d cabinet_medical'",
        "echo '========================================='",
        "echo 'Appuyez sur Entrée pour continuer...'",
        "pause"
    ]
    
    for cmd in commands:
        subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    reset_database()
