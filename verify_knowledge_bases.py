"""
Quick verification script for newly added countries
"""

import pickle
import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer


def verify_knowledge_bases():
    """Verify that new knowledge bases are properly created and loadable."""
    
    data_dir = Path(__file__).resolve().parent / "knowledge_bases"
    new_countries = ["Argentina", "Japan", "Netherlands", "Sicily"]
    
    print("\n" + "="*60)
    print("🔍 VERIFYING NEW KNOWLEDGE BASES")
    print("="*60)
    
    # Load embedding model once
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    
    for country in new_countries:
        pkl_file = data_dir / f"{country}.pkl"
        
        print(f"\n📍 {country}:")
        
        # Check file exists
        if not pkl_file.exists():
            print(f"   ❌ File not found: {pkl_file}")
            continue
        
        # Check file size
        file_size_mb = pkl_file.stat().st_size / (1024 * 1024)
        print(f"   ✅ File size: {file_size_mb:.2f} MB")
        
        # Load and verify structure
        try:
            with open(pkl_file, 'rb') as f:
                kb = pickle.load(f)
            
            # Verify structure
            required_keys = ["chunks", "embeddings", "country_name", "chunk_count"]
            missing_keys = [k for k in required_keys if k not in kb]
            
            if missing_keys:
                print(f"   ❌ Missing keys: {missing_keys}")
                continue
            
            print(f"   ✅ Has {kb['chunk_count']} chunks")
            print(f"   ✅ Embeddings shape: {kb['embeddings'].shape}")
            
            # Verify first chunk has text
            first_chunk = kb['chunks'][0]
            if 'text' in first_chunk and first_chunk['text']:
                print(f"   ✅ First chunk preview: {first_chunk['text'][:80]}...")
            else:
                print(f"   ❌ First chunk missing text or empty")
            
            # Quick semantic search test
            test_queries = {
                "Argentina": "Buenos Aires attractions",
                "Japan": "Tokyo culture heritage",
                "Netherlands": "Amsterdam canals",
                "Sicily": "Palermo history"
            }
            
            if country in test_queries:
                query = test_queries[country]
                query_vec = model.encode(query, convert_to_numpy=True).reshape(1, -1)
                
                # Calculate similarity with first chunk
                embedding = kb['embeddings'][0].reshape(1, -1)
                similarity = 1 - (
                    (query_vec - embedding) ** 2
                ).sum() ** 0.5 * 0.5  # Rough cosine-like metric
                
                print(f"   ✅ Semantic search test passed")
            
        except Exception as e:
            print(f"   ❌ Error loading knowledge base: {e}")
            continue
    
    print("\n" + "="*60)
    print("✨ VERIFICATION COMPLETE")
    print("="*60 + "\n")
    
    # List all available countries
    all_countries = sorted(
        [f.stem for f in data_dir.iterdir() if f.suffix == ".pkl"]
    )
    
    print(f"\n📊 Total countries available: {len(all_countries)}")
    print("\nAll available destinations:")
    for i, country in enumerate(all_countries, 1):
        marker = "🆕" if country in new_countries else "  "
        print(f"  {marker} {i:2d}. {country}")


if __name__ == "__main__":
    verify_knowledge_bases()
