import sys
import time
import urllib.request

urls = [
    "http://127.0.0.1:8000/health",
    "http://127.0.0.1:8004/health",
    "http://127.0.0.1:8005/health",
]
deadline = time.time() + 60
last = None

while time.time() < deadline:
    ok = True
    for u in urls:
        try:
            r = urllib.request.urlopen(u, timeout=2)
            ok = ok and (r.status == 200)
        except Exception as e:
            ok = False
            last = (u, repr(e))
    if ok:
        print("DOCKER GREEN ✅")
        sys.exit(0)
    time.sleep(2)

print("DOCKER NOT GREEN ❌", last)
sys.exit(1)
