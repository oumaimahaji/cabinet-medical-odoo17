# Script pour supprimer le module website
def uninstall_website(env):
    website_module = env['ir.module.module'].search([('name', '=', 'website')])
    if website_module:
        website_module.button_uninstall()
        print("Module website désinstallé")
    else:
        print("Module website non trouvé")
