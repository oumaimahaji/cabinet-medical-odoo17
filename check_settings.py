import logging
import sys
import json
import urllib.request
import http.cookiejar

sys.path.append(r'C:\odoo - Copie\odoo')
import odoo

sys.stdout = open('c:/odoo - Copie/inspection_output.txt', 'w', encoding='utf-8')
logging.getLogger('odoo').setLevel(logging.ERROR)

print("--- DEBUT INSPECTION RPC DIRECTE ---")

# Initialiser Odoo et récupérer l'environnement
odoo.tools.config.parse_config(['-c', r'C:\odoo - Copie\odoo\odoo.conf', '-d', 'cabinet_medical'])
registry = odoo.registry('cabinet_medical')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    # 1. Temporairement ré-écrire le mot de passe pour être sûr
    user = env['res.users'].search([('login', '=', 'oumaima.hajji@esprit.tn')], limit=1)
    if user:
        user.password = 'test12345'
        cr.commit()

    view = env.ref('cabinet_medical.res_config_settings_view_form', raise_if_not_found=False)
    view_id = view.id if view else False

# 2. Configurer l'opener avec gestionnaire de cookies
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 3. Authentification
auth_url = "http://localhost:8069/web/session/authenticate"
auth_payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "db": "cabinet_medical",
        "login": "oumaima.hajji@esprit.tn",
        "password": "test12345"
    },
    "id": 1
}

headers = {"Content-Type": "application/json"}

try:
    req = urllib.request.Request(auth_url, data=json.dumps(auth_payload).encode('utf-8'), headers=headers)
    with opener.open(req) as response:
        res_data = json.loads(response.read().decode('utf-8'))
        print("Authentification effectuee.")
        
    # 4. Requete pour recuperer la vue
    rpc_url = "http://localhost:8069/web/dataset/call_kw/res.config.settings/get_views"
    
    # Correction de l'imbrication des arguments: args est une liste d'arguments positionnels
    rpc_payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "res.config.settings",
            "method": "get_views",
            "args": [[[view_id, 'form']]] if view_id else [[['form']]],
            "kwargs": {}
        },
        "id": 2
    }
    
    req_rpc = urllib.request.Request(rpc_url, data=json.dumps(rpc_payload).encode('utf-8'), headers=headers)
    with opener.open(req_rpc) as rpc_response:
        rpc_res = json.loads(rpc_response.read().decode('utf-8'))
        
        if 'error' in rpc_res:
            print("\n/!\\ LE SERVEUR SUR LE PORT 8069 A RETOURNE UNE ERREUR RPC :")
            print(json.dumps(rpc_res['error'], indent=2))
        else:
            result = rpc_res.get('result', {})
            arch = result.get('views', {}).get('form', {}).get('arch', '')
            print("\n--- REPONSE HTTP / RPC DU SERVEUR SUR LE PORT 8069 ---")
            if 'medecin_traitant_setting' in arch:
                print("  -> Le bloc 'medecin_traitant_setting' EXISTE dans la reponse HTTP du port 8069 !")
            else:
                print("  -> Le bloc 'medecin_traitant_setting' est ABSENT de la reponse HTTP du port 8069 !")
                
            print("Detail des champs dans la reponse HTTP :")
            for field in ['cabinet_nom', 'cnam_actif', 'medecin_nom', 'cnam_taux_remboursement']:
                present = field in arch
                print(f"  * {field} : {'PRESENT' if present else 'ABSENT'}")
                
except Exception as e:
    print("Erreur de requete HTTP sur le port 8069 :", e)

print("--- FIN INSPECTION RPC DIRECTE ---")
sys.stdout.close()
