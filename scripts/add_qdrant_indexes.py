"""
Add missing payload indexes to existing Qdrant collection
Run this script to enable filename and category search functionality
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType
from src.data_manager.core.config import config

def add_indexes():
    """Add missing payload indexes to Qdrant collection"""
    
    # Get Qdrant configuration
    host = config.get_vector_db_config('host', 'localhost')
    port = config.get_vector_db_config('port', 6333)
    api_key = config.get_vector_db_config('api_key', None)
    collection_name = config.get_vector_db_config('index_name', 'test')
    
    # Check if host is a full URL (contains protocol)
    if host.startswith('http://') or host.startswith('https://'):
        print(f"Connecting to Qdrant at {host}...")
        client = QdrantClient(url=host, api_key=api_key, port=port)
    else:
        print(f"Connecting to Qdrant at {host}:{port}...")
        client = QdrantClient(host=host, port=port, api_key=api_key)
    
    # Check if collection exists
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    collection_exists = collection_name in collection_names
    
    if not collection_exists:
        print(f"❌ Collection '{collection_name}' does not exist!")
        print(f"Available collections: {', '.join(collection_names) if collection_names else '(none)'}")
        return False
    
    print(f"✓ Collection '{collection_name}' found")
    
    # Add indexes
    indexes_to_add = [
        ('source_filename', 'Used for filename search'),
        ('category', 'Used for category search'),
    ]
    
    success_count = 0
    for field_name, description in indexes_to_add:
        try:
            print(f"\nAdding index for '{field_name}' ({description})...")
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=PayloadSchemaType.KEYWORD
            )
            print(f"  ✓ Index for '{field_name}' created successfully")
            success_count += 1
        except Exception as e:
            error_str = str(e).lower()
            if 'already exists' in error_str or 'exist' in error_str:
                print(f"  ℹ️  Index for '{field_name}' already exists")
                success_count += 1
            else:
                print(f"  ❌ Failed to create index for '{field_name}': {str(e)}")
    
    print(f"\n{'='*60}")
    print(f"✓ Successfully added/verified {success_count}/{len(indexes_to_add)} indexes")
    print(f"{'='*60}")
    
    return success_count == len(indexes_to_add)

if __name__ == "__main__":
    print("="*60)
    print("Qdrant Payload Index Creator")
    print("="*60)
    
    success = add_indexes()
    
    if success:
        print("\n✅ All indexes are ready!")
        print("You can now use filename and category search in the admin panel.")
    else:
        print("\n⚠️  Some indexes could not be created.")
        print("Check the error messages above.")
        sys.exit(1)

