import urllib.request
from urllib.error import HTTPError

try:
    urllib.request.urlopen('http://localhost:8069/web?debug=1')
except HTTPError as e:
    print(e.read().decode('utf-8'))
