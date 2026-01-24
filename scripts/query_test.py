import chromadb
from pprint import pprint

# ChromaDB Config
CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
COLLECTION_NAME = "ksa_project"

def query_backend_learning():
    print(f"🚀 Connecting to ChromaDB ({CHROMA_HOST}:{CHROMA_PORT})...")
    try:
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception as e:
        print(f"❌ Failed to connect to ChromaDB: {e}")
        return

    query_text = "Tôi muốn học backend"
    print(f"\n🔍 Querying: '{query_text}'")
    
    # Query ChromaDB
    results = collection.query(
        query_texts=[query_text],
        n_results=5,  # Fetch top 5 to see good matches
        include=["metadatas", "documents", "distances"]
    )
    
    num_results = len(results['ids'][0])
    print(f"   Found {num_results} results:\n")
    
    if num_results == 0:
        print("   No results found.")
        return

    # Print results
    for i in range(num_results):
        doc_id = results['ids'][0][i]
        document = results['documents'][0][i]
        metadata = results['metadatas'][0][i]
        distance = results['distances'][0][i]
        
        # Calculate similarity percentage
        # Assuming cosine distance where 0 is identical and 1 is orthogonal (or up to 2 for opposite)
        # For display purposes, (1 - distance) is a common proxy for similarity score if distance < 1
        # If using L2 (Euclidean), this conversion might not be strictly "percentage" but relative score.
        # We'll display both distance and an estimated similarity.
        similarity_score = (1 - distance) * 100
        
        print(f"--- Result {i+1} ---")
        print(f"ID: {doc_id}")
        print(f"Distance: {distance:.4f}")
        print(f"Similarity: {similarity_score:.2f}%")
        print(f"Content: {document}")
        print("Metadata:")
        pprint(metadata, indent=2, width=80)
        print("-" * 40)

if __name__ == "__main__":
    query_backend_learning()
