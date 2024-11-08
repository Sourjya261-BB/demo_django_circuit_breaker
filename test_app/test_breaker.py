import requests
import time
import random
from concurrent.futures import ThreadPoolExecutor

def make_request():
    try:
        # Add a random delay between 0.1 and 0.5 seconds before each request
        time.sleep(random.uniform(1, 2))
        
        response = requests.get("http://127.0.0.1:8000/users/")
        print(response.text)
        
        # Add a delay after each request if needed
        time.sleep(random.uniform(1, 2))
        
    except requests.RequestException as e:
        print(f"Request failed: {e}")

# Number of requests to simulate
num_requests = 200

with ThreadPoolExecutor(max_workers=1) as executor:
    futures = [executor.submit(make_request) for _ in range(num_requests)]
