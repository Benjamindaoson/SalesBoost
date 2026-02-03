"""
Competitor Analysis Tool

Provides competitive intelligence and market analysis.
Simulates integration with market research databases and competitive intelligence platforms.
"""
from typing import Dict, Any, Optional, List
from pydantic import Field
from enum import Enum

from app.tools.base import BaseTool, ToolInputModel
from app.infra.gateway.schemas import AgentType


class CompetitorCategory(str, Enum):
    """Competitor categories"""
    DIRECT = "direct"
    INDIRECT = "indirect"
    POTENTIAL = "potential"


class CompetitorAnalysisInput(ToolInputModel):
    """Competitor analysis input"""
    competitor_name: Optional[str] = Field(None, description="Specific competitor name to analyze")
    category: Optional[str] = Field(None, description="Competitor category: direct, indirect, potential")
    aspect: Optional[str] = Field(None, description="Analysis aspect: pricing, features, market_share, strengths, weaknesses")


class CompetitorAnalysisTool(BaseTool):
    """
    Competitor Analysis Tool

    Provides competitive intelligence including:
    - Competitor profiles
    - Pricing comparison
    - Feature comparison
    - Market share analysis
    - Strengths and weaknesses

    Allowed agents: Coach, System
    """

    name = "competitor_analysis"
    description = "Analyze competitors including pricing, features, market position, strengths and weaknesses. Essential for competitive positioning."
    args_schema = CompetitorAnalysisInput
    allowed_agents = {
        AgentType.COACH.value,
        "system"
    }

    def __init__(self):
        super().__init__()
        # Simulated competitor database
        self._competitors: Dict[str, Dict[str, Any]] = {
            "CompetitorA": {
                "name": "CompetitorA",
                "category": "direct",
                "market_share": 35.2,
                "founded": 2015,
                "employees": 500,
                "pricing": {
                    "basic": 49,
                    "professional": 99,
                    "enterprise": 299
                },
                "features": [
                    "CRM Integration",
                    "Email Automation",
                    "Analytics Dashboard",
                    "Mobile App",
                    "API Access"
                ],
                "strengths": [
                    "Strong brand recognition",
                    "Extensive integration ecosystem",
                    "24/7 customer support",
                    "User-friendly interface"
                ],
                "weaknesses": [
                    "Higher pricing than competitors",
                    "Limited customization options",
                    "Slow feature rollout",
                    "Complex onboarding process"
                ],
                "target_market": "Enterprise and mid-market companies",
                "recent_news": [
                    "Raised $50M Series C funding",
                    "Launched AI-powered analytics",
                    "Expanded to European market"
                ]
            },
            "CompetitorB": {
                "name": "CompetitorB",
                "category": "direct",
                "market_share": 28.5,
                "founded": 2018,
                "employees": 300,
                "pricing": {
                    "starter": 29,
                    "growth": 79,
                    "enterprise": 199
                },
                "features": [
                    "Sales Automation",
                    "Lead Scoring",
                    "Email Tracking",
                    "Reporting",
                    "Team Collaboration"
                ],
                "strengths": [
                    "Competitive pricing",
                    "Fast implementation",
                    "Modern UI/UX",
                    "Strong mobile experience"
                ],
                "weaknesses": [
                    "Limited enterprise features",
                    "Smaller integration library",
                    "Less established brand",
                    "Support only during business hours"
                ],
                "target_market": "SMBs and startups",
                "recent_news": [
                    "Acquired by larger tech company",
                    "Released new mobile app",
                    "Reached 10,000 customers"
                ]
            },
            "CompetitorC": {
                "name": "CompetitorC",
                "category": "indirect",
                "market_share": 15.8,
                "founded": 2020,
                "employees": 150,
                "pricing": {
                    "free": 0,
                    "pro": 59,
                    "business": 149
                },
                "features": [
                    "Contact Management",
                    "Email Templates",
                    "Basic Analytics",
                    "Calendar Integration"
                ],
                "strengths": [
                    "Free tier available",
                    "Simple and intuitive",
                    "Quick setup",
                    "Good for small teams"
                ],
                "weaknesses": [
                    "Limited advanced features",
                    "No API access on lower tiers",
                    "Basic reporting",
                    "Scalability concerns"
                ],
                "target_market": "Freelancers and small businesses",
                "recent_news": [
                    "Launched freemium model",
                    "Reached profitability",
                    "Expanded team by 50%"
                ]
            }
        }

    async def _run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze competitors

        Args:
            payload: {
                "competitor_name": "CompetitorA",  # optional
                "category": "direct",              # optional
                "aspect": "pricing"                # optional
            }

        Returns:
            Competitor analysis data
        """
        competitor_name = payload.get("competitor_name")
        category = payload.get("category")
        aspect = payload.get("aspect")

        # Specific competitor analysis
        if competitor_name:
            return await self._analyze_competitor(competitor_name, aspect)

        # Category-based analysis
        if category:
            return await self._analyze_by_category(category, aspect)

        # General market overview
        return await self._market_overview()

    async def _analyze_competitor(self, competitor_name: str, aspect: Optional[str]) -> Dict[str, Any]:
        """Analyze specific competitor"""
        competitor = self._competitors.get(competitor_name)

        if not competitor:
            return {
                "success": False,
                "error": f"Competitor '{competitor_name}' not found",
                "available_competitors": list(self._competitors.keys())
            }

        # Full profile if no specific aspect
        if not aspect:
            return {
                "success": True,
                "competitor": competitor
            }

        # Specific aspect analysis
        if aspect == "pricing":
            return {
                "success": True,
                "competitor": competitor_name,
                "aspect": "pricing",
                "data": competitor["pricing"],
                "comparison": self._compare_pricing(competitor_name)
            }
        elif aspect == "features":
            return {
                "success": True,
                "competitor": competitor_name,
                "aspect": "features",
                "data": competitor["features"],
                "feature_count": len(competitor["features"])
            }
        elif aspect == "market_share":
            return {
                "success": True,
                "competitor": competitor_name,
                "aspect": "market_share",
                "data": competitor["market_share"],
                "rank": self._get_market_rank(competitor_name)
            }
        elif aspect == "strengths":
            return {
                "success": True,
                "competitor": competitor_name,
                "aspect": "strengths",
                "data": competitor["strengths"]
            }
        elif aspect == "weaknesses":
            return {
                "success": True,
                "competitor": competitor_name,
                "aspect": "weaknesses",
                "data": competitor["weaknesses"],
                "opportunities": self._identify_opportunities(competitor["weaknesses"])
            }
        else:
            return {
                "success": False,
                "error": f"Unknown aspect: {aspect}",
                "valid_aspects": ["pricing", "features", "market_share", "strengths", "weaknesses"]
            }

    async def _analyze_by_category(self, category: str, aspect: Optional[str]) -> Dict[str, Any]:
        """Analyze competitors by category"""
        competitors = {
            name: data for name, data in self._competitors.items()
            if data["category"] == category
        }

        if not competitors:
            return {
                "success": False,
                "error": f"No competitors found in category: {category}",
                "valid_categories": ["direct", "indirect", "potential"]
            }

        return {
            "success": True,
            "category": category,
            "count": len(competitors),
            "competitors": list(competitors.keys()),
            "total_market_share": sum(c["market_share"] for c in competitors.values()),
            "data": competitors if not aspect else {
                name: data.get(aspect, {}) for name, data in competitors.items()
            }
        }

    async def _market_overview(self) -> Dict[str, Any]:
        """Get market overview"""
        total_competitors = len(self._competitors)
        total_market_share = sum(c["market_share"] for c in self._competitors.values())

        # Category breakdown
        categories = {}
        for competitor in self._competitors.values():
            cat = competitor["category"]
            categories[cat] = categories.get(cat, 0) + 1

        # Market leader
        leader = max(self._competitors.items(), key=lambda x: x[1]["market_share"])

        return {
            "success": True,
            "total_competitors": total_competitors,
            "total_market_share_tracked": total_market_share,
            "market_leader": {
                "name": leader[0],
                "market_share": leader[1]["market_share"]
            },
            "category_breakdown": categories,
            "competitors": list(self._competitors.keys())
        }

    def _compare_pricing(self, competitor_name: str) -> Dict[str, Any]:
        """Compare pricing across competitors"""
        target = self._competitors[competitor_name]["pricing"]
        comparisons = {}

        for name, data in self._competitors.items():
            if name != competitor_name:
                pricing = data["pricing"]
                # Compare similar tiers
                comparison = {}
                for tier in target.keys():
                    if tier in pricing:
                        diff = pricing[tier] - target[tier]
                        comparison[tier] = {
                            "competitor_price": target[tier],
                            "other_price": pricing[tier],
                            "difference": diff,
                            "percentage": round((diff / target[tier]) * 100, 1) if target[tier] > 0 else 0
                        }
                comparisons[name] = comparison

        return comparisons

    def _get_market_rank(self, competitor_name: str) -> int:
        """Get market rank by market share"""
        sorted_competitors = sorted(
            self._competitors.items(),
            key=lambda x: x[1]["market_share"],
            reverse=True
        )
        for rank, (name, _) in enumerate(sorted_competitors, 1):
            if name == competitor_name:
                return rank
        return -1

    def _identify_opportunities(self, weaknesses: List[str]) -> List[str]:
        """Identify opportunities based on competitor weaknesses"""
        opportunity_map = {
            "Higher pricing": "Offer competitive pricing strategy",
            "Limited customization": "Emphasize our customization capabilities",
            "Slow feature rollout": "Highlight our rapid innovation",
            "Complex onboarding": "Showcase our simple onboarding process",
            "Limited enterprise features": "Target enterprise customers",
            "Smaller integration library": "Promote our extensive integrations",
            "Support only during business hours": "Emphasize 24/7 support",
            "Limited advanced features": "Highlight advanced feature set",
            "Basic reporting": "Showcase advanced analytics",
            "Scalability concerns": "Emphasize enterprise scalability"
        }

        opportunities = []
        for weakness in weaknesses:
            for key, opportunity in opportunity_map.items():
                if key.lower() in weakness.lower():
                    opportunities.append(opportunity)
                    break

        return opportunities if opportunities else ["Conduct deeper competitive analysis"]
