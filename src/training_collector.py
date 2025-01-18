import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path


logger = logging.getLogger("resume_tailor")


@dataclass
class TrainingExample:
    """Represents a single training example."""
    original_content: str
    tailored_content: str
    job_description: str
    persona: str
    model_used: str
    success_metrics: Dict[str, float]
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TrainingMetrics:
    """Metrics for training data collection."""
    total_examples: int = 0
    successful_examples: int = 0
    avg_improvement_score: float = 0.0
    collection_start: Optional[datetime] = None
    last_update: Optional[datetime] = None


class TrainingDataCollector:
    """Collects and manages training data for model improvement."""

    def __init__(
        self,
        storage_dir: str = "training_data",
        max_examples_per_file: int = 1000
    ) -> None:
        """
        Initialize the training data collector.

        Args:
            storage_dir: Directory to store training data
            max_examples_per_file: Maximum examples per JSONL file
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_examples_per_file = max_examples_per_file
        self.metrics = TrainingMetrics(collection_start=datetime.now())
        self.current_file_examples = 0
        self._load_metrics()

    def _get_current_file_path(self) -> Path:
        """Get path for current training data file."""
        timestamp = datetime.now().strftime("%Y%m%d")
        file_index = self.current_file_examples // self.max_examples_per_file
        return self.storage_dir / f"training_data_{timestamp}_{file_index}.jsonl"

    def _load_metrics(self) -> None:
        """Load existing metrics from storage."""
        metrics_file = self.storage_dir / "metrics.json"
        if metrics_file.exists():
            try:
                with open(metrics_file, "r") as f:
                    data = json.load(f)
                    self.metrics = TrainingMetrics(**data)
            except Exception as e:
                logger.error(f"Failed to load metrics: {e}")

    def _save_metrics(self) -> None:
        """Save current metrics to storage."""
        metrics_file = self.storage_dir / "metrics.json"
        try:
            with open(metrics_file, "w") as f:
                json.dump(asdict(self.metrics), f, default=str)
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")

    def add_example(
        self,
        example: TrainingExample,
        calculate_improvement: bool = True
    ) -> None:
        """
        Add a new training example to the collection.

        Args:
            example: Training example to add
            calculate_improvement: Whether to calculate improvement metrics
        """
        try:
            # Convert example to dictionary for storage
            example_dict = asdict(example)
            example_dict["timestamp"] = example.timestamp.isoformat()

            # Write to current file
            current_file = self._get_current_file_path()
            with open(current_file, "a") as f:
                json.dump(example_dict, f)
                f.write("\n")

            self.current_file_examples += 1
            self.metrics.total_examples += 1
            self.metrics.last_update = datetime.now()

            if calculate_improvement:
                improvement_score = self._calculate_improvement(example)
                if improvement_score > 0:
                    self.metrics.successful_examples += 1
                    # Update running average
                    self.metrics.avg_improvement_score = (
                        (self.metrics.avg_improvement_score *
                         (self.metrics.successful_examples - 1) +
                         improvement_score) / self.metrics.successful_examples
                    )

            # Rotate file if needed
            if self.current_file_examples >= self.max_examples_per_file:
                self.current_file_examples = 0

            self._save_metrics()

        except Exception as e:
            logger.error(f"Failed to add training example: {e}")
            raise

    def _calculate_improvement(self, example: TrainingExample) -> float:
        """
        Calculate improvement score for a training example.

        Args:
            example: Training example to evaluate

        Returns:
            Improvement score between 0 and 1
        """
        # Use success metrics if available
        if example.success_metrics:
            weights = {
                "format_retention": 0.3,
                "terminology_accuracy": 0.4,
                "skill_match": 0.3
            }
            score = sum(
                example.success_metrics.get(metric, 0) * weight
                for metric, weight in weights.items()
            )
            return min(max(score, 0), 1)
        return 0.0

    def get_training_examples(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        model: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[TrainingExample]:
        """
        Retrieve training examples based on filters.

        Args:
            start_date: Filter by start date
            end_date: Filter by end date
            model: Filter by model used
            limit: Maximum number of examples to return

        Returns:
            List of filtered training examples
        """
        examples = []
        try:
            for file_path in sorted(self.storage_dir.glob("training_data_*.jsonl")):
                with open(file_path, "r") as f:
                    for line in f:
                        example_dict = json.loads(line)
                        example_dict["timestamp"] = datetime.fromisoformat(
                            example_dict["timestamp"]
                        )
                        example = TrainingExample(**example_dict)

                        if start_date and example.timestamp < start_date:
                            continue
                        if end_date and example.timestamp > end_date:
                            continue
                        if model and example.model_used != model:
                            continue

                        examples.append(example)
                        if limit and len(examples) >= limit:
                            return examples

            return examples

        except Exception as e:
            logger.error(f"Failed to retrieve training examples: {e}")
            return []

    def get_metrics(self) -> TrainingMetrics:
        """Get current training metrics."""
        return self.metrics

    def clear_old_data(self, days_to_keep: int = 30) -> int:
        """
        Clear training data older than specified days.

        Args:
            days_to_keep: Number of days of data to retain

        Returns:
            Number of files removed
        """
        cutoff_date = datetime.now().strftime("%Y%m%d")
        removed = 0

        try:
            for file_path in self.storage_dir.glob("training_data_*.jsonl"):
                file_date = file_path.stem.split("_")[2]
                if file_date < cutoff_date:
                    file_path.unlink()
                    removed += 1

            return removed

        except Exception as e:
            logger.error(f"Failed to clear old training data: {e}")
            return 0
