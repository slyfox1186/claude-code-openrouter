#!/usr/bin/env python3
"""
Conversation History Manager for OpenRouter MCP Server

Handles conversation continuation with UUID tags to maintain chat history
across multiple tool calls.
"""
import json
import os
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger("conversation-manager")


class ConversationManager:
    """Manages conversation history with UUID-based continuation"""

    def __init__(self, storage_dir: str = "/tmp/openrouter_conversations"):
        """Initialize conversation manager

        Args:
            storage_dir: Directory to store conversation files
        """
        self.storage_dir = storage_dir
        self.ensure_storage_dir()
        # In-memory cache for active conversations (following best practices)
        self._conversation_cache = {}

    def ensure_storage_dir(self):
        """Ensure storage directory exists"""
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
            logger.info(f"STORAGE: Conversation storage directory: {self.storage_dir}")

            # Test write access
            test_file = os.path.join(self.storage_dir, "test_write.tmp")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            logger.info(f"STORAGE: Directory is writable: {self.storage_dir}")
        except Exception as e:
            logger.error(
                f"STORAGE: Failed to create or write to storage directory {self.storage_dir}: {e}"
            )
            raise

    def get_conversation_file(self, continuation_id: str) -> str:
        """Get file path for conversation

        Args:
            continuation_id: UUID of the conversation

        Returns:
            File path for the conversation
        """
        return os.path.join(self.storage_dir, f"conversation_{continuation_id}.json")

    def create_conversation(self) -> str:
        """Create a new conversation

        Returns:
            New conversation UUID
        """
        continuation_id = str(uuid.uuid4())
        conversation_data = {
            "id": continuation_id,
            "created_at": datetime.utcnow().isoformat(),
            "messages": [],
        }

        file_path = self.get_conversation_file(continuation_id)
        logger.debug(f"STORAGE: Creating conversation file: {file_path}")

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(conversation_data, f, indent=2)

            # Add to cache
            self._conversation_cache[continuation_id] = conversation_data

            logger.info(f"STORAGE: Created new conversation: {continuation_id}")
            logger.debug(
                f"STORAGE: Conversation file created successfully at: {file_path}"
            )
            return continuation_id
        except Exception as e:
            logger.error(f"STORAGE: Error creating conversation {continuation_id}: {e}")
            raise

    def load_conversation(self, continuation_id: str) -> Optional[Dict[str, Any]]:
        """Load conversation by ID with in-memory caching

        Args:
            continuation_id: UUID of the conversation

        Returns:
            Conversation data or None if not found
        """
        # Check in-memory cache first (best practice)
        if continuation_id in self._conversation_cache:
            logger.debug(f"STORAGE: Loading conversation {continuation_id} from cache")
            cached_data = self._conversation_cache[continuation_id]
            logger.debug(
                f"STORAGE: Cached conversation has {len(cached_data.get('messages', []))} messages"
            )
            return cached_data

        file_path = self.get_conversation_file(continuation_id)
        logger.debug(f"STORAGE: Attempting to load conversation from file: {file_path}")

        if not os.path.exists(file_path):
            logger.warning(f"STORAGE: Conversation file not found: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                conversation_data = json.load(f)

            # Cache the loaded conversation
            self._conversation_cache[continuation_id] = conversation_data
            logger.debug(
                f"STORAGE: Loaded conversation {continuation_id} with {len(conversation_data.get('messages', []))} messages from file"
            )
            return conversation_data
        except Exception as e:
            logger.error(f"STORAGE: Error loading conversation {continuation_id}: {e}")
            return None

    def save_conversation(self, conversation_data: Dict[str, Any]):
        """Save conversation data with cache update

        Args:
            conversation_data: Conversation data to save
        """
        continuation_id = conversation_data.get("id")
        if not continuation_id:
            logger.error("Cannot save conversation without ID")
            return

        file_path = self.get_conversation_file(continuation_id)
        conversation_data["updated_at"] = datetime.utcnow().isoformat()

        try:
            # Update cache first (best practice for performance)
            self._conversation_cache[continuation_id] = conversation_data

            # Then persist to disk
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(conversation_data, f, indent=2)
            logger.debug(f"Saved conversation {continuation_id}")
        except Exception as e:
            logger.error(f"Error saving conversation {continuation_id}: {e}")
            # Remove from cache if save failed
            if continuation_id in self._conversation_cache:
                del self._conversation_cache[continuation_id]

    def add_message(
        self,
        continuation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a message to the conversation

        Args:
            continuation_id: UUID of the conversation
            role: Message role (user, assistant)
            content: Message content
            metadata: Optional metadata (model, files, etc.)

        Returns:
            True if successful, False otherwise
        """
        logger.debug(
            f"STORAGE: Adding {role} message to conversation {continuation_id}"
        )

        conversation_data = self.load_conversation(continuation_id)
        if not conversation_data:
            logger.error(
                f"STORAGE: Cannot add message to non-existent conversation: {continuation_id}"
            )
            return False

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if metadata:
            message["metadata"] = metadata

        conversation_data["messages"].append(message)
        logger.debug(
            f"STORAGE: Message added to conversation data. Total messages: {len(conversation_data['messages'])}"
        )

        # Save conversation
        self.save_conversation(conversation_data)

        # Verify the message was actually saved
        verification_data = self.load_conversation(continuation_id)
        if verification_data and len(verification_data["messages"]) == len(
            conversation_data["messages"]
        ):
            logger.info(
                f"STORAGE: Successfully added {role} message to conversation {continuation_id}. Total messages: {len(verification_data['messages'])}"
            )
            return True
        else:
            logger.error(
                f"STORAGE: Failed to verify message save for conversation {continuation_id}"
            )
            return False

    def get_conversation_history(
        self, continuation_id: str, max_tokens: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """Get conversation history in OpenAI format with optional token optimization

        Args:
            continuation_id: UUID of the conversation
            max_tokens: Maximum tokens to include (follows Zen MCP pattern)

        Returns:
            List of messages in OpenAI format
        """
        conversation_data = self.load_conversation(continuation_id)
        if not conversation_data:
            return []

        messages = conversation_data.get("messages", [])

        # Convert to OpenAI format
        openai_messages = []
        for msg in messages:
            openai_messages.append({"role": msg["role"], "content": msg["content"]})

        # Token optimization (following Zen MCP pattern)
        if max_tokens and len(openai_messages) > 0:
            # Rough token estimation (4 chars = 1 token)
            total_chars = sum(len(msg["content"]) for msg in openai_messages)
            estimated_tokens = total_chars // 4

            if estimated_tokens > max_tokens:
                # Keep most recent messages within token limit
                target_chars = max_tokens * 4
                optimized_messages = []
                current_chars = 0

                # Start from most recent and work backwards
                for msg in reversed(openai_messages):
                    msg_chars = len(msg["content"])
                    if current_chars + msg_chars <= target_chars:
                        optimized_messages.insert(0, msg)
                        current_chars += msg_chars
                    else:
                        break

                logger.debug(
                    f"Optimized conversation {continuation_id}: {len(openai_messages)} -> {len(optimized_messages)} messages"
                )
                openai_messages = optimized_messages

        logger.debug(
            f"Retrieved {len(openai_messages)} messages for conversation {continuation_id}"
        )
        return openai_messages

    def get_conversation_summary(self, continuation_id: str) -> Dict[str, Any]:
        """Get conversation summary

        Args:
            continuation_id: UUID of the conversation

        Returns:
            Conversation summary
        """
        conversation_data = self.load_conversation(continuation_id)
        if not conversation_data:
            return {}

        messages = conversation_data.get("messages", [])
        return {
            "id": continuation_id,
            "created_at": conversation_data.get("created_at"),
            "updated_at": conversation_data.get("updated_at"),
            "message_count": len(messages),
            "last_message": messages[-1] if messages else None,
        }

    def list_conversations(self) -> List[Dict[str, Any]]:
        """List all conversations

        Returns:
            List of conversation summaries
        """
        conversations = []

        try:
            for filename in os.listdir(self.storage_dir):
                if filename.startswith("conversation_") and filename.endswith(".json"):
                    continuation_id = filename[
                        13:-5
                    ]  # Remove "conversation_" and ".json"
                    summary = self.get_conversation_summary(continuation_id)
                    if summary:
                        conversations.append(summary)
        except Exception as e:
            logger.error(f"Error listing conversations: {e}")

        # Sort by updated_at (most recent first)
        conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return conversations

    def delete_conversation(self, continuation_id: str) -> bool:
        """Delete a conversation

        Args:
            continuation_id: UUID of the conversation to delete

        Returns:
            True if successful, False otherwise
        """
        file_path = self.get_conversation_file(continuation_id)

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted conversation: {continuation_id}")
                return True
            else:
                logger.warning(
                    f"Conversation not found for deletion: {continuation_id}"
                )
                return False
        except Exception as e:
            logger.error(f"Error deleting conversation {continuation_id}: {e}")
            return False

    def cleanup_old_conversations(self, max_age_days: int = 30):
        """Clean up old conversations

        Args:
            max_age_days: Maximum age in days to keep conversations
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        cutoff_iso = cutoff_date.isoformat()

        deleted_count = 0
        conversations = self.list_conversations()

        for conv in conversations:
            updated_at = conv.get("updated_at", "")
            if updated_at < cutoff_iso:
                if self.delete_conversation(conv["id"]):
                    deleted_count += 1

        logger.info(
            f"Cleaned up {deleted_count} old conversations (older than {max_age_days} days)"
        )
        return deleted_count
