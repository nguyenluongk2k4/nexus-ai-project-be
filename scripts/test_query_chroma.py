import chromadb
from pprint import pprint

# ChromaDB Config
CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
COLLECTION_NAME = "ksa_project"

def test_query():
    print(f"🚀 Connecting to ChromaDB ({CHROMA_HOST}:{CHROMA_PORT})...")
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    collection = client.get_collection(name=COLLECTION_NAME)
    
    query_text = "lập trình hướng đối tượng"
    print(f"\n🔍 Querying: '{query_text}'")
    
    results = collection.query(
        query_texts=[query_text],
        n_results=3,
        include=["metadatas", "documents", "distances"]
    )
    
    print(f"   Found {len(results['ids'][0])} results:\n")
    
    for i in range(len(results['ids'][0])):
        print(f"--- Result {i+1} ---")
        print(f"ID: {results['ids'][0][i]}")
        
        # Pretty print metadata
        meta = results['metadatas'][0][i]
        print("Metadata:")
        pprint(meta, indent=2, width=80)
        print("-" * 40)

if __name__ == "__main__":
    test_query()
