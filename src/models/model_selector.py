import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .config import AVAILABLE_MODELS
from .types import PerformanceMetrics, ModelConfig


class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass
class ModelPerformance:
    """Track model performance metrics."""
    success_rate: float = 0.0
    avg_latency: float = 0.0
    cost_efficiency: float = 0.0
    error_rate: float = 0.0
    last_used: Optional[datetime] = None
    total_uses: int = 0
    token_efficiency: float = 0.0
    cache_hit_rate: float = 0.0
    avg_response_quality: float = 0.0


logger = logging.getLogger("resume_tailor")


class ModelSelector:
    """Enhanced model selector with advanced selection strategies."""
    def __init__(self, config: Optional[ModelConfig] = None):
        self.performance_history: PerformanceMetrics = {}
        self.model_usage: Dict[str, List[datetime]] = {
            model: [] for model in AVAILABLE_MODELS
        }
        self.model_costs: Dict[str, float] = {
            model: AVAILABLE_MODELS[model].get("cost_per_token", 0.0)
            for model in AVAILABLE_MODELS
        }
        self.model_performance: Dict[str, ModelPerformance] = {
            model: ModelPerformance() for model in AVAILABLE_MODELS
        }
        self.task_affinities: Dict[str, Set[str]] = {}
        self.backup_models: Dict[str, str] = {}
        self.last_performance_update = datetime.now()
        self.performance_window = timedelta(hours=24)
        self.model_switch_threshold = 0.2  # 20% performance difference triggers switch
        self.cost_efficiency_weight = 0.4
        self.success_rate_weight = 0.3
        self.latency_weight = 0.2
        self.quality_weight = 0.1

    async def select_model(
        self,
        task_type: str,
        content_length: int,
        required_accuracy: float,
        priority: TaskPriority = TaskPriority.MEDIUM,
        max_cost: Optional[float] = None,
        fallback_allowed: bool = True,
        optimize_for_cost: bool = False
    ) -> str:
        """Select the most appropriate model based on requirements."""
        # Update performance metrics if needed
        if datetime.now() - self.last_performance_update > self.performance_window:
            await self._update_performance_metrics()

        suitable_models = await self._get_suitable_models(
            task_type,
            content_length,
            required_accuracy,
            max_cost
        )

        if not suitable_models:
            if not fallback_allowed:
                raise ValueError("No suitable models found and fallback not allowed")
            return await self._select_fallback_model(task_type, content_length)

        # Select model based on priority and optimization preferences
        if optimize_for_cost:
            return await self._select_cost_efficient_model(suitable_models, task_type)
        elif priority == TaskPriority.HIGH:
            return await self._select_high_priority_model(suitable_models, task_type)
        elif priority == TaskPriority.LOW:
            return await self._select_balanced_model(suitable_models, task_type)
        else:
            return await self._select_balanced_model(suitable_models, task_type)

    async def _select_high_priority_model(
        self,
        models: List[str],
        task_type: str
    ) -> str:
        """Select best performing model regardless of cost."""
        return max(
            models,
            key=lambda m: (
                self.model_performance[m].success_rate * self.success_rate_weight
                + self.model_performance[m].avg_response_quality * self.quality_weight
                + (1 - self.model_performance[m].error_rate) * 0.2
                + (1 - self.model_performance[m].avg_latency / 10) * self.latency_weight
            )
        )

    async def _select_cost_efficient_model(
        self,
        models: List[str],
        task_type: str
    ) -> str:
        """Select most cost-efficient model that meets requirements."""
        return max(
            models,
            key=lambda m: (
                self.model_performance[m].cost_efficiency * self.cost_efficiency_weight
                + self.model_performance[m].token_efficiency * 0.3
                + self.model_performance[m].cache_hit_rate * 0.3
            )
        )

    async def _select_balanced_model(
        self,
        models: List[str],
        task_type: str
    ) -> str:
        """Select model balancing performance and cost."""
        return max(
            models,
            key=lambda m: (
                self.model_performance[m].success_rate * self.success_rate_weight
                + self.model_performance[m].cost_efficiency * self.cost_efficiency_weight
                + (1 - self.model_performance[m].avg_latency / 10) * self.latency_weight
                + self.model_performance[m].avg_response_quality * self.quality_weight
            )
        )

    async def _select_fallback_model(
        self,
        task_type: str,
        content_length: int
    ) -> str:
        """Select a fallback model when no suitable models are found."""
        # First try backup models if defined
        for model in AVAILABLE_MODELS:
            if (
                model in self.backup_models
                and content_length <= AVAILABLE_MODELS[self.backup_models[model]]["max_tokens"]
            ):
                return self.backup_models[model]

        # Otherwise select most basic model that can handle the content length
        available = [
            m for m in AVAILABLE_MODELS
            if content_length <= AVAILABLE_MODELS[m]["max_tokens"]
        ]
        if not available:
            raise ValueError("No models can handle the content length")
        return min(available, key=lambda m: self.model_costs[m])

    async def _get_suitable_models(
        self,
        task_type: str,
        content_length: int,
        required_accuracy: float,
        max_cost: Optional[float] = None
    ) -> List[str]:
        """Get list of suitable models based on requirements."""
        suitable_models = []

        for model_name, config in AVAILABLE_MODELS.items():
            # Check basic requirements
            if content_length > config["max_tokens"]:
                continue

            # Check accuracy requirements
            metrics = config["success_metrics"]
            if (
                metrics["terminology_accuracy"] < required_accuracy
                or metrics["skill_match"] < required_accuracy
            ):
                continue

            # Check cost constraints if specified
            if max_cost is not None:
                estimated_cost = self._estimate_cost(model_name, content_length)
                if estimated_cost > max_cost:
                    continue

            # Check performance thresholds
            perf = self.model_performance[model_name]
            if (
                perf.error_rate > 0.2
                or perf.success_rate < required_accuracy
            ):
                continue

            suitable_models.append(model_name)

        return suitable_models

    async def _update_performance_metrics(self) -> None:
        """Update performance metrics for all models."""
        now = datetime.now()
        window_start = now - self.performance_window

        for model in AVAILABLE_MODELS:
            # Filter recent usage
            recent_usage = [
                t for t in self.model_usage[model]
                if t > window_start
            ]

            if recent_usage:
                perf = self.model_performance[model]
                perf.total_uses = len(recent_usage)
                perf.last_used = max(recent_usage)

                # Get recent performance metrics
                recent_metrics = [
                    score for (m, task), score in self.performance_history.items()
                    if m == model
                ]

                if recent_metrics:
                    successful_count = sum(
                        1 for score in recent_metrics if score >= 0.8
                    )
                    perf.success_rate = successful_count / len(recent_metrics)
                    perf.error_rate = 1.0 - perf.success_rate

                    # Calculate cost efficiency
                    total_cost = self.model_costs[model] * len(recent_usage)
                    if total_cost > 0:
                        perf.cost_efficiency = perf.success_rate / total_cost

                    # Check if model switch is needed
                    await self._check_model_switch(model, perf)

        self.last_performance_update = now

    async def _check_model_switch(
        self,
        model: str,
        performance: ModelPerformance
    ) -> None:
        """Check if model should be switched based on performance."""
        if performance.success_rate < 0.5:  # Consistent poor performance
            for backup_model, backup_perf in self.model_performance.items():
                if (
                    backup_model != model
                    and backup_perf.success_rate > (
                        performance.success_rate + self.model_switch_threshold
                    )
                ):
                    self.backup_models[model] = backup_model
                    logger.info(
                        f"Switching model {model} to {backup_model} due to "
                        f"performance difference"
                    )
                    break

    def _estimate_cost(self, model: str, content_length: int) -> float:
        """Estimate the cost of using a model for given content length."""
        cost_per_token = self.model_costs[model]
        # Rough estimate of tokens (assuming 4 chars per token on average)
        estimated_tokens = content_length / 4
        return cost_per_token * estimated_tokens

    def update_performance(
        self,
        model: str,
        task_type: str,
        performance_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update performance history for a model."""
        self.performance_history[(model, task_type)] = performance_score
        self.model_usage[model].append(datetime.now())

        # Update advanced metrics if metadata is provided
        if metadata and model in self.model_performance:
            perf = self.model_performance[model]
            if "response_quality" in metadata:
                perf.avg_response_quality = (
                    perf.avg_response_quality * 0.7
                    + float(metadata["response_quality"]) * 0.3
                )
            if "token_efficiency" in metadata:
                perf.token_efficiency = float(metadata["token_efficiency"])
            if "cache_hit" in metadata:
                hits = perf.cache_hit_rate * perf.total_uses
                perf.cache_hit_rate = (hits + float(metadata["cache_hit"])) / (
                    perf.total_uses + 1
                )

        if metadata:
            logger.info(
                f"Model {model} performance updated - Score: {performance_score}, "
                f"Task: {task_type}, Metadata: {metadata}"
            )

    def get_model_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics about model usage and performance."""
        stats = {}
        for model in AVAILABLE_MODELS:
            perf = self.model_performance[model]
            relevant_scores = [
                score for (m, _), score in self.performance_history.items()
                if m == model
            ]

            stats[model] = {
                "total_uses": perf.total_uses,
                "last_used": perf.last_used,
                "success_rate": perf.success_rate,
                "cost_efficiency": perf.cost_efficiency,
                "error_rate": perf.error_rate,
                "avg_response_quality": perf.avg_response_quality,
                "token_efficiency": perf.token_efficiency,
                "cache_hit_rate": perf.cache_hit_rate,
                "avg_performance": (
                    sum(relevant_scores) / len(relevant_scores)
                    if relevant_scores else None
                ),
                "cost_per_token": self.model_costs[model]
            }

        return stats

    def get_task_performance(self, task_type: str) -> Dict[str, float]:
        """Get performance metrics for a specific task type."""
        return {
            model: score
            for (model, task), score in self.performance_history.items()
            if task == task_type
        }

    def optimize_model_selection(
        self,
        budget: float,
        performance_threshold: float
    ) -> Dict[str, Tuple[str, float]]:
        """Optimize model selection based on budget and performance requirements."""
        task_models = {}
        for task_type in set(task for _, task in self.performance_history.keys()):
            task_perf = self.get_task_performance(task_type)
            suitable_models = [
                model for model, score in task_perf.items()
                if score >= performance_threshold
            ]

            if suitable_models:
                # Select the most cost-effective model that meets performance requirements
                selected = min(
                    suitable_models,
                    key=lambda m: self.model_costs[m]
                )
                task_models[task_type] = (
                    selected,
                    self.model_costs[selected]
                )
            else:
                # Fall back to best performing model regardless of cost
                selected = max(task_perf.items(), key=lambda x: x[1])[0]
                task_models[task_type] = (
                    selected,
                    self.model_costs[selected]
                )

        return task_models
