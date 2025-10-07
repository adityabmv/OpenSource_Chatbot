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
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for bot_data in data.get('bots', []):
                        bot = BotConfig(**bot_data)
                        self.bots[bot.id] = bot
            except Exception as e:
                print(f"Error loading bots: {e}")
                self.bots = {}

    def save_bots(self):
        """Save bots to storage file"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            data = {
                'bots': [bot.dict() for bot in self.bots.values()],
                'last_updated': datetime.now().isoformat()
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving bots: {e}")

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
            import shutil
            shutil.rmtree(bot.vectorstore_path)

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
                'vectorstore_size_mb': 0
            }

        # Calculate vectorstore size and count
        total_size = 0
        num_files = 0

        for root, dirs, files in os.walk(vectorstore_path):
            for file in files:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)
                num_files += 1

        # Try to get collection count if possible
        num_chunks = 0
        try:
            from langchain_chroma import Chroma
            from embeddings import get_embeddings_model

            embeddings_model = get_embeddings_model(model_name=bot.embedding_model)
            vectorstore = Chroma(
                collection_name="rag_db",
                embedding_function=embeddings_model,
                persist_directory=vectorstore_path
            )
            num_chunks = len(vectorstore._collection.get()["documents"])
        except Exception:
            # Fallback: estimate based on files
            num_chunks = num_files

        return {
            'num_chunks': num_chunks,
            'vectorstore_exists': True,
            'vectorstore_size_mb': round(total_size / (1024 * 1024), 2),
            'num_files': num_files
        }
