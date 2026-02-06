"""
Vector search functionality for Firestore RAG
Searches Firestore for semantically similar products
"""

from google.cloud import firestore
from typing import List, Dict

PROJECT_ID = "project-ffed2c3c-0f30-4f6d-820"
FIRESTORE_DB = "product-vectors"

# Initialize
firestore_client = firestore.Client(project=PROJECT_ID, database=FIRESTORE_DB)

def calculate_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    if not vec1 or not vec2:
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a ** 2 for a in vec1) ** 0.5
    magnitude2 = sum(a ** 2 for a in vec2) ** 0.5
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

def search_products_by_vector(query: str, top_k: int = 5) -> List[Dict]:
    """
    Search for products similar to the query using vector similarity
    Returns top_k most relevant products
    """
    
    # For now, create a simple embedding from the query
    import hashlib
    hash_obj = hashlib.sha256(query.encode())
    hash_hex = hash_obj.hexdigest()
    query_embedding = [float(int(hash_hex[i:i+2], 16)) / 255.0 for i in range(0, len(hash_hex)-1, 2)]
    while len(query_embedding) < 1536:
        query_embedding.append(0.0)
    query_embedding = query_embedding[:1536]
    
    # Get all products from Firestore
    products_ref = firestore_client.collection("products")
    docs = products_ref.stream()
    
    # Calculate similarity for each product
    results = []
    for doc in docs:
        product_data = doc.to_dict()
        
        if "embedding" not in product_data:
            continue
        
        product_embedding = product_data["embedding"]
        similarity = calculate_similarity(query_embedding, product_embedding)
        
        # Store with similarity score
        product_with_score = {
            **product_data,
            "similarity_score": similarity,
            "doc_id": doc.id
        }
        results.append(product_with_score)
    
    # Sort by similarity and return top_k
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    return results[:top_k]
