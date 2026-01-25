import requests
import os

# API Endpoint
UPLOAD_URL = "http://localhost:8000/api/upload"

def test_upload():
    print(f">> Testing Upload to {UPLOAD_URL}...")
    
    # Create a dummy file to upload (text file)
    filename = "test_upload_doc.txt"
    content = "This is a test document for Gemini upload."
    
    with open(filename, "w") as f:
        f.write(content)
        
    try:
        # Open the file and send POST request
        with open(filename, "rb") as f:
            files = {"file": (filename, f, "text/plain")}
            response = requests.post(UPLOAD_URL, files=files)
            
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("[OK] Upload Successful!")
            print("Response:", response.json())
        else:
            print("[FAIL] Upload Failed:")
            print(response.text)
            
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        
    finally:
        # Clean up
        if os.path.exists(filename):
            os.remove(filename)

if __name__ == "__main__":
    test_upload()
