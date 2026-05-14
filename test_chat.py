import urllib.request
import urllib.error
import json

req = urllib.request.Request(
    'http://localhost:8000/chat/query',
    data=json.dumps({"query": "hello", "scope": "general"}).encode('utf-8'),
    headers={
        "Authorization": "Bearer test-dev-token",
        "Content-Type": "application/json"
    },
    method='POST'
)

try:
    with urllib.request.urlopen(req) as response:
        for line in response:
            print(line.decode('utf-8').strip())
except urllib.error.URLError as e:
    print(f"Failed: {e.reason}")
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
