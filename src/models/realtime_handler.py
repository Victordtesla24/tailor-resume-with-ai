import asyncio
import logging
from typing import Dict, Optional, Any, AsyncIterator
from uuid import uuid4

from .api_client import APIClient
from .types import ResponseQueue

logger = logging.getLogger("resume_tailor")


class RealtimeHandler:
    """Handles realtime API interactions and streaming responses."""
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
        self.active_sessions: Dict[str, ResponseQueue] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}

    async def start_session(
        self,
        model: str,
        initial_prompt: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start a new realtime session."""
        session_id = str(uuid4())
        response_queue: ResponseQueue = asyncio.Queue()
        self.active_sessions[session_id] = response_queue
        self.session_metadata[session_id] = {
            "model": model,
            "metadata": metadata or {},
            "status": "active"
        }

        # Start processing in background
        asyncio.create_task(
            self.api_client.handle_realtime_request(
                session_id,
                model,
                initial_prompt,
                self.active_sessions
            )
        )

        return session_id

    async def send_message(self, session_id: str, message: str) -> None:
        """Send a message to an active session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        if self.session_metadata[session_id]["status"] != "active":
            raise ValueError(f"Session {session_id} is not active")

        model = self.session_metadata[session_id]["model"]
        await self.api_client.handle_realtime_request(
            session_id,
            model,
            message,
            self.active_sessions
        )

    async def get_response(self, session_id: str) -> AsyncIterator[Dict[str, Any]]:
        """Get streaming responses from a session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")

        queue = self.active_sessions[session_id]
        try:
            while True:
                response = await queue.get()
                yield response
                if response["type"] == "done":
                    break
                queue.task_done()
        except asyncio.CancelledError:
            logger.warning(f"Response stream cancelled for session {session_id}")
            raise

    def end_session(self, session_id: str) -> None:
        """End a realtime session."""
        if session_id in self.active_sessions:
            self.session_metadata[session_id]["status"] = "completed"
            del self.active_sessions[session_id]
            logger.info(f"Session {session_id} ended")

    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active sessions."""
        return {
            session_id: metadata
            for session_id, metadata in self.session_metadata.items()
            if metadata["status"] == "active"
        }

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a specific session."""
        if session_id not in self.session_metadata:
            raise ValueError(f"Session {session_id} not found")
        return self.session_metadata[session_id]
