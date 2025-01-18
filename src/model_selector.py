import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


logger = logging.getLogger("resume_tailor")


@dataclass
class ModelPerformance:
    """Performance metrics for a model."""
    success_rate: float
    avg_latency: float
    cost_per_token: float
    last_used: datetime
    total_uses: int


@dataclass
class ModelRequirements:
    """Requirements for model selection."""
    min_success_rate: float = 0.8
    max_latency_ms: float = 5000.0
    max_cost_per_1k: float = 0.02
    priority: str = "balanced"  # One of: balanced, speed, cost, quality


class ModelSelector:
    """Automated model selection based on requirements and performance."""

    def __init__(self) -> None:
        # Initialize with default model configurations from user.log
        self.models: Dict[str, Dict[str, Any]] = {
            "gpt-4": {
                "input_cost": 0.00250,
                "output_cost": 0.01000,
                "capabilities": ["high_quality", "complex_reasoning"],
                "max_tokens": 3000,
                "typical_latency": 2000,  # ms
            },
            "o1-mini": {
                "input_cost": 0.0030,
                "output_cost": 0.0120,
                "capabilities": ["fast_inference", "validation"],
                "max_tokens": 2000,
                "typical_latency": 1000,  # ms
            },
            "o1-preview": {
                "input_cost": 0.00250,
                "output_cost": 0.01000,
                "capabilities": ["executive_polish", "refinement"],
                "max_tokens": 2500,
                "typical_latency": 1500,  # ms
            }
        }
        self.performance_history: Dict[str, ModelPerformance] = {}
        self._initialize_performance_history()

    def _initialize_performance_history(self) -> None:
        """Initialize performance history with default values."""
        now = datetime.now()
        for model in self.models:
            self.performance_history[model] = ModelPerformance(
                success_rate=0.9,  # Start optimistic
                avg_latency=self.models[model]["typical_latency"],
                cost_per_token=(
                    self.models[model]["input_cost"] +
                    self.models[model]["output_cost"]
                ) / 2,
                last_used=now,
                total_uses=0
            )

    def select_model(
        self,
        task_type: str,
        requirements: Optional[ModelRequirements] = None,
        content_length: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Select the best model based on task requirements and performance history.

        Args:
            task_type: Type of task (e.g., 'initial_draft', 'refinement', 'validation')
            requirements: Specific requirements for model selection
            content_length: Length of content to process (for token estimation)

        Returns:
            Tuple of (selected model name, model configuration)
        """
        reqs = requirements or ModelRequirements()

        # Filter models meeting basic requirements
        qualified_models = self._filter_qualified_models(reqs)

        if not qualified_models:
            logger.warning("No models meet basic requirements, using fallback model")
            return "o1-mini", self.models["o1-mini"]

        # Score models based on priority
        model_scores = self._score_models(qualified_models, reqs.priority, task_type)

        # Select best model
        selected_model = max(model_scores.items(), key=lambda x: x[1])[0]

        return selected_model, self.models[selected_model]

    def _filter_qualified_models(
        self,
        requirements: ModelRequirements
    ) -> List[str]:
        """Filter models meeting basic requirements."""
        qualified = []

        for model, perf in self.performance_history.items():
            if (
                perf.success_rate >= requirements.min_success_rate and
                perf.avg_latency <= requirements.max_latency_ms and
                perf.cost_per_token * 1000 <= requirements.max_cost_per_1k
            ):
                qualified.append(model)

        return qualified

    def _score_models(
        self,
        models: List[str],
        priority: str,
        task_type: str
    ) -> Dict[str, float]:
        """Score models based on priority and task type."""
        scores: Dict[str, float] = {}

        # Weight factors based on priority
        weights = self._get_priority_weights(priority)

        for model in models:
            perf = self.performance_history[model]
            # Calculate base score components
            quality_score = perf.success_rate
            speed_score = 1.0 - (perf.avg_latency / 5000.0)  # Normalize to 0-1
            cost_score = 1.0 - (perf.cost_per_token / 0.02)  # Normalize to 0-1

            # Apply task-specific adjustments
            task_multiplier = self._get_task_multiplier(model, task_type)

            # Calculate weighted score
            scores[model] = (
                weights["quality"] * quality_score +
                weights["speed"] * speed_score +
                weights["cost"] * cost_score
            ) * task_multiplier

        return scores

    def _get_priority_weights(self, priority: str) -> Dict[str, float]:
        """Get weight factors based on priority."""
        if priority == "speed":
            return {"quality": 0.2, "speed": 0.6, "cost": 0.2}
        elif priority == "cost":
            return {"quality": 0.2, "speed": 0.2, "cost": 0.6}
        elif priority == "quality":
            return {"quality": 0.6, "speed": 0.2, "cost": 0.2}
        else:  # balanced
            return {"quality": 0.4, "speed": 0.3, "cost": 0.3}

    def _get_task_multiplier(self, model: str, task_type: str) -> float:
        """Get task-specific multiplier for model scoring."""
        capabilities = self.models[model]["capabilities"]

        multipliers = {
            "initial_draft": 1.2 if "high_quality" in capabilities else 1.0,
            "refinement": 1.2 if "refinement" in capabilities else 1.0,
            "validation": 1.2 if "validation" in capabilities else 1.0
        }

        return multipliers.get(task_type, 1.0)

    def update_performance(
        self,
        model: str,
        success: bool,
        latency: float,
        tokens_used: int,
        cost: float
    ) -> None:
        """
        Update performance history for a model.

        Args:
            model: Model name
            success: Whether the task was successful
            latency: Task latency in milliseconds
            tokens_used: Number of tokens used
            cost: Total cost for the task
        """
        if model not in self.performance_history:
            logger.warning(f"Unknown model {model} in performance update")
            return

        perf = self.performance_history[model]

        # Update success rate with exponential moving average
        alpha = 0.1  # Weight for new data
        new_success_rate = (
            (1 - alpha) * perf.success_rate +
            alpha * (1.0 if success else 0.0)
        )

        # Update average latency
        new_avg_latency = (
            (perf.avg_latency * perf.total_uses + latency) /
            (perf.total_uses + 1)
        )

        # Update cost per token
        new_cost_per_token = cost / tokens_used if tokens_used > 0 else perf.cost_per_token

        self.performance_history[model] = ModelPerformance(
            success_rate=new_success_rate,
            avg_latency=new_avg_latency,
            cost_per_token=new_cost_per_token,
            last_used=datetime.now(),
            total_uses=perf.total_uses + 1
        )

    def get_model_stats(self, model: str) -> Optional[Dict[str, Any]]:
        """Get performance statistics for a model."""
        if model not in self.performance_history:
            return None

        perf = self.performance_history[model]
        config = self.models[model]

        return {
            "performance": asdict(perf),
            "configuration": config,
            "cost_efficiency": perf.success_rate / perf.cost_per_token,
            "speed_efficiency": perf.success_rate / (perf.avg_latency / 1000)
        }
