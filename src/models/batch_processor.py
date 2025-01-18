import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .api_client import APIClient
from .config import AVAILABLE_MODELS
from .token_bucket import TokenBucket

logger = logging.getLogger("resume_tailor")


class BatchProcessor:
    """Enhanced batch processing with monitoring and optimizations."""
    def __init__(
        self,
        api_client: APIClient,
        token_bucket: TokenBucket,
        max_batch_size: int = 50,
        auto_process_threshold: Optional[int] = None,
        cost_limit_per_batch: Optional[float] = None,
        max_concurrent_requests: int = 10
    ):
        self.api_client = api_client
        self.token_bucket = token_bucket
        self.max_batch_size = max_batch_size
        self.auto_process_threshold = auto_process_threshold
        self.cost_limit_per_batch = cost_limit_per_batch
        self.max_concurrent_requests = max_concurrent_requests
        self.batch_queue: List[Dict[str, Any]] = []
        self.processing_metrics: Dict[str, Any] = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "avg_processing_time": 0.0,
            "last_batch_size": 0,
            "last_batch_time": None,
            "total_cost": 0.0,
            "cost_savings": 0.0,
            "batch_efficiency": 0.0
        }
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def process_batch(
        self,
        batch_items: List[Dict[str, Any]],
        priority: bool = False
    ) -> List[Dict[str, Any]]:
        """Process a batch of requests with priority handling and cost management."""
        start_time = datetime.now()
        batch_size = len(batch_items)
        estimated_cost = self._estimate_batch_cost(batch_items)

        # Check cost limit
        if (
            self.cost_limit_per_batch and
            estimated_cost > self.cost_limit_per_batch
        ):
            logger.warning(
                f"Batch cost estimate {estimated_cost} exceeds limit "
                f"{self.cost_limit_per_batch}"
            )
            # Try to optimize batch by model selection
            batch_items = await self._optimize_batch_cost(
                batch_items,
                self.cost_limit_per_batch
            )
            estimated_cost = self._estimate_batch_cost(batch_items)

        # Split into smaller batches if needed
        if batch_size > self.max_batch_size:
            logger.info(f"Splitting large batch of {batch_size} items")
            results = []
            for i in range(0, batch_size, self.max_batch_size):
                sub_batch = batch_items[i:i + self.max_batch_size]
                sub_results = await self._process_batch_items(
                    sub_batch,
                    priority,
                    estimated_cost / (batch_size / self.max_batch_size)
                )
                results.extend(sub_results)
            return results

        results = await self._process_batch_items(
            batch_items,
            priority,
            estimated_cost
        )

        # Update batch processing time
        batch_time = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Batch processing completed in {batch_time:.2f}s "
            f"(estimated cost: {estimated_cost:.4f})"
        )

        return results

    async def _process_batch_items(
        self,
        items: List[Dict[str, Any]],
        priority: bool,
        estimated_cost: float
    ) -> List[Dict[str, Any]]:
        """Process a set of batch items with monitoring."""
        start_time = datetime.now()
        tasks = []

        for item in items:
            task = asyncio.create_task(self._process_batch_item(item, priority))
            tasks.append(task)

        try:
            results = await asyncio.gather(*tasks)
            actual_cost = sum(
                result.get("cost", 0.0)
                for result in results
                if result.get("success", False)
            )

            # Update cost metrics
            self.processing_metrics["total_cost"] += actual_cost
            if actual_cost < estimated_cost:
                cost_savings = estimated_cost - actual_cost
                self.processing_metrics["cost_savings"] += cost_savings
                self.processing_metrics["batch_efficiency"] = (
                    actual_cost / estimated_cost
                    if estimated_cost > 0 else 1.0
                )

            self._update_metrics(results, start_time)
            return results
        except Exception as e:
            logger.error(f"Batch processing error: {str(e)}")
            return [{"id": item["id"], "error": str(e), "success": False} for item in items]

    async def _process_batch_item(
        self,
        item: Dict[str, Any],
        priority: bool
    ) -> Dict[str, Any]:
        """Process a single batch item with enhanced error handling."""
        async with self.semaphore:  # Limit concurrent requests
            start_time = datetime.now()
            try:
                # Use burst mode for priority items
                timeout = 30 if priority else None
                if not await self.token_bucket.wait_for_tokens(1, timeout):
                    raise TimeoutError("Token bucket timeout")

                response = await self.api_client.make_api_call_async(
                    item["model"],
                    item["prompt"],
                    max_retries=5 if priority else 3
                )

                processing_time = (datetime.now() - start_time).total_seconds()
                tokens_used = len(response.split()) * 1.3  # Rough estimate
                cost = self._calculate_cost(item["model"], tokens_used)

                return {
                    "id": item["id"],
                    "response": response,
                    "success": True,
                    "processing_time": processing_time,
                    "cost": cost,
                    "tokens_used": int(tokens_used)
                }

            except Exception as e:
                logger.error(f"Error processing batch item {item['id']}: {str(e)}")
                return {
                    "id": item["id"],
                    "error": str(e),
                    "success": False,
                    "processing_time": (datetime.now() - start_time).total_seconds()
                }

    def add_to_batch(self, item: Dict[str, Any], auto_process: bool = True) -> None:
        """Add an item to the batch queue with optional auto-processing."""
        self.batch_queue.append(item)

        if (
            auto_process and
            self.auto_process_threshold and
            len(self.batch_queue) >= self.auto_process_threshold
        ):
            logger.info(
                f"Auto-processing batch of {len(self.batch_queue)} items "
                f"(threshold: {self.auto_process_threshold})"
            )
            asyncio.create_task(self.process_current_batch())

    def clear_batch(self) -> None:
        """Clear the batch queue and reset metrics."""
        self.batch_queue.clear()
        self._reset_metrics()

    async def process_current_batch(self, priority: bool = False) -> List[Dict[str, Any]]:
        """Process current batch queue with priority option."""
        if not self.batch_queue:
            return []

        batch_items = self.batch_queue.copy()
        self.clear_batch()
        return await self.process_batch(batch_items, priority)

    def get_batch_size(self) -> int:
        """Get the current size of the batch queue."""
        return len(self.batch_queue)

    def _update_metrics(
        self,
        results: List[Dict[str, Any]],
        start_time: datetime
    ) -> None:
        """Update processing metrics."""
        batch_time = (datetime.now() - start_time).total_seconds()
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful

        self.processing_metrics["total_processed"] += len(results)
        self.processing_metrics["successful"] += successful
        self.processing_metrics["failed"] += failed
        self.processing_metrics["last_batch_size"] = len(results)
        self.processing_metrics["last_batch_time"] = batch_time

        # Update average processing time
        if "processing_time" in results[0]:
            times = [r["processing_time"] for r in results]
            avg_time = sum(times) / len(times)
            if self.processing_metrics["avg_processing_time"] == 0:
                self.processing_metrics["avg_processing_time"] = avg_time
            else:
                self.processing_metrics["avg_processing_time"] = (
                    self.processing_metrics["avg_processing_time"] * 0.9 + avg_time * 0.1
                )

    def _reset_metrics(self) -> None:
        """Reset processing metrics."""
        self.processing_metrics = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "avg_processing_time": 0.0,
            "last_batch_size": 0,
            "last_batch_time": None
        }

    def _estimate_batch_cost(self, items: List[Dict[str, Any]]) -> float:
        """Estimate the cost of processing a batch."""
        total_cost = 0.0
        for item in items:
            # Rough token estimate based on prompt length
            estimated_tokens = len(item["prompt"].split()) * 1.3
            total_cost += self._calculate_cost(item["model"], estimated_tokens)
        return total_cost

    def _calculate_cost(self, model: str, tokens: float) -> float:
        """Calculate cost for a specific model and token count."""
        if model in AVAILABLE_MODELS:
            return float(tokens * AVAILABLE_MODELS[model].get("cost_per_token", 0.0))
        return 0.0

    async def _optimize_batch_cost(
        self,
        items: List[Dict[str, Any]],
        cost_limit: float
    ) -> List[Dict[str, Any]]:
        """Optimize batch processing to meet cost constraints."""
        optimized_items = []
        current_cost = 0.0

        # Sort items by priority/importance
        sorted_items = sorted(
            items,
            key=lambda x: x.get("priority", 0),
            reverse=True
        )

        for item in sorted_items:
            # Try to find a cheaper model that can handle the request
            original_model = item["model"]
            for model in AVAILABLE_MODELS:
                if model == original_model:
                    continue

                estimated_tokens = len(item["prompt"].split()) * 1.3
                new_cost = self._calculate_cost(model, estimated_tokens)

                if new_cost < self._calculate_cost(original_model, estimated_tokens):
                    item["model"] = model
                    break

            item_cost = self._estimate_batch_cost([item])
            if current_cost + item_cost <= cost_limit:
                optimized_items.append(item)
                current_cost += item_cost
            else:
                logger.warning(
                    f"Skipping item {item['id']} due to cost constraints"
                )

        return optimized_items

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive processing metrics including cost analysis."""
        metrics = dict(self.processing_metrics)
        metrics["cost_efficiency"] = (
            self.processing_metrics["cost_savings"] /
            self.processing_metrics["total_cost"]
            if self.processing_metrics["total_cost"] > 0 else 0.0
        )
        return metrics
