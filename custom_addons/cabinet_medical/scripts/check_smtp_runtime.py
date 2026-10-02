import odoo

odoo.tools.config.parse_config([
    '-c', '/etc/odoo/odoo.conf',
    '-d', 'cabinet_medical_db',
    '--db_host', 'db',
    '--db_user', 'odoo',
    '--db_password', 'odoo_secret_pwd'
])

reg = odoo.registry('cabinet_medical_db')
with reg.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    
    print("=== ODOO.CONF TOOLS.CONFIG ===")
    print("smtp_server:", odoo.tools.config.get('smtp_server'))
    print("smtp_port:", odoo.tools.config.get('smtp_port'))
    print("smtp_ssl:", odoo.tools.config.get('smtp_ssl'))
    print("email_from:", odoo.tools.config.get('email_from'))
    
    print("\n=== IR_MAIL_SERVER RECORDS IN DB ===")
    servers = env['ir.mail_server'].search([])
    print(f"Total servers found: {len(servers)}")
    for s in servers:
        print(f"Server ID: {s.id}, Name: '{s.name}', Host: {s.smtp_host}, Port: {s.smtp_port}, Encryption: {s.smtp_encryption}, User: {s.smtp_user}, Active: {s.active}")
        try:
            res = s.test_smtp_connection()
            print(f"  -> Connection Test Result: {res}")
        except Exception as e:
            print(f"  -> Connection Test FAILED: {e}")
            
    print("\n=== ACTIVE MAIL SERVER USED BY ODOO ===")
    # Check what ir.mail_server.send_email actually picks:
    active_server = env['ir.mail_server'].search([('active', '=', True)], order='sequence', limit=1)
    if active_server:
        print(f"Default Active Server used by send_email(): ID={active_server.id} ({active_server.name}: {active_server.smtp_host}:{active_server.smtp_port})")
    else:
        print("No active ir_mail_server record. Odoo falls back to tools.config (odoo.conf).")
