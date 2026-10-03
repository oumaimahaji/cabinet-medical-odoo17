# -*- coding: utf-8 -*-
"""
Inspection and real test of SMTP email sending in Odoo 17.
"""
import odoo
from odoo import fields

def check_and_test_smtp():
    odoo.tools.config.parse_config([
        '-c', '/etc/odoo/odoo.conf',
        '-d', 'cabinet_medical_db',
        '--db_host', 'db',
        '--db_user', 'odoo',
        '--db_password', 'Xj1nBDVze5ZY7bn8QajNvpXz'
    ])

    reg = odoo.registry('cabinet_medical_db')
    with reg.cursor() as cr:
        env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        
        print("=" * 70)
        print("ÉTAPE 5 : INSPECTION ET TEST DE LA CONFIGURATION SMTP")
        print("=" * 70)
        
        print("\n1. PARAMÈTRES ODOO.CONF")
        print(f"  - email_from : {odoo.tools.config.get('email_from')}")
        print(f"  - smtp_server : {odoo.tools.config.get('smtp_server')}")
        print(f"  - smtp_port : {odoo.tools.config.get('smtp_port')}")
        print(f"  - smtp_ssl : {odoo.tools.config.get('smtp_ssl')}")
        
        print("\n2. SERVEURS DE MESSAGERIE CONFIGURÉS (ir.mail_server)")
        servers = env['ir.mail_server'].search([])
        print(f"  Nombre de serveurs trouvés : {len(servers)}")
        for s in servers:
            print(f"  [-] ID: {s.id} | Nom: '{s.name}'")
            print(f"      Hôte: {s.smtp_host} | Port: {s.smtp_port}")
            print(f"      Chiffrement: {s.smtp_encryption} | Utilisateur: {s.smtp_user}")
            print(f"      Séquence: {s.sequence} | Actif: {s.active}")
            try:
                res = s.test_smtp_connection()
                print(f"      -> Test de connexion socket SMTP : SUCCÈS ({res})")
            except Exception as e:
                print(f"      -> Test de connexion socket SMTP : ÉCHEC ({e})")
                
        print("\n3. TEST RÉEL D'ENVOI D'UN EMAIL VIA L'APPLICATION")
        try:
            # Create a mail.mail object and send it
            mail_vals = {
                'subject': '[Test Audit SMTP] Vérification de l\'envoi réel',
                'body_html': '<p>Ceci est un test de validation de la chaîne SMTP pour Cabinet Médical.</p>',
                'email_to': 'audit.test@cabinet.tn',
                'email_from': odoo.tools.config.get('email_from') or 'admine.hajji@gmail.com',
                'auto_delete': False,
            }
            test_mail = env['mail.mail'].create(mail_vals)
            print(f"  Email de test créé (ID: {test_mail.id})")
            
            # Send immediately
            test_mail.send(raise_exception=True)
            print(f"  Statut après send() : {test_mail.state}")
            
            if test_mail.state == 'sent':
                print("  [PASS] Email envoyé avec succès par le serveur SMTP !")
                smtp_success = True
            elif test_mail.state == 'exception':
                print(f"  [FAIL] Échec de l'envoi : {test_mail.failure_reason}")
                smtp_success = False
            else:
                print(f"  Statut de l'email : {test_mail.state}")
                smtp_success = (test_mail.state in ('sent', 'outgoing'))
        except Exception as e:
            print(f"  [FAIL] Exception lors de l'envoi SMTP : {e}")
            smtp_success = False
            
        print("\n" + "=" * 70)
        if smtp_success:
            print("RÉSULTAT DU TEST SMTP : SUCCÈS COMPLET (✅ OPÉRATIONNEL)")
        else:
            print("RÉSULTAT DU TEST SMTP : ÉCHEC OU NON CONFIGURÉ")
        print("=" * 70)

if __name__ == '__main__':
    check_and_test_smtp()
