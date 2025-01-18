import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger("resume_tailor")


@dataclass
class TrainingExample:
    """Structure for a single training example."""
    prompt: str
    response: str
    model: str
    timestamp: str
    metadata: Dict[str, Any]
    feedback: List[Dict[str, Any]]
    performance_metrics: Dict[str, float]
    validation_status: str = "pending"


class TrainingCollector:
    """Enhanced training data collector with validation pipeline."""
    def __init__(
        self,
        data_dir: str = "training_data",
        validation_threshold: float = 0.8,
        auto_validate: bool = True
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.current_batch: List[TrainingExample] = []
        self.batch_size = 100
        self.validation_threshold = validation_threshold
        self.auto_validate = auto_validate
        self.validation_queue: asyncio.Queue[TrainingExample] = asyncio.Queue()
        self.validated_examples: Set[str] = set()
        self.validation_metrics: Dict[str, Dict[str, float]] = {}

        # Initialize validation worker task as None
        self.validation_worker_task: Optional[asyncio.Task[None]] = None

    async def start_validation_worker(self) -> None:
        """Start the validation worker if auto-validate is enabled."""
        if self.auto_validate and self.validation_worker_task is None:
            try:
                loop = asyncio.get_running_loop()
                self.validation_worker_task = loop.create_task(
                    self._validation_worker()
                )
            except RuntimeError:
                logger.warning("No running event loop, validation worker not started")

    async def collect_interaction(
        self,
        prompt: str,
        response: str,
        model: str,
        metadata: Optional[Dict[str, Any]] = None,
        performance_metrics: Optional[Dict[str, float]] = None
    ) -> str:
        """Collect a single interaction for training."""
        example = TrainingExample(
            prompt=prompt,
            response=response,
            model=model,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {},
            feedback=[],
            performance_metrics=performance_metrics or {},
            validation_status="pending"
        )

        self.current_batch.append(example)
        if len(self.current_batch) >= self.batch_size:
            await self._save_batch()

        # Add to validation queue if auto-validate is enabled
        if self.auto_validate:
            await self.validation_queue.put(example)

        example_id = f"{example.timestamp}_{hash(example.prompt)}"
        return example_id

    async def collect_feedback(
        self,
        example_id: str,
        feedback: Dict[str, Any],
        source: str = "user",
        trigger_validation: bool = True
    ) -> None:
        """Collect feedback on a specific interaction."""
        feedback_data = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "feedback": feedback
        }

        try:
            example_file = self.data_dir / f"example_{example_id}.json"
            if example_file.exists():
                with example_file.open("r") as f:
                    example_data = json.load(f)
                    example_data["feedback"].append(feedback_data)

                    if trigger_validation:
                        example = TrainingExample(**example_data)
                        await self.validation_queue.put(example)

                with example_file.open("w") as f:
                    json.dump(example_data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving feedback: {e}")

    async def _save_batch(self) -> None:
        """Save the current batch of interactions."""
        if not self.current_batch:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_file = self.data_dir / f"batch_{timestamp}.jsonl"

        try:
            with batch_file.open("w") as f:
                for example in self.current_batch:
                    f.write(json.dumps(asdict(example)) + "\n")
            self.current_batch = []
            logger.info(f"Saved training batch to {batch_file}")
        except Exception as e:
            logger.error(f"Error saving training batch: {e}")

    async def _validation_worker(self) -> None:
        """Background worker for validating training examples."""
        while True:
            example = await self.validation_queue.get()
            try:
                validation_result = await self._validate_example(example)
                example_id = f"{example.timestamp}_{hash(example.prompt)}"

                if validation_result[0] >= self.validation_threshold:
                    self.validated_examples.add(example_id)
                    example.validation_status = "validated"
                else:
                    example.validation_status = "failed"
                    logger.warning(
                        f"Example {example_id} failed validation: {validation_result[1]}"
                    )

                # Update validation metrics
                self.validation_metrics[example_id] = {
                    "score": validation_result[0],
                    "timestamp": float(datetime.now().timestamp())
                }

                # Save updated example
                example_file = self.data_dir / f"example_{example_id}.json"
                with example_file.open("w") as f:
                    json.dump(asdict(example), f, indent=2)

            except Exception as e:
                logger.error(f"Validation error: {str(e)}")
            finally:
                self.validation_queue.task_done()

    async def _validate_example(
        self,
        example: TrainingExample
    ) -> Tuple[float, str]:
        """Validate a training example."""
        score = 0.0
        reasons = []

        # Check response quality
        if len(example.response) < 10:
            reasons.append("Response too short")
        else:
            score += 0.3

        # Check feedback sentiment if available
        if example.feedback:
            positive_feedback = sum(
                1 for f in example.feedback
                if f.get("sentiment", "neutral") == "positive"
            )
            score += 0.3 * (positive_feedback / len(example.feedback))

        # Check performance metrics
        if example.performance_metrics:
            avg_performance = sum(example.performance_metrics.values()) / len(
                example.performance_metrics
            )
            score += 0.4 * avg_performance

        return score, ", ".join(reasons)

    def get_training_stats(self) -> Dict[str, Any]:
        """Get statistics about collected training data."""
        stats: Dict[str, Any] = {
            "total_files": 0,
            "total_examples": 0,
            "validated_examples": len(self.validated_examples),
            "validation_rate": 0.0,
            "models": dict[str, int](),
            "feedback_count": 0,
            "avg_validation_score": 0.0
        }

        try:
            # Count example files and gather statistics
            validation_scores = []
            for example_file in self.data_dir.glob("example_*.json"):
                stats["total_files"] += 1
                with example_file.open("r") as f:
                    example_data = json.load(f)
                    stats["total_examples"] += 1

                    model = str(example_data["model"])
                    if model not in stats["models"]:
                        stats["models"][model] = 0
                    stats["models"][model] += 1

                    stats["feedback_count"] += len(example_data["feedback"])

                    if example_data["validation_status"] == "validated":
                        example_id = f"{example_data['timestamp']}_{hash(example_data['prompt'])}"
                        if example_id in self.validation_metrics:
                            validation_scores.append(
                                self.validation_metrics[example_id]["score"]
                            )

            if validation_scores:
                stats["avg_validation_score"] = sum(validation_scores) / len(validation_scores)
            if stats["total_examples"] > 0:
                stats["validation_rate"] = (
                    len(self.validated_examples) / stats["total_examples"]
                )

        except Exception as e:
            logger.error(f"Error calculating training stats: {e}")

        return stats

    def get_recent_interactions(
        self,
        limit: int = 10,
        model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get most recent interactions, optionally filtered by model."""
        interactions = []
        try:
            # Get all batch files, sorted by timestamp (newest first)
            batch_files = sorted(
                self.data_dir.glob("batch_*.jsonl"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            for batch_file in batch_files:
                with batch_file.open("r") as f:
                    for line in f:
                        interaction = json.loads(line)
                        if model and interaction["model"] != model:
                            continue
                        interactions.append(interaction)
                        if len(interactions) >= limit:
                            break
                if len(interactions) >= limit:
                    break

        except Exception as e:
            logger.error(f"Error retrieving recent interactions: {e}")

        return interactions[:limit]

    def cleanup_old_data(self, days: int = 30) -> None:
        """Remove training data older than specified days."""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        try:
            for file in self.data_dir.glob("*"):
                if file.stat().st_mtime < cutoff:
                    file.unlink()
                    logger.info(f"Removed old training data file: {file}")
        except Exception as e:
            logger.error(f"Error cleaning up old training data: {e}")

    async def export_training_data(
        self,
        output_file: str,
        format: str = "jsonl",
        validated_only: bool = True
    ) -> None:
        """Export all training data to a single file."""
        try:
            examples = []
            for example_file in sorted(self.data_dir.glob("example_*.json")):
                with example_file.open("r") as f:
                    example_data = json.load(f)
                    if (
                        not validated_only or
                        example_data["validation_status"] == "validated"
                    ):
                        examples.append(example_data)

            with open(output_file, "w") as out_f:
                if format == "jsonl":
                    for example in examples:
                        out_f.write(json.dumps(example) + "\n")
                else:
                    json.dump(examples, out_f, indent=2)

            logger.info(f"Exported training data to {output_file}")
        except Exception as e:
            logger.error(f"Error exporting training data: {e}")
