"""
Inspect what metadata fields exist in the current Qdrant vectors
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from src.data_manager.core.config import config

def inspect_metadata():
    """Check what metadata fields exist in vectors"""
    
    # Get Qdrant configuration
    host = config.get_vector_db_config('host', 'localhost')
    port = config.get_vector_db_config('port', 6333)
    api_key = config.get_vector_db_config('api_key', None)
    collection_name = config.get_vector_db_config('index_name', 'test')
    
    # Connect to Qdrant
    if host.startswith('http://') or host.startswith('https://'):
        print(f"Connecting to Qdrant at {host}...")
        client = QdrantClient(url=host, api_key=api_key, port=port)
    else:
        print(f"Connecting to Qdrant at {host}:{port}...")
        client = QdrantClient(host=host, port=port, api_key=api_key)
    
    print(f"Collection: {collection_name}\n")
    
    # Get a few sample vectors
    points, _ = client.scroll(
        collection_name=collection_name,
        limit=5,
        with_payload=True,
        with_vectors=False
    )
    
    if not points:
        print("❌ No vectors found in collection!")
        return
    
    print(f"✓ Found {len(points)} sample vectors\n")
    print("="*80)
    
    # Inspect each vector's metadata
    for i, point in enumerate(points, 1):
        print(f"\n📦 Vector {i} (ID: {point.id})")
        print("-"*80)
        
        if point.payload:
            print(f"Metadata fields ({len(point.payload)} total):")
            for key, value in sorted(point.payload.items()):
                # Truncate long values
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                print(f"  • {key}: {value}")
        else:
            print("  (No metadata)")
    
    print("\n" + "="*80)
    
    # Collect all unique keys
    all_keys = set()
    for point in points:
        if point.payload:
            all_keys.update(point.payload.keys())
    
    print(f"\n📋 All unique metadata fields across samples:")
    for key in sorted(all_keys):
        print(f"  • {key}")
    
    # Check specifically for filename-related fields
    filename_fields = [k for k in all_keys if 'filename' in k.lower() or 'name' in k.lower()]
    print(f"\n🔍 Filename-related fields found: {filename_fields if filename_fields else 'NONE'}")
    
    if 'source_filename' not in all_keys:
        print(f"\n⚠️  WARNING: 'source_filename' field is MISSING from existing vectors!")
        print(f"   This means these vectors were uploaded before the metadata fix.")
        print(f"   You need to re-upload your data for filename search to work.")

if __name__ == "__main__":
    print("="*80)
    print("Qdrant Vector Metadata Inspector")
    print("="*80 + "\n")
    
    inspect_metadata()

