import requests
import time
import sys

def test_api():
    base_url = "http://127.0.0.1:8000"
    
    # Wait for server
    for i in range(10):
        try:
            r = requests.get(f"{base_url}/docs")
            if r.status_code == 200:
                print("Server is up!")
                break
        except:
            time.sleep(1)
            print(f"Waiting for server... {i+1}")
    else:
        print("Server failed to start.")
        sys.exit(1)

    # Test Upload
    content = "Financial Report\n\n1. Introduction\nThis is a test report about $10M revenue."
    files = {"file": ("test.txt", content)}
    
    try:
        r = requests.post(f"{base_url}/upload", files=files)
        print("Upload Status:", r.status_code)
        print("Upload Response:", r.json())
        
        if r.status_code == 200:
            doc_id = r.json()["document_id"]
            
            # Test Query
            q_payload = {"document_id": doc_id, "query": "What is the revenue?"}
            r_q = requests.post(f"{base_url}/query", json=q_payload)
            print("Query Status:", r_q.status_code)
            print("Query Response:", r_q.json())
            
    except Exception as e:
        print("Test failed:", str(e))

if __name__ == "__main__":
    test_api()
