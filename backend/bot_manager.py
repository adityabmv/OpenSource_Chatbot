# bot_manager.py
import json
import os
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime

class BotConfig(BaseModel):
    id: str
    name: str
    description: str = ""
    chunk_size: int = 500
    chunk_overlap: int = 50
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ocr_lang: str = "eng"
    created_at: datetime
    updated_at: datetime
    vectorstore_path: str
    is_active: bool = True

class BotManager:
    def __init__(self, storage_path: str = "bots_config.json"):
        self.storage_path = storage_path
        self.bots: Dict[str, BotConfig] = {}
        self.load_bots()

    def load_bots(self):
        """Load bots from storage file"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for bot_data in data.get('bots', []):
                        bot = BotConfig(**bot_data)
                        self.bots[bot.id] = bot
            except Exception as e:
                print(f"Error loading bots: {e}")
                self.bots = {}
        else:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            # Initialize with empty data
            self.save_bots()

    def save_bots(self):
        """Save bots to storage file"""
        try:
            # Ensure directory exists
            dir_path = os.path.dirname(self.storage_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
                
            # Prepare data
            data = {
                'bots': [bot.dict() for bot in self.bots.values()],
                'last_updated': datetime.now().isoformat()
            }
            
            # Write to temporary file first
            temp_path = f"{self.storage_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Atomic rename to final location
            if os.path.exists(self.storage_path):
                os.replace(temp_path, self.storage_path)
            else:
                os.rename(temp_path, self.storage_path)
                
        except Exception as e:
            print(f"Error saving bots: {e}")
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            raise

    def create_bot(self, name: str, description: str = "", **kwargs) -> BotConfig:
        """Create a new bot"""
        bot_id = str(uuid.uuid4())
        now = datetime.now()

        # Create bot-specific vectorstore directory
        vectorstore_path = f"vector_db_{bot_id}"

        bot = BotConfig(
            id=bot_id,
            name=name,
            description=description,
            vectorstore_path=vectorstore_path,
            created_at=now,
            updated_at=now,
            **kwargs
        )

        self.bots[bot_id] = bot
        self.save_bots()
        return bot

    def get_bot(self, bot_id: str) -> Optional[BotConfig]:
        """Get a bot by ID"""
        return self.bots.get(bot_id)

    def get_all_bots(self) -> List[BotConfig]:
        """Get all bots"""
        return list(self.bots.values())

    def get_active_bots(self) -> List[BotConfig]:
        """Get all active bots"""
        return [bot for bot in self.bots.values() if bot.is_active]

    def update_bot(self, bot_id: str, **updates) -> Optional[BotConfig]:
        """Update a bot"""
        if bot_id not in self.bots:
            return None

        bot = self.bots[bot_id]
        updates['updated_at'] = datetime.now()

        # Handle special updates
        for key, value in updates.items():
            if hasattr(bot, key):
                setattr(bot, key, value)

        self.save_bots()
        return bot

    def delete_bot(self, bot_id: str) -> bool:
        """Delete a bot and its vectorstore"""
        if bot_id not in self.bots:
            return False

        bot = self.bots[bot_id]

        # Remove vectorstore directory if it exists
        if os.path.exists(bot.vectorstore_path):
            try:
                # First try to close any open Chroma connections
                import chromadb
                try:
                    client = chromadb.PersistentClient(path=bot.vectorstore_path)
                    client.reset()  # This closes connections
                except Exception as e:
                    print(f"Warning: Could not reset Chroma client: {e}")
                
                # Force Python garbage collection
                import gc
                gc.collect()
                
                # Wait a moment for resources to be freed
                import time
                time.sleep(1)
                
                # Now try to remove the directory
                import shutil
                shutil.rmtree(bot.vectorstore_path, ignore_errors=True)
            except Exception as e:
                print(f"Warning: Could not fully remove vectorstore: {e}")
                # Continue with bot deletion even if vectorstore deletion fails
                pass

        del self.bots[bot_id]
        self.save_bots()
        return True

    def get_bot_stats(self, bot_id: str) -> Optional[Dict]:
        """Get statistics for a bot"""
        bot = self.get_bot(bot_id)
        if not bot:
            return None

        vectorstore_path = bot.vectorstore_path
        if not os.path.exists(vectorstore_path):
            return {
                'num_chunks': 0,
                'vectorstore_exists': False,
                'vectorstore_size_mb': 0,
                'num_files': 0
            }

        # Calculate total size
        total_size = 0
        for root, dirs, files in os.walk(vectorstore_path):
            for file in files:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)

        # Initialize stats with defaults in case we can't get detailed stats
        stats = {
            'num_chunks': 0,
            'vectorstore_exists': True,
            'vectorstore_size_mb': round(total_size / (1024 * 1024), 2),
            'num_files': 0
        }

        # Try to get collection stats
        try:
            import chromadb
            client = chromadb.PersistentClient(path=vectorstore_path)
            collection = client.get_collection("rag_db")
            collection_data = collection.get()
            
            # Get number of chunks
            if collection_data.get('ids'):
                stats['num_chunks'] = len(collection_data['ids'])
            
            # Get source files from metadata
            source_files = set()
            if collection_data.get('metadatas'):
                for meta in collection_data['metadatas']:
                    if meta and 'file_name' in meta:
                        source_files.add(meta['file_name'])
                stats['num_files'] = len(source_files)

        except Exception as e:
            print(f"Error getting detailed stats: {e}")
            # Already have basic stats set above, just return those
            pass

        return stats
