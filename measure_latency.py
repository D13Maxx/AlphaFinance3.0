import requests
import time
import statistics
import sys
import uuid

def measure_latency(iterations=10):
    base_url = "http://127.0.0.1:8000"
    
    # Wait for server
    print("Waiting for server...")
    for i in range(10):
        try:
            requests.get(f"{base_url}/docs")
            break
        except:
            time.sleep(1)
    else:
        print("Server not reachable")
        return

    upload_times = []
    query_times = []

    content_base = "Financial Report\n\n1. Introduction\nThis is a test report about $10M revenue."

    print(f"Running {iterations} iterations...")
    
    for i in range(iterations):
        # Unique content to avoid potential caching (though system shouldn't satisfy cache yet)
        content = f"{content_base} Batch {i}"
        files = {"file": (f"test_{i}.txt", content)}
        
        # Measure Upload
        start = time.perf_counter()
        r = requests.post(f"{base_url}/upload", files=files)
        lat = (time.perf_counter() - start) * 1000 # ms
        upload_times.append(lat)
        
        if r.status_code != 200:
            print(f"Upload failed: {r.status_code}")
            continue
            
        doc_id = r.json()["document_id"]
        
        # Measure Query
        q_payload = {"document_id": doc_id, "query": "What is the revenue?"}
        start = time.perf_counter()
        r_q = requests.post(f"{base_url}/query", json=q_payload)
        lat_q = (time.perf_counter() - start) * 1000 # ms
        query_times.append(lat_q)
        
        if r_q.status_code != 200:
             print(f"Query failed: {r_q.status_code}")

    avg_upload = statistics.mean(upload_times)
    avg_query = statistics.mean(query_times)
    
    print(f"\nResults ({iterations} iterations):")
    print(f"Average Upload Latency: {avg_upload:.2f} ms")
    print(f"Average Query Latency:  {avg_query:.2f} ms")

if __name__ == "__main__":
    measure_latency(20)
