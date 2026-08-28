import requests

try:
    response = requests.get('http://localhost:8069/my/consultations')
    print("Status code:", response.status_code)
    print("Content preview:", response.text[:200])
except Exception as e:
    print(e)
