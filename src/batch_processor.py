import json
import logging
from typing import Dict, List, Optional, Any
from openai import OpenAI
from openai.types import FileObject, Batch
from datetime import datetime


logger = logging.getLogger("resume_tailor")


class BatchProcessor:
    """Handles batch processing of resume tailoring requests."""

    def __init__(self, client: Optional[OpenAI] = None) -> None:
        self.client = client or OpenAI()
        self.batch_metrics: Dict[str, Dict] = {}

    def prepare_batch_file(self, requests: List[Dict[str, Any]]) -> FileObject:
        """Prepare requests in JSONL format for batch processing."""
        batch_data = []
        for idx, request in enumerate(requests):
            batch_data.append({
                "custom_id": f"request-{idx}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": request.get("model", "gpt-4"),
                    "messages": request.get("messages", []),
                    "max_tokens": request.get("max_tokens", 1000)
                }
            })

        # Create batch file using bytes for file content
        batch_content = json.dumps(batch_data).encode('utf-8')
        batch_file = self.client.files.create(
            file=batch_content,
            purpose="batch"
        )
        return batch_file

    def submit_batch(self, batch_file_id: str) -> Batch:
        """Submit a batch for processing."""
        try:
            batch = self.client.batches.create(
                input_file_id=batch_file_id,
                endpoint="/v1/chat/completions",
                completion_window="24h"
            )
            self.batch_metrics[batch.id] = {
                "start_time": datetime.now(),
                "status": batch.status,
                "total_requests": batch.request_counts.total if batch.request_counts else 0
            }
            return batch
        except Exception as e:
            logger.error(f"Failed to submit batch: {e}")
            raise

    def monitor_batch(self, batch_id: str) -> Batch:
        """Monitor batch progress and update metrics."""
        try:
            batch = self.client.batches.retrieve(batch_id)
            self.batch_metrics[batch_id].update({
                "current_status": batch.status,
                "completed_requests": batch.request_counts.completed if batch.request_counts else 0,
                "failed_requests": batch.request_counts.failed if batch.request_counts else 0,
                "last_checked": datetime.now()
            })
            return batch
        except Exception as e:
            logger.error(f"Failed to monitor batch {batch_id}: {e}")
            raise

    def get_batch_results(self, output_file_id: str) -> List[Dict]:
        """Retrieve and parse batch results."""
        try:
            response = self.client.files.content(output_file_id)
            results = [json.loads(line) for line in response.text.splitlines()]
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve batch results: {e}")
            raise
