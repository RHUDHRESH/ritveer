"""
Intake Agent
Onboards new artisans, validates profiles, assesses skills
First point of contact for artisans joining the platform
"""

from typing import Dict, Any, List
from datetime import datetime
from .base_agent import BaseAgent, AgentState, AgentRole
from ..tools import (
    web_scraper,
    market_research,
    competitor_analysis,
    trend_detection,
)
import uuid


class IntakeAgent(BaseAgent):
    """
    Intake Agent - Onboards artisans
    - Validates profile information
    - Assesses craft skills
    - Determines specialization
    - Sets up initial business profile
    """

    def __init__(self):
        super().__init__(
            role=AgentRole.INTAKE,
            name="IntakeAgent",
            description="Onboards artisans, validates profiles, assesses skills"
        )
        # Register tools
        self.register_tool("market_research")
        self.register_tool("competitor_analysis")
        self.register_tool("trend_detection")
        self.register_tool("web_scraper")

    async def think(self, state: AgentState) -> Dict[str, Any]:
        """
        Analyze artisan profile and determine:
        - Craft authenticity
        - Skill level
        - Market potential
        - Business readiness
        """
        artisan_data = state.context.get("artisan_data", {})

        # Assessment criteria
        assessment = {
            "artisan_name": artisan_data.get("name", ""),
            "craft_type": artisan_data.get("craft_type", ""),
            "location": artisan_data.get("location", ""),
            "experience_years": artisan_data.get("experience_years", 0),
        }

        # Determine skill level based on experience
        years = assessment["experience_years"]
        if years < 2:
            skill_level = "beginner"
        elif years < 5:
            skill_level = "intermediate"
        elif years < 10:
            skill_level = "advanced"
        else:
            skill_level = "expert"

        assessment["skill_level"] = skill_level

        # Determine business readiness
        has_portfolio = artisan_data.get("has_portfolio", False)
        has_website = artisan_data.get("has_website", False)
        has_social = artisan_data.get("has_social_media", False)

        business_readiness_score = sum([has_portfolio, has_website, has_social]) / 3
        assessment["business_readiness_score"] = business_readiness_score

        # Store thinking process
        self.remember(f"artisan_{state.artisan_id}_assessment", assessment)

        return {
            "action": "analyze_profile",
            "assessment": assessment,
            "decision": "proceed_to_market_analysis"
        }

    async def act(self, state: AgentState, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute actions to onboard artisan:
        1. Research market for their craft
        2. Analyze competitors
        3. Detect trends
        4. Create initial business profile
        """
        artisan_data = state.context.get("artisan_data", {})
        craft_type = artisan_data.get("craft_type")
        location = artisan_data.get("location")

        results = {}

        # Action 1: Research market for their craft
        market_data = await market_research.execute(
            craft_type=craft_type,
            location=location
        )
        results["market_research"] = market_data.to_dict() if market_data.success else None

        # Action 2: Analyze competitors
        competitor_data = await competitor_analysis.execute(
            craft_type=craft_type,
            location=location
        )
        results["competitor_analysis"] = competitor_data.to_dict() if competitor_data.success else None

        # Action 3: Detect trends
        trend_data = await trend_detection.execute(
            craft_type=craft_type
        )
        results["trends"] = trend_data.to_dict() if trend_data.success else None

        # Action 4: Create business profile
        artisan_id = state.artisan_id
        business_profile = {
            "artisan_id": artisan_id,
            "craft_type": craft_type,
            "location": location,
            "skill_level": self.recall(f"artisan_{artisan_id}_assessment").get("skill_level"),
            "market_opportunity": "high" if market_data.success else "unknown",
            "competitive_position": "research_completed",
            "profile_created_at": datetime.utcnow().isoformat(),
            "status": "onboarding_complete"
        }
        results["business_profile"] = business_profile

        return {
            "action": "onboard_artisan",
            "artisan_id": artisan_id,
            "results": results,
            "profile": business_profile
        }

    async def observe(self, state: AgentState, result: Dict[str, Any]) -> None:
        """
        Observe outcomes:
        - Store profile information
        - Update knowledge base
        - Prepare handoff to next agent
        """
        artisan_id = result.get("artisan_id")
        profile = result.get("profile", {})

        # Store profile in memory
        self.remember(f"artisan_{artisan_id}_profile", profile)

        # Store market research in memory for future reference
        results = result.get("results", {})
        if results.get("market_research"):
            self.remember(f"artisan_{artisan_id}_market", results["market_research"])

        if results.get("competitor_analysis"):
            self.remember(f"artisan_{artisan_id}_competitors", results["competitor_analysis"])

        # Prepare context for next agent (SupplierAgent)
        state.context["onboarding_complete"] = True
        state.context["artisan_profile"] = profile
        state.context["market_analysis"] = results.get("market_research")

    async def validate_artisan(self, artisan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate artisan profile completeness
        Returns validation result
        """
        required_fields = ["name", "craft_type", "location", "experience_years"]
        missing_fields = [f for f in required_fields if f not in artisan_data]

        validation = {
            "is_valid": len(missing_fields) == 0,
            "missing_fields": missing_fields,
            "artisan_data": artisan_data,
        }

        return validation
