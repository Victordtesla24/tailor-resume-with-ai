import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .api_client import APIClient
from .batch_processor import BatchProcessor
from .config import AVAILABLE_MODELS, PERSONAS_CACHED
from .format_handler import FormatHandler
from .model_selector import ModelSelector, TaskPriority
from .prompt_cache import PromptCache
from .realtime_handler import RealtimeHandler
from .skill_analyzer import SkillAnalyzer
from .token_bucket import TokenBucket
from .training_collector import TrainingCollector
from .types import PerformanceMetrics

logger = logging.getLogger("resume_tailor")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class ModelManager:
    """Main orchestrator for all model-related functionality."""
    def __init__(
        self,
        max_cost_per_request: Optional[float] = None,
        performance_threshold: float = 0.8,
        auto_optimize: bool = True,
        cost_optimization_target: Optional[float] = None,
        enable_advanced_monitoring: bool = True
    ) -> None:
        self.token_bucket = TokenBucket(
            tokens_per_second=50,
            bucket_size=100,
            burst_limit=150
        )
        self.api_client = APIClient()
        self.format_handler = FormatHandler()
        self.skill_analyzer = SkillAnalyzer()
        self.model_selector = ModelSelector()
        self.prompt_cache = PromptCache()
        self.realtime_handler = RealtimeHandler(self.api_client)
        self.batch_processor = BatchProcessor(
            self.api_client,
            self.token_bucket,
            max_batch_size=50,
            auto_process_threshold=10
        )
        self.training_collector = TrainingCollector()

        # Cost and performance settings
        self.max_cost_per_request = max_cost_per_request
        self.performance_threshold = performance_threshold
        self.auto_optimize = auto_optimize
        self.cost_optimization_target = cost_optimization_target
        self.enable_advanced_monitoring = enable_advanced_monitoring
        self.optimization_metrics: Dict[str, Any] = {
            "total_cost": 0.0,
            "cost_savings": 0.0,
            "performance_scores": {},
            "model_switches": 0,
            "cost_efficiency": 0.0,
            "token_utilization": 0.0,
            "cache_hit_ratio": 0.0,
            "batch_efficiency": 0.0,
            "realtime_latency": 0.0
        }

    async def generate_tailored_resume(
        self,
        resume_content: str,
        job_description: str,
        resume_skills: List[str],
        iterations: int = 2,
        past_performance: Optional[PerformanceMetrics] = None,
        max_cost: Optional[float] = None,
        priority: bool = False
    ) -> Dict[str, str]:
        """Generate a tailored resume using multiple models iteratively."""
        start_time = datetime.now()
        total_cost = 0.0

        # Try to use cached industry classification first
        industry_prompt = "What industry is this job description for?\n" + job_description
        industry = await self._get_cached_or_generate(
            "o1-mini",
            industry_prompt,
            system_message="You are an expert at identifying industries from job descriptions."
        )

        # Preprocess job description and match persona
        job_description_set = set(job_description.lower().split())
        selected_persona = self._match_persona(job_description_set, resume_skills)

        # Determine sections to tailor
        sections_to_tailor = await self._determine_sections(job_description, resume_content)
        tailored_resume = {}

        # Analyze skills with temporal aspects
        for skill in resume_skills:
            self.skill_analyzer.update_skill_metrics(skill, resume_content)

        # Process sections with automated model selection and cost optimization
        batch_items = []
        for section, content in sections_to_tailor.items():
            # Select model based on requirements and cost constraints
            priority_level = TaskPriority.HIGH if priority else TaskPriority.MEDIUM
            model = await self.model_selector.select_model(
                task_type="section_tailoring",
                content_length=len(content),
                required_accuracy=self.performance_threshold,
                priority=priority_level,
                fallback_allowed=True
            )

            # Check cost constraints separately
            if max_cost is not None:
                estimated_cost = self._estimate_request_cost(model, len(content))
                if estimated_cost > max_cost:
                    logger.warning(
                        f"Selected model {model} exceeds cost limit. "
                        f"Estimated cost: {estimated_cost}, Limit: {max_cost}"
                    )
                    continue

            # Generate optimized prompt
            prompt = await self._generate_optimized_prompt(
                section,
                content,
                job_description,
                selected_persona,
                model
            )

            batch_items.append({
                "id": section,
                "model": model,
                "prompt": prompt,
                "priority": priority
            })

        # Process batches with monitoring
        batch_results = await self.batch_processor.process_batch(
            batch_items,
            priority=priority
        )
        for result in batch_results:
            if result["success"]:
                section_id = result["id"]
                tailored_content = result["response"]

                # Verify industry terminology
                term_accuracy, used_terms = self.skill_analyzer.verify_industry_terminology(
                    tailored_content,
                    {term.lower() for term in industry.split()}
                )

                # Retain original formatting
                formatted_content = self.format_handler.retain_format(
                    sections_to_tailor[section_id],
                    tailored_content
                )

                tailored_resume[section_id] = formatted_content

                # Collect training data with proper type casting
                await self.training_collector.collect_interaction(
                    prompt=str(batch_items[0]["prompt"]),
                    response=str(tailored_content),
                    model=str(batch_items[0]["model"]),
                    metadata={
                        "section": str(section_id),
                        "term_accuracy": float(term_accuracy),
                        "used_terms": list(used_terms)
                    }
                )

        # Update optimization metrics with enhanced monitoring
        processing_time = (datetime.now() - start_time).total_seconds()
        total_tokens = sum(
            result.get("tokens_used", 0)
            for result in batch_results
            if result.get("success", False)
        )
        cache_hits = sum(1 for result in batch_results if result.get("cached", False))

        self._update_optimization_metrics(
            float(total_cost),
            float(processing_time),
            len(batch_results),
            total_tokens=total_tokens,
            cache_hits=cache_hits,
            batch_size=len(batch_items)
        )

        # Apply cost optimization if target is set
        if (
            self.cost_optimization_target
            and total_cost > self.cost_optimization_target
        ):
            await self._optimize_cost_usage(batch_results)

        return tailored_resume

    def _match_persona(self, job_description_set: set[str], resume_skills: List[str]) -> str:
        """Match the most appropriate persona based on job and skills."""
        resume_skills_set = set(skill.lower() for skill in resume_skills)

        # Precompute overlap scores
        for persona, cached_data in PERSONAS_CACHED.items():
            role_overlap = len(
                cached_data["target_roles_set"].intersection(job_description_set)
            )
            skill_overlap = len(
                cached_data["focus_set"].intersection(resume_skills_set)
            )
            cached_data["precomputed_overlap"] = role_overlap + skill_overlap

        # Select best matching persona
        best_match = max(
            PERSONAS_CACHED.items(),
            key=lambda item: item[1]["precomputed_overlap"]
        )[0]

        return str(best_match)

    async def _determine_sections(
        self,
        job_description: str,
        resume_content: str
    ) -> Dict[str, str]:
        """Determine which sections need tailoring."""
        # First try to identify sections using common headers
        sections: Dict[str, str] = {}
        current_section: Optional[str] = None
        current_content: List[str] = []

        # Common section headers and their variations
        section_headers = {
            "summary": [
                "career objective", "CAREER OBJECTIVE", "Career Objective",
                "professional summary", "PROFESSIONAL SUMMARY",
                "summary", "SUMMARY", "objective", "OBJECTIVE",
                "profile", "PROFILE"
            ],
            "experience": [
                "work experience", "WORK EXPERIENCE", "Work Experience",
                "experience", "EXPERIENCE", "Experience",
                "employment history", "EMPLOYMENT HISTORY",
                "work history", "WORK HISTORY",
                "career history", "CAREER HISTORY"
            ],
            "skills": [
                "skills", "SKILLS", "Skills",
                "technical skills", "TECHNICAL SKILLS", "Technical Skills",
                "core competencies", "CORE COMPETENCIES",
                "key skills", "KEY SKILLS",
                "expertise", "EXPERTISE"
            ],
            "education": [
                "education", "EDUCATION", "Education",
                "academic background", "ACADEMIC BACKGROUND",
                "academic history", "ACADEMIC HISTORY",
                "qualifications", "QUALIFICATIONS"
            ]
        }

        # Process resume content line by line
        lines = resume_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue

            logger.debug(f"Processing line: {line}")

            # Check if line is a section header (case-insensitive)
            line_lower = line.lower()
            line_upper = line.upper()
            found_header = False

            # Special case for CAREER OBJECTIVE -> summary mapping
            if line == "CAREER OBJECTIVE":
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                    logger.debug(f"Saved section {current_section}: {sections[current_section]}")
                current_section = "summary"
                current_content = []
                found_header = True
                logger.debug("Found CAREER OBJECTIVE header, switching to summary section")
                logger.debug(f"Current sections: {list(sections.keys())}")
                continue

            # Check other section headers
            if not found_header:
                for section, headers in section_headers.items():
                    # Convert all headers to lowercase and uppercase for matching
                    headers_lower = [h.lower() for h in headers]
                    headers_upper = [h.upper() for h in headers]

                    # Check exact matches first
                    if (line in headers
                            or line_lower in headers_lower
                            or line_upper in headers_upper):
                        if current_section and current_content:
                            sections[current_section] = '\n'.join(current_content).strip()
                            logger.debug(f"Saved section {current_section}: {sections[current_section]}")
                        current_section = section
                        current_content = []
                        found_header = True
                        logger.debug(f"Found {section} header")
                        break

                    # Then check partial matches (both lower and upper case)
                    if any(header in line_lower for header in headers_lower) or \
                       any(header in line_upper for header in headers_upper):
                        if current_section and current_content:
                            sections[current_section] = '\n'.join(current_content).strip()
                            logger.debug(f"Saved section {current_section}: {sections[current_section]}")
                        current_section = section
                        current_content = []
                        found_header = True
                        logger.debug(f"Found {section} header (partial match)")
                        break

            # If not a header and we have a current section, append the line
            if not found_header and current_section is not None:
                current_content.append(line)
                logger.debug(f"Added line to {current_section} section: {line}")

        # Add the last section
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()
            logger.debug(f"Saved final section {current_section}: {sections[current_section]}")

        logger.debug(f"Found sections: {list(sections.keys())}")
        logger.debug(f"Summary section content: {sections.get('summary', 'Not found')}")

        # If no sections found using headers, fall back to AI-based parsing
        if not sections:
            logger.debug("No sections found using headers, falling back to AI parsing")
            cached_response = self.prompt_cache.get_cached_response("gpt-4", resume_content)
            if cached_response:
                return self._parse_sections_response(str(cached_response))

            response = await self.api_client.make_api_call_async(
                "gpt-4",
                resume_content,
                system_message=(
                    "You are a JSON-only response bot. Always respond with valid JSON. "
                    "Format section names in lowercase and ensure all content is properly escaped."
                )
            )
            self.prompt_cache.cache_response("gpt-4", resume_content, str(response))
            return self._parse_sections_response(str(response))

        return sections

    def _parse_sections_response(self, response: str) -> Dict[str, str]:
        """Parse the sections response into a structured format."""
        try:
            import json
            # Clean the response string to handle potential leading/trailing text
            response = response.strip()
            # If response starts with a backtick block, extract just the JSON
            if response.startswith("```json"):
                response = response.split("```json")[1].split("```")[0].strip()
            elif response.startswith("```"):
                response = response.split("```")[1].split("```")[0].strip()

            sections = json.loads(response)
            if not isinstance(sections, dict):
                raise ValueError("Response is not a dictionary")
            return {str(k).lower(): str(v) for k, v in sections.items()}
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse sections response: {e}")
            # Return default sections if parsing fails
            return {
                "summary": "",
                "experience": "",
                "skills": "",
                "education": ""
            }

    def get_prompt(
        self,
        section: str,
        content: str,
        job_description: str,
        importance: Optional[int] = None,
        persona: str = "default"
    ) -> str:
        """Generate a tailored prompt for a section."""
        # Adjust template based on importance
        base_template = str(AVAILABLE_MODELS["gpt-4"]["prompt_template"])
        if importance:
            importance_context = (
                f"\nImportance Level: {importance}/5 - "
                f"Adjust content alignment with job requirements accordingly."
            )
            base_template = base_template + importance_context

        return base_template.format(
            section=section,
            content=content,
            job_description=job_description,
            persona=persona
        )

    async def _get_cached_or_generate(
        self,
        model: str,
        prompt: str,
        system_message: Optional[str] = None,
        max_age: Optional[timedelta] = None
    ) -> str:
        """Get cached response or generate new one with cost optimization."""
        cached = self.prompt_cache.get_cached_response(model, prompt, max_age)
        if cached:
            cost_savings = float(self._estimate_request_cost(model, len(prompt)))
            self.optimization_metrics["cost_savings"] = (
                float(self.optimization_metrics["cost_savings"]) + cost_savings
            )
            return str(cached)

        response = await self.api_client.make_api_call_async(
            model,
            prompt,
            system_message=system_message
        )
        self.prompt_cache.cache_response(model, prompt, str(response))
        return str(response)

    def _assess_section_importance(self, section: str) -> float:
        """Assess the importance of a resume section."""
        importance_weights = {
            "summary": 0.9,
            "experience": 1.0,
            "skills": 0.8,
            "education": 0.7,
            "projects": 0.8,
            "certifications": 0.7,
            "achievements": 0.9
        }
        return float(importance_weights.get(section.lower(), 0.5))

    async def _generate_optimized_prompt(
        self,
        section: str,
        content: str,
        job_description: str,
        persona: str,
        model: str
    ) -> str:
        """Generate an optimized prompt for the selected model."""
        # Get base prompt template
        template = str(AVAILABLE_MODELS[model]["prompt_template"])

        # Add context based on past successful prompts
        successful_prompts = self.prompt_cache.get_common_prompts(limit=5)
        context_patterns = [
            str(prompt["prompt"])
            for prompt in successful_prompts
            if int(prompt["count"]) > 5
        ]

        # Optimize prompt based on model capabilities
        if model == "gpt-4":
            # More detailed instructions for high-capability model
            return template.format(
                section=section,
                content=content,
                job_description=job_description,
                persona=persona,
                context="\n".join(context_patterns)
            )
        else:
            # Simpler prompt for basic models
            return template.format(
                section=section,
                content=content,
                job_description=job_description,
                persona=persona
            )

    def _estimate_request_cost(self, model: str, content_length: int) -> float:
        """Estimate the cost of a request based on content length."""
        if model not in AVAILABLE_MODELS:
            return float('inf')

        cost_per_token = float(AVAILABLE_MODELS[model].get("cost_per_token", 0.0))
        estimated_tokens = float(content_length) / 4.0  # Rough estimate
        return cost_per_token * estimated_tokens

    def _update_optimization_metrics(
        self,
        cost: float,
        processing_time: float,
        requests_processed: int,
        total_tokens: int = 0,
        cache_hits: int = 0,
        batch_size: int = 0
    ) -> None:
        """Update optimization and performance metrics."""
        self.optimization_metrics["total_cost"] = (
            float(self.optimization_metrics["total_cost"]) + float(cost)
        )

        # Calculate enhanced performance metrics
        if requests_processed > 0:
            avg_time_per_request = float(processing_time) / float(requests_processed)

            if "performance_scores" not in self.optimization_metrics:
                self.optimization_metrics["performance_scores"] = {}

            timestamp = datetime.now().isoformat()

            # Calculate advanced metrics
            # Assuming 1000 tokens per request is optimal
            token_utilization = float(total_tokens) / (requests_processed * 1000)
            cache_hit_ratio = (
                float(cache_hits) / requests_processed if requests_processed > 0 else 0
            )
            batch_efficiency = float(requests_processed) / batch_size if batch_size > 0 else 1.0
            cost_per_token = float(cost) / total_tokens if total_tokens > 0 else 0

            self.optimization_metrics["performance_scores"][timestamp] = {
                "avg_time_per_request": float(avg_time_per_request),
                "cost_per_request": float(cost) / float(requests_processed),
                "requests_processed": int(requests_processed),
                "token_utilization": token_utilization,
                "cache_hit_ratio": cache_hit_ratio,
                "batch_efficiency": batch_efficiency,
                "cost_per_token": cost_per_token
            }

            # Update rolling metrics
            self.optimization_metrics["token_utilization"] = token_utilization
            self.optimization_metrics["cache_hit_ratio"] = cache_hit_ratio
            self.optimization_metrics["batch_efficiency"] = batch_efficiency
            # Assuming $0.0004 per token is baseline
            self.optimization_metrics["cost_efficiency"] = 1.0 - (cost_per_token / 0.0004)

    async def _optimize_cost_usage(self, batch_results: List[Dict[str, Any]]) -> None:
        """Optimize cost usage based on batch results."""
        # Analyze expensive operations
        expensive_models: Dict[str, float] = {}
        for result in batch_results:
            if result.get("success", False):
                model = result.get("model", "")
                cost = result.get("cost", 0.0)
                if model:
                    expensive_models[model] = expensive_models.get(model, 0.0) + cost

        # Update model selector with cost insights
        for model, total_cost in expensive_models.items():
            self.model_selector.update_performance(
                model,
                "cost_optimization",
                1.0 - (
                    float(total_cost)
                    / float(
                        self.cost_optimization_target
                        if self.cost_optimization_target is not None
                        else 1.0
                    )
                )
            )

        # Adjust batch processing parameters if needed
        if self.optimization_metrics["batch_efficiency"] < 0.7:
            self.batch_processor.max_batch_size = max(
                10,
                int(self.batch_processor.max_batch_size * 0.8)
            )

    def list_available_models(self) -> List[Dict[str, str]]:
        """List all available models with their descriptions."""
        return [
            {
                "name": model_name,
                "description": AVAILABLE_MODELS[model_name].get(
                    "description",
                    "No description available"
                )
            }
            for model_name in AVAILABLE_MODELS.keys()
        ]

    async def get_completion(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None
    ) -> str:
        """Get completion from the specified model."""
        try:
            response = await self.api_client.make_api_call_async(
                model,
                prompt,
                temperature=temperature
            )
            return str(response)
        except Exception as e:
            logger.error(f"Error getting completion: {str(e)}")
            return ""

    def validate_output(
        self,
        original_text: str,
        generated_text: str,
        job_description: str,
        section: str
    ) -> tuple[bool, List[str], Dict[str, float]]:
        """Validate the generated output for a section."""
        issues = []
        metrics = {}

        # Check length ratio
        original_length = len(original_text.split())
        generated_length = len(generated_text.split())
        length_ratio = generated_length / original_length if original_length > 0 else 0
        metrics["length_ratio"] = length_ratio
        if length_ratio < 0.5 or length_ratio > 2.0:
            issues.append("Generated text length significantly differs from original")

        # Check keyword retention
        original_keywords = set(word.lower() for word in original_text.split())
        generated_keywords = set(word.lower() for word in generated_text.split())
        keyword_retention = (
            len(original_keywords.intersection(generated_keywords))
            / len(original_keywords)
        )
        metrics["keyword_retention"] = keyword_retention
        if keyword_retention < 0.7:
            issues.append("Important keywords from original text are missing")

        # Check job description alignment
        job_keywords = set(word.lower() for word in job_description.split())
        job_alignment = len(job_keywords.intersection(generated_keywords)) / len(job_keywords)
        metrics["job_alignment"] = job_alignment
        if job_alignment < 0.3:
            issues.append("Low alignment with job description keywords")

        # Section-specific checks
        if section.lower() == "experience":
            metrics["metrics_mentioned"] = self._count_metrics_mentions(generated_text)
            if metrics["metrics_mentioned"] < 3:
                issues.append("Experience section should include more quantifiable achievements")

        return len(issues) == 0, issues, metrics

    def _count_metrics_mentions(self, text: str) -> int:
        """Count mentions of metrics and numbers in text."""
        import re
        # Look for percentages, numbers with units, or standalone numbers
        patterns = [
            r'\d+%',  # Percentages
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',  # Currency
            r'\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:million|billion|k|M|B))?',  # Numbers with units
        ]
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, text))
        return count

    async def collect_training_data(
        self,
        resume_text: str,
        job_description: str,
        generated_text: str,
        section: str,
        metrics: Dict[str, float]
    ) -> None:
        """Collect training data for model improvement."""
        try:
            await self.training_collector.collect_interaction(
                prompt=str(resume_text),
                response=str(generated_text),
                model="gpt-4",  # Default to gpt-4 for training data
                metadata={
                    "section": str(section),
                    "job_description": str(job_description),
                    "metrics": metrics
                }
            )
        except Exception as e:
            logger.error(f"Error collecting training data: {str(e)}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics about system performance."""
        return {
            "api": self.api_client.get_metrics(),
            "models": self.model_selector.get_model_stats(),
            "cache": self.prompt_cache.get_cache_stats(),
            "training": self.training_collector.get_training_stats(),
            "optimization": dict(self.optimization_metrics),
            "token_bucket": self.token_bucket.get_metrics()
        }
