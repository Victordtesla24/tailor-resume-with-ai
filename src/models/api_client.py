import logging
import asyncio
from time import time
from typing import Dict, Optional, Any, cast, AsyncIterator, Awaitable, List
from datetime import datetime

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionMessageParam

from .config import AVAILABLE_MODELS
from .token_bucket import TokenBucket
from .types import ResponseQueue

logger = logging.getLogger("resume_tailor")


class APIClient:
    """Enhanced API client with advanced monitoring and error handling."""
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.token_bucket = TokenBucket(
            tokens_per_second=50,
            bucket_size=100,
            burst_limit=150
        )
        self.request_metrics: Dict[str, List[float]] = {}
        self.error_metrics: Dict[str, Dict[str, int]] = {}
        self.cost_metrics: Dict[str, float] = {}
        self.last_error_time: Optional[datetime] = None
        self.consecutive_errors = 0

    def _update_metrics(
        self,
        model: str,
        duration: float,
        success: bool,
        tokens_used: Optional[int] = None,
        error_type: Optional[str] = None
    ) -> None:
        """Update comprehensive performance metrics."""
        # Update request timing metrics
        if model not in self.request_metrics:
            self.request_metrics[model] = []
        self.request_metrics[model].append(duration)

        # Keep only last 1000 requests for memory efficiency
        if len(self.request_metrics[model]) > 1000:
            self.request_metrics[model] = self.request_metrics[model][-1000:]

        # Update error metrics
        if not success:
            if model not in self.error_metrics:
                self.error_metrics[model] = {}
            error_category = error_type or "unknown"
            self.error_metrics[model][error_category] = (
                self.error_metrics[model].get(error_category, 0) + 1
            )
            self.consecutive_errors += 1
            self.last_error_time = datetime.now()
        else:
            self.consecutive_errors = 0

        # Update cost metrics if token usage is provided
        if tokens_used is not None and model in AVAILABLE_MODELS:
            cost_per_token = AVAILABLE_MODELS[model].get("cost_per_token", 0.0)
            self.cost_metrics[model] = (
                self.cost_metrics.get(model, 0.0) + tokens_used * cost_per_token
            )

    async def make_api_call_async(
        self,
        model: str,
        prompt: str,
        max_retries: int = 3,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> str:
        """Enhanced async API call with system messages and streaming support."""
        start_time = time()
        last_error: Optional[Exception] = None
        tokens_used = 0

        for attempt in range(max_retries):
            try:
                # Use burst mode if we have consecutive errors
                if not await self.token_bucket.wait_for_tokens(
                    1,
                    timeout=30,
                    burst=self.consecutive_errors > 3
                ):
                    raise TimeoutError("Token bucket timeout")

                # Prepare messages with optional system message
                messages: List[ChatCompletionMessageParam] = []
                if system_message:
                    messages.append({"role": "system", "content": system_message})
                messages.append({"role": "user", "content": prompt})

                # Prepare API parameters
                params: dict = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": AVAILABLE_MODELS[model]["max_tokens"],
                    "temperature": temperature or AVAILABLE_MODELS[model]["temperature"],
                    "stream": stream
                }

                if stream:
                    return await self._handle_streaming_response(params)

                completion = await cast(
                    Awaitable[ChatCompletion],
                    self.client.chat.completions.create(**params)
                )

                content = completion.choices[0].message.content
                if content:
                    tokens_used = completion.usage.total_tokens if completion.usage else 0
                    duration = time() - start_time
                    self._update_metrics(
                        model, duration, True, tokens_used=tokens_used
                    )
                    return content
                return ""

            except openai.RateLimitError as e:
                last_error = e
                wait_time = min(30 * (2 ** attempt), 300)  # Max 5 minutes wait
                logger.warning(
                    f"Rate limit hit for model {model}. "
                    f"Waiting {wait_time}s before retry."
                )
                self._update_metrics(
                    model,
                    time() - start_time,
                    False,
                    error_type="rate_limit"
                )
                await asyncio.sleep(wait_time)

            except openai.APIError as e:
                last_error = e
                logger.warning(f"API error occurred: {str(e)}")
                self._update_metrics(
                    model,
                    time() - start_time,
                    False,
                    error_type="api_error"
                )
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error: {str(e)}")
                self._update_metrics(
                    model,
                    time() - start_time,
                    False,
                    error_type="unexpected"
                )
                await asyncio.sleep(2 ** attempt)

        error_msg = f"Max retries reached for model {model}. Last error: {str(last_error)}"
        logger.error(error_msg)
        raise last_error if last_error else Exception(error_msg)

    async def _handle_streaming_response(
        self,
        params: dict
    ) -> str:
        """Handle streaming API responses."""
        full_response = []
        try:
            stream = await cast(
                Awaitable[AsyncIterator[ChatCompletionChunk]],
                self.client.chat.completions.create(**params)
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response.append(chunk.choices[0].delta.content)

            return "".join(full_response)

        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            raise

    async def handle_realtime_request(
        self,
        request_id: str,
        model: str,
        prompt: str,
        response_queues: Dict[str, ResponseQueue]
    ) -> None:
        """Enhanced realtime request handler with error recovery."""
        response_queue: ResponseQueue = asyncio.Queue()
        response_queues[request_id] = response_queue
        start_time = time()

        try:
            params: dict = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True
            }
            stream = await cast(
                Awaitable[AsyncIterator[ChatCompletionChunk]],
                self.client.chat.completions.create(**params)
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    await response_queue.put({
                        "type": "content",
                        "data": chunk.choices[0].delta.content,
                        "timestamp": datetime.now().isoformat()
                    })

            self._update_metrics(model, time() - start_time, True)

        except Exception as e:
            error_data = {
                "type": "error",
                "data": str(e),
                "timestamp": datetime.now().isoformat()
            }
            await response_queue.put(error_data)
            self._update_metrics(
                model,
                time() - start_time,
                False,
                error_type="realtime"
            )
        finally:
            await response_queue.put({
                "type": "done",
                "timestamp": datetime.now().isoformat()
            })
            del response_queues[request_id]

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive API performance metrics."""
        metrics = {
            "request_times": {
                model: {
                    "avg": sum(times) / len(times) if times else 0,
                    "max": max(times) if times else 0,
                    "min": min(times) if times else 0,
                    "count": len(times),
                    "last_10_avg": (
                        sum(times[-10:]) / len(times[-10:])
                        if len(times) >= 10 else None
                    )
                }
                for model, times in self.request_metrics.items()
            },
            "errors": {
                model: dict(errors)
                for model, errors in self.error_metrics.items()
            },
            "costs": dict(self.cost_metrics),
            "health": {
                "consecutive_errors": self.consecutive_errors,
                "last_error_time": (
                    self.last_error_time.isoformat()
                    if self.last_error_time else None
                )
            }
        }
        return metrics
