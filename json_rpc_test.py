import urllib.request
import json

data = json.dumps({
    "jsonrpc": "2.0",
    "method": "call",
    "params": {},
    "id": 1
}).encode('utf-8')

req = urllib.request.Request(
    'http://localhost:8069/web/webclient/version_info',
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode('utf-8'))
except Exception as e:
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
    else:
        print(e)
