"""Salary analysis and market rate estimation."""

import re
from typing import Dict, List, Optional, Tuple, Union


class SalaryAnalyzer:
    """Analyzes salary information and provides market rate estimates."""

    def __init__(self) -> None:
        """Initialize salary analyzer."""
        # Base salary ranges by experience level (in AUD)
        self.base_ranges = {
            "entry": (60000, 85000),
            "mid": (85000, 120000),
            "senior": (120000, 180000),
            "lead": (150000, 220000),
            "architect": (180000, 250000)
        }

        # Skill premium multipliers
        self.skill_premiums = {
            "ai": 1.2,
            "cloud": 1.15,
            "security": 1.15,
            "blockchain": 1.2,
            "data_science": 1.15,
            "devops": 1.1,
            "mobile": 1.1,
            "frontend": 1.05,
            "backend": 1.05,
            "fullstack": 1.1
        }

        # Industry multipliers
        self.industry_multipliers = {
            "finance": 1.2,
            "healthcare": 1.1,
            "technology": 1.15,
            "retail": 1.0,
            "manufacturing": 1.05,
            "energy": 1.1,
            "consulting": 1.15,
            "government": 0.95
        }

        # Location adjustments (relative to Melbourne)
        self.location_adjustments = {
            "sydney": 1.1,
            "melbourne": 1.0,
            "brisbane": 0.95,
            "perth": 0.95,
            "adelaide": 0.9,
            "canberra": 1.05,
            "remote": 0.95
        }

    def analyze_market_rate(
        self,
        years_experience: int,
        skills: List[str],
        industry: str,
        location: str = "melbourne",
        current_salary: Optional[float] = None
    ) -> Tuple[float, float, Dict[str, Union[float, Tuple[float, float]]]]:
        """Calculate estimated market rate salary range.

        Args:
            years_experience: Years of relevant experience
            skills: List of key skills
            industry: Industry sector
            location: Job location (default: melbourne)
            current_salary: Current salary if available

        Returns:
            Tuple containing:
            - Minimum market rate
            - Maximum market rate
            - Dictionary of adjustment factors
        """
        # Determine experience level
        level = self._determine_level(years_experience)
        base_min, base_max = self.base_ranges[level]

        # Calculate skill premium
        skill_multiplier = self._calculate_skill_premium(skills)

        # Get industry multiplier
        industry_multiplier = self.industry_multipliers.get(
            industry.lower(), 1.0
        )

        # Get location adjustment
        location_multiplier = self.location_adjustments.get(
            location.lower(), 1.0
        )

        # Calculate adjusted range
        min_rate = (
            base_min *
            skill_multiplier *
            industry_multiplier *
            location_multiplier
        )
        max_rate = (
            base_max *
            skill_multiplier *
            industry_multiplier *
            location_multiplier
        )

        # Record adjustment factors
        factors: Dict[str, Union[float, Tuple[float, float]]] = {
            "base_range": (base_min, base_max),
            "skill_multiplier": skill_multiplier,
            "industry_multiplier": industry_multiplier,
            "location_multiplier": location_multiplier
        }

        return min_rate, max_rate, factors

    def extract_salary_info(self, text: str) -> Optional[Tuple[float, float]]:
        """Extract salary range from job description text.

        Args:
            text: Job description text

        Returns:
            Tuple of (min_salary, max_salary) if found, None otherwise
        """
        # Common salary patterns
        patterns = [
            # Range with K notation
            r"\$?\s*(\d{2,3})[Kk]\s*(?:-|to)\s*\$?\s*(\d{2,3})[Kk]",
            # Range with full numbers
            r"\$?\s*(\d{4,6})\s*(?:-|to)\s*\$?\s*(\d{4,6})",
            # Single value with K
            r"\$?\s*(\d{2,3})[Kk]",
            # Package notation
            r"(?:package|pkg).*?\$?\s*(\d{2,3})[Kk]",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:
                    min_val = float(match.group(1))
                    max_val = float(match.group(2))
                    # Convert K notation to full numbers
                    if 'k' in pattern.lower():
                        min_val *= 1000
                        max_val *= 1000
                    return min_val, max_val
                else:
                    val = float(match.group(1))
                    if 'k' in pattern.lower():
                        val *= 1000
                    # Create a range around the single value
                    return val * 0.9, val * 1.1
        return None

    def get_salary_insights(
        self,
        market_min: float,
        market_max: float,
        current_salary: Optional[float] = None,
        offered_salary: Optional[float] = None
    ) -> List[str]:
        """Generate salary insights and negotiation tips.

        Args:
            market_min: Minimum market rate
            market_max: Maximum market rate
            current_salary: Current salary if available
            offered_salary: Offered salary if available

        Returns:
            List of insights and recommendations
        """
        insights: List[str] = []

        # Add market position insight
        insights.append(
            f"Market range for this role: ${market_min:,.0f} - ${market_max:,.0f}"
        )

        if current_salary:
            if current_salary < market_min:
                insights.append(
                    "You are currently below market rate. "
                    "Consider negotiating for a significant increase."
                )
            elif current_salary > market_max:
                insights.append(
                    "You are currently above market rate. "
                    "Focus on value proposition in negotiations."
                )
            else:
                position = (current_salary - market_min) / (market_max - market_min)
                if position < 0.4:
                    insights.append(
                        "You are in the lower market range. "
                        "Room for upward negotiation."
                    )
                elif position > 0.6:
                    insights.append(
                        "You are in the upper market range. "
                        "Strong position for negotiations."
                    )

        if offered_salary:
            if offered_salary < market_min:
                insights.append(
                    "Offered salary is below market rate. "
                    "Consider negotiating up with market data."
                )
            elif offered_salary > market_max:
                insights.append(
                    "Offered salary is above market rate. "
                    "Strong offer relative to market."
                )
            else:
                position = (offered_salary - market_min) / (market_max - market_min)
                insights.append(
                    f"Offer is at {position:.0%} of market range. "
                    f"{'Consider negotiating up.' if position < 0.5 else 'Competitive offer.'}"
                )

        # Add general negotiation tips
        insights.append(
            "💡 Tip: Focus on total package including super, bonuses, and benefits"
        )
        insights.append(
            "💡 Tip: Use market data and your experience to support negotiations"
        )

        return insights

    def _determine_level(self, years_experience: int) -> str:
        """Determine experience level based on years."""
        if years_experience < 3:
            return "entry"
        elif years_experience < 5:
            return "mid"
        elif years_experience < 8:
            return "senior"
        elif years_experience < 12:
            return "lead"
        else:
            return "architect"

    def _calculate_skill_premium(self, skills: List[str]) -> float:
        """Calculate skill-based salary premium."""
        # Get premium multipliers for matching skills
        premiums = [
            self.skill_premiums.get(skill.lower(), 1.0)
            for skill in skills
        ]

        if not premiums:
            return 1.0

        # Use diminishing returns for multiple premium skills
        # Take the highest premium and add 20% of additional premiums
        base_premium = max(premiums) - 1.0  # Convert to premium above 1.0
        additional_premiums = sorted(premiums, reverse=True)[1:]
        extra_premium = sum(
            (p - 1.0) * 0.2  # Take 20% of each additional premium
            for p in additional_premiums
        )

        return 1.0 + base_premium + extra_premium
