# chat_history.py
import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional

class ChatHistoryManager:
    def __init__(self, history_dir="chat_history"):
        self.history_dir = history_dir
        os.makedirs(history_dir, exist_ok=True)

    def _get_history_file(self, bot_id: str) -> str:
        """Get the history file path for a bot"""
        return os.path.join(self.history_dir, f"chat_history_{bot_id}.json")

    def _generate_conversation_id(self) -> str:
        """Generate a unique conversation ID"""
        return f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

    def _generate_title(self, first_message: str) -> str:
        """Generate a title from the first message"""
        # Take first 50 characters and clean them up
        title = first_message.strip()[:50]
        if len(first_message) > 50:
            title += "..."
        return title

    def create_conversation(self, bot_id: str, uid: str = "") -> str:
        """Create a new conversation and return its ID"""
        conversation_id = self._generate_conversation_id()
        history_file = self._get_history_file(bot_id)

        conversation = {
            "id": conversation_id,
            "title": "New Conversation",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": [],
            "uid": uid
        }

        # Load existing data or create new
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                data = json.load(f)
        else:
            data = {"conversations": []}

        data["conversations"].append(conversation)

        # Save
        with open(history_file, 'w') as f:
            json.dump(data, f, indent=2)

        return conversation_id

    def save_message(self, bot_id: str, conversation_id: str, role: str, content: str):
        """Save a message to a conversation"""
        history_file = self._get_history_file(bot_id)

        if not os.path.exists(history_file):
            # Create conversation if it doesn't exist
            conversation_id = self.create_conversation(bot_id)

        with open(history_file, 'r') as f:
            data = json.load(f)

        # Find conversation
        conversation = None
        for conv in data["conversations"]:
            if conv["id"] == conversation_id:
                conversation = conv
                break

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Add message
        message = {
            "id": f"msg_{len(conversation['messages']) + 1}",
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }

        conversation["messages"].append(message)
        conversation["updated_at"] = datetime.now().isoformat()

        # Update title if this is the first message
        if len(conversation["messages"]) == 1:
            conversation["title"] = self._generate_title(content)

        # Save
        with open(history_file, 'w') as f:
            json.dump(data, f, indent=2)

    def get_conversations(self, bot_id: str, uid: str = None) -> List[Dict]:
        """Get all conversations for a bot, optionally filtered by UID"""
        history_file = self._get_history_file(bot_id)

        if not os.path.exists(history_file):
            return []

        with open(history_file, 'r') as f:
            data = json.load(f)

        conversations = data.get("conversations", [])
        # Add message count to each conversation
        for conv in conversations:
            conv["message_count"] = len(conv.get("messages", []))

        if uid:
            conversations = [conv for conv in conversations if conv.get("uid", "") == uid]

        return conversations

    def get_conversation(self, bot_id: str, conversation_id: str, uid: str = None) -> Optional[Dict]:
        """Get a specific conversation with messages, optionally filtered by UID"""
        conversations = self.get_conversations(bot_id, uid=uid)
        for conv in conversations:
            if conv["id"] == conversation_id:
                return conv
        return None

    def delete_conversation(self, bot_id: str, conversation_id: str, uid: str = None) -> bool:
        """Delete a conversation, optionally filtered by UID"""
        history_file = self._get_history_file(bot_id)

        if not os.path.exists(history_file):
            return False

        with open(history_file, 'r') as f:
            data = json.load(f)

        # Remove conversation, only if UID matches (if provided)
        if uid:
            data["conversations"] = [conv for conv in data["conversations"] if not (conv["id"] == conversation_id and conv.get("uid", "") == uid)]
        else:
            data["conversations"] = [conv for conv in data["conversations"] if conv["id"] != conversation_id]

        with open(history_file, 'w') as f:
            json.dump(data, f, indent=2)

        return True

    def update_conversation_title(self, bot_id: str, conversation_id: str, new_title: str):
        """Update a conversation's title"""
        history_file = self._get_history_file(bot_id)

        if not os.path.exists(history_file):
            return False

        with open(history_file, 'r') as f:
            data = json.load(f)

        # Find and update conversation
        for conv in data["conversations"]:
            if conv["id"] == conversation_id:
                conv["title"] = new_title
                conv["updated_at"] = datetime.now().isoformat()
                break

        with open(history_file, 'w') as f:
            json.dump(data, f, indent=2)
