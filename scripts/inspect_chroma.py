#!/usr/bin/env python3
"""
Script to inspect ChromaDB data structure and metadata
"""
import chromadb
import json
from pprint import pprint

# Connect to ChromaDB server
client = chromadb.HttpClient(host="localhost", port=8001)

# List all collections
print("=" * 60)
print("📚 COLLECTIONS")
print("=" * 60)
collections = client.list_collections()
for col in collections:
    print(f"\n✅ Collection: {col.name}")
    print(f"   ID: {col.id}")
    print(f"   Count: {col.count()}")
    print(f"   Metadata: {col.metadata}")

# Get specific collection
collection = client.get_collection(name="ksa_project")

print("\n" + "=" * 60)
print("🔍 SAMPLE DATA (first 3 documents)")
print("=" * 60)

# Peek at first 3 documents (without embeddings to avoid errors)
results = collection.get(limit=3, include=["documents", "metadatas"])

for i in range(len(results['ids'])):
    print(f"\n--- Document {i+1} ---")
    print(f"ID: {results['ids'][i]}")
    print(f"Document (truncated): {results['documents'][i][:200]}...")
    
    if results.get('metadatas') and len(results['metadatas']) > i and results['metadatas'][i]:
        print(f"Metadata:")
        pprint(results['metadatas'][i], indent=2)

print("\n" + "=" * 60)
print("📊 METADATA STRUCTURE ANALYSIS")
print("=" * 60)

# Analyze metadata fields across all docs
all_results = collection.get(limit=100, include=["metadatas"])
metadata_fields = set()

if all_results.get('metadatas'):
    for metadata in all_results['metadatas']:
        if metadata:
            metadata_fields.update(metadata.keys())

print(f"\n🔑 Metadata fields found:")
for field in sorted(metadata_fields):
    print(f"   - {field}")

print("\n" + "=" * 60)
print("🔎 SEARCH TEST")
print("=" * 60)

# Test search
query = "backend development"
search_results = collection.query(
    query_texts=[query],
    n_results=3,
    include=["documents", "metadatas", "distances"]
)

print(f"\nQuery: '{query}'")
print(f"Results: {len(search_results['ids'][0])}")

for i in range(len(search_results['ids'][0])):
    print(f"\n--- Result {i+1} ---")
    print(f"ID: {search_results['ids'][0][i]}")
    print(f"Distance: {search_results['distances'][0][i]:.4f}")
    print(f"Document (truncated): {search_results['documents'][0][i][:150]}...")
    
    if search_results.get('metadatas') and search_results['metadatas'][0][i]:
        print(f"Metadata:")
        pprint(search_results['metadatas'][0][i], indent=2)

print("\n" + "=" * 60)
print("✅ Inspection complete!")
print("=" * 60)
