import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from datetime import datetime

# Config
API_KEY = "45095f01-0f86-44fe-8c8b-5ad1f75360bc"
APP_ID = "67eeb376-e35b-42b8-9403-bcfcad30399c"
URL = f"http://127.0.0.1:8000/api/auth/credentials/signup/{APP_ID}"

HEADERS = {
    "Authorization": f"ApiKey {API_KEY}",
    "Content-Type": "application/json"
}
PASSWORD = "user_password"
BASE_EMAIL = "user+{}@example.com"
TOTAL_REQUESTS = 10
CONCURRENCY = 30# Number of threads

success_count = 0
fail_count = 0

# Thread-safe counters
from threading import Lock
success_lock = Lock()
fail_lock = Lock()

def send_request(i):
    global success_count, fail_count
    email = BASE_EMAIL.format(i)
    data = {
        "email": email,
        "password": PASSWORD
    }

    try:
        response = requests.post(URL, headers=HEADERS, data=json.dumps(data), timeout=5)
        if response.status_code == 201:
            with success_lock:
                success_count += 1
        else:
            with fail_lock:
                fail_count += 1
            return f"[{i}] ❌ Status {response.status_code}: {response.text.strip()}"
    except Exception as e:
        with fail_lock:
            fail_count += 1
        return f"[{i}] ❌ Exception: {str(e)}"
    return None  # No error

def main():
    start = datetime.now()
    errors = []

    print(f"📤 Sending {TOTAL_REQUESTS} concurrent requests to {URL} with {CONCURRENCY} workers\n")

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(send_request, i) for i in range(TOTAL_REQUESTS)]
        for f in tqdm(as_completed(futures), total=TOTAL_REQUESTS, desc="Stress Test Progress", unit="req"):
            result = f.result()
            if result:
                tqdm.write(result)

    end = datetime.now()
    duration = (end - start).total_seconds()
    print(f"\n🏁 Done in {duration:.2f}s → ✅ {success_count} succeeded | ❌ {fail_count} failed")

if __name__ == "__main__":
    main()

