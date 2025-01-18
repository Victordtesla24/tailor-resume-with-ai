import json
import logging
from typing import Dict, Optional, Any, Callable, Awaitable, cast
from datetime import datetime
from dataclasses import dataclass
from openai import OpenAI
from websockets.client import connect as ws_connect
from websockets.client import WebSocketClientProtocol


logger = logging.getLogger("resume_tailor")


@dataclass
class RealtimeConfig:
    """Configuration for realtime processing."""
    model: str = "gpt-4o-realtime-preview"
    max_tokens: int = 1000
    temperature: float = 0.7
    stream: bool = True


@dataclass
class RealtimeMetrics:
    """Metrics for realtime processing."""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tokens: int = 0
    total_cost: float = 0.0
    latency_ms: float = 0.0


class RealtimeProcessor:
    """Handles realtime processing using OpenAI's Realtime API."""

    def __init__(
        self,
        client: Optional[OpenAI] = None,
        config: Optional[RealtimeConfig] = None
    ) -> None:
        self.client = client or OpenAI()
        self.config = config or RealtimeConfig()
        self.metrics: Dict[str, RealtimeMetrics] = {}
        self.ws: Optional[WebSocketClientProtocol] = None
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[None]]] = {}

    async def connect(self) -> None:
        """Establish WebSocket connection to Realtime API."""
        try:
            auth_token = await self._get_auth_token()
            self.ws = await ws_connect(
                "wss://api.openai.com/v1/realtime",
                extra_headers={"Authorization": f"Bearer {auth_token}"}
            )
            logger.info("Connected to Realtime API")
        except Exception as e:
            logger.error(f"Failed to connect to Realtime API: {e}")
            raise

    async def _get_auth_token(self) -> str:
        """Get authentication token for WebSocket connection."""
        try:
            # Note: This is a placeholder until OpenAI adds proper type hints
            response = await cast(Any, self.client).realtime.auth.create()
            return cast(str, response.token)
        except Exception as e:
            logger.error(f"Failed to get auth token: {e}")
            raise

    def register_handler(
        self,
        event_type: str,
        handler: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """Register handler for specific event types."""
        self._handlers[event_type] = handler

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle incoming WebSocket messages."""
        event_type = message.get("type")
        if event_type and event_type in self._handlers:
            await self._handlers[event_type](message)
        else:
            logger.warning(f"No handler for event type: {event_type}")

    async def process_resume_realtime(
        self,
        content: str,
        job_description: str,
        on_update: Callable[[str], Awaitable[None]]
    ) -> None:
        """
        Process resume content in realtime with streaming updates.

        Args:
            content: Resume content to process
            job_description: Job description for tailoring
            on_update: Callback for receiving realtime updates
        """
        if not self.ws:
            await self.connect()

        session_id = f"session_{datetime.now().timestamp()}"
        self.metrics[session_id] = RealtimeMetrics(start_time=datetime.now())

        try:
            request = {
                "type": "resume_tailor",
                "model": self.config.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert resume tailoring assistant providing "
                            "realtime feedback and improvements."
                        )
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Resume Content:\n{content}\n\n"
                            f"Job Description:\n{job_description}"
                        )
                    }
                ],
                "stream": True,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature
            }

            if not self.ws:
                raise RuntimeError("WebSocket connection not established")

            await self.ws.send(json.dumps(request))

            async for message in cast(Any, self.ws):
                data = json.loads(message)
                if data.get("type") == "content":
                    await on_update(data.get("text", ""))
                elif data.get("type") == "error":
                    raise Exception(data.get("message", "Unknown error"))
                elif data.get("type") == "done":
                    end_time = datetime.now()
                    self.metrics[session_id].end_time = end_time
                    self.metrics[session_id].latency_ms = (
                        end_time - self.metrics[session_id].start_time
                    ).total_seconds() * 1000
                    break

        except Exception as e:
            logger.error(f"Error during realtime processing: {e}")
            raise
        finally:
            self._update_metrics(session_id)

    def _update_metrics(self, session_id: str) -> None:
        """Update cost and token metrics for the session."""
        metrics = self.metrics[session_id]
        if metrics.end_time:
            # Calculate costs based on user.log pricing
            input_cost = 0.0050  # $0.0050 per 1K tokens
            output_cost = 0.0200  # $0.0200 per 1K tokens

            # Estimate token counts (can be refined based on actual usage)
            input_tokens = metrics.total_tokens // 3  # Rough estimate
            output_tokens = metrics.total_tokens - input_tokens

            total_cost = (
                (input_tokens / 1000) * input_cost +
                (output_tokens / 1000) * output_cost
            )

            metrics.total_cost = total_cost

    async def close(self) -> None:
        """Close WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.ws = None

    def get_session_metrics(self, session_id: str) -> Optional[RealtimeMetrics]:
        """Get metrics for a specific session."""
        return self.metrics.get(session_id)

    def get_all_metrics(self) -> Dict[str, RealtimeMetrics]:
        """Get metrics for all sessions."""
        return self.metrics.copy()
