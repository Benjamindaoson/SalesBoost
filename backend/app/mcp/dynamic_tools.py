"""
Dynamic Tool Generator - 动态工具生成器

根据上下文动态生成定制化工具，而不是使用静态工具。

核心能力：
1. 从模板生成工具
2. 注入上下文数据
3. 动态编译和验证
4. 安全沙箱执行

Author: Claude (Anthropic)
Version: 2.0
"""

from __future__ import annotations

import ast
import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolTemplate:
    """工具模板"""
    template_id: str
    name: str
    description: str
    code_template: str  # Python code template with placeholders
    parameters_schema: Dict[str, Any]
    context_requirements: List[str]  # Required context fields
    estimated_cost: float = 0.0
    estimated_latency: float = 1.0


class DynamicToolGenerator:
    """
    动态工具生成器

    根据上下文动态生成定制化工具。

    Usage:
        generator = DynamicToolGenerator()

        # 注册模板
        generator.register_template(roi_calculator_template)

        # 生成工具
        tool = await generator.generate(
            template_id="roi_calculator",
            context={
                "industry": "SaaS",
                "customer_size": "500-1000",
                "benchmarks": {...}
            }
        )

        # 使用工具
        result = await tool.execute(
            current_spend=100000,
            expected_improvement=0.25
        )
    """

    def __init__(self):
        self.templates: Dict[str, ToolTemplate] = {}
        self.generated_tools: Dict[str, Any] = {}  # Cache
        self._register_default_templates()

    def _register_default_templates(self):
        """注册默认模板"""

        # ROI计算器模板
        roi_template = ToolTemplate(
            template_id="roi_calculator",
            name="ROI Calculator",
            description="Calculate ROI based on industry benchmarks",
            code_template="""
async def calculate_roi(current_spend: float, expected_improvement: float) -> dict:
    '''Calculate ROI with industry-specific benchmarks'''

    # Industry benchmarks (injected from context)
    industry = "{industry}"
    avg_roi = {avg_roi}
    implementation_cost = {implementation_cost}

    # Calculate
    annual_savings = current_spend * expected_improvement
    payback_period = implementation_cost / annual_savings
    three_year_roi = (annual_savings * 3 - implementation_cost) / implementation_cost

    return {{
        "industry": industry,
        "annual_savings": annual_savings,
        "payback_period_months": payback_period * 12,
        "three_year_roi_percent": three_year_roi * 100,
        "benchmark_comparison": "above" if three_year_roi > avg_roi else "below"
    }}
""",
            parameters_schema={
                "type": "object",
                "properties": {
                    "current_spend": {"type": "number"},
                    "expected_improvement": {"type": "number"},
                },
                "required": ["current_spend", "expected_improvement"],
            },
            context_requirements=["industry", "avg_roi", "implementation_cost"],
        )

        self.register_template(roi_template)

        # 客户研究工具模板
        research_template = ToolTemplate(
            template_id="customer_researcher",
            name="Customer Researcher",
            description="Research customer with customized data sources",
            code_template="""
async def research_customer(company_name: str) -> dict:
    '''Research customer using configured data sources'''

    results = {{}}

    # Data sources (injected from context)
    data_sources = {data_sources}

    for source in data_sources:
        if source == "linkedin":
            # LinkedIn research
            results["linkedin"] = await linkedin_search(company_name)
        elif source == "crm":
            # CRM lookup
            results["crm"] = await crm_lookup(company_name)
        elif source == "news":
            # News search
            results["news"] = await news_search(company_name)

    # Industry-specific insights
    industry = "{industry}"
    results["industry_insights"] = get_industry_insights(industry)

    return results
""",
            parameters_schema={
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                },
                "required": ["company_name"],
            },
            context_requirements=["data_sources", "industry"],
        )

        self.register_template(research_template)

        # 动态定价工具模板
        pricing_template = ToolTemplate(
            template_id="dynamic_pricer",
            name="Dynamic Pricer",
            description="Calculate pricing based on customer context",
            code_template="""
async def calculate_price(base_price: float, quantity: int) -> dict:
    '''Calculate price with dynamic discounts'''

    # Customer context (injected)
    customer_tier = "{customer_tier}"
    industry = "{industry}"
    relationship_score = {relationship_score}

    # Discount rules
    tier_discounts = {tier_discounts}
    volume_discounts = {volume_discounts}

    # Calculate discounts
    tier_discount = tier_discounts.get(customer_tier, 0)
    volume_discount = 0
    for threshold, discount in sorted(volume_discounts.items()):
        if quantity >= threshold:
            volume_discount = discount

    relationship_discount = min(relationship_score * 0.05, 0.15)  # Max 15%

    total_discount = min(tier_discount + volume_discount + relationship_discount, 0.40)  # Max 40%

    final_price = base_price * quantity * (1 - total_discount)

    return {{
        "base_price": base_price,
        "quantity": quantity,
        "tier_discount": tier_discount,
        "volume_discount": volume_discount,
        "relationship_discount": relationship_discount,
        "total_discount": total_discount,
        "final_price": final_price,
        "price_per_unit": final_price / quantity
    }}
""",
            parameters_schema={
                "type": "object",
                "properties": {
                    "base_price": {"type": "number"},
                    "quantity": {"type": "integer"},
                },
                "required": ["base_price", "quantity"],
            },
            context_requirements=[
                "customer_tier",
                "industry",
                "relationship_score",
                "tier_discounts",
                "volume_discounts",
            ],
        )

        self.register_template(pricing_template)

    def register_template(self, template: ToolTemplate):
        """注册工具模板"""
        self.templates[template.template_id] = template
        logger.info(f"Registered tool template: {template.template_id}")

    async def generate(
        self,
        template_id: str,
        context: Dict[str, Any],
        cache: bool = True,
    ) -> Any:
        """
        生成工具

        Args:
            template_id: Template ID
            context: Context data to inject
            cache: Whether to cache generated tool

        Returns:
            Generated tool instance
        """
        # Check cache
        cache_key = self._get_cache_key(template_id, context)
        if cache and cache_key in self.generated_tools:
            logger.info(f"Using cached tool: {template_id}")
            return self.generated_tools[cache_key]

        # Get template
        if template_id not in self.templates:
            raise ValueError(f"Template not found: {template_id}")

        template = self.templates[template_id]

        # Validate context
        self._validate_context(template, context)

        # Generate code
        code = self._generate_code(template, context)

        # Compile and validate
        tool_func = self._compile_tool(code, template)

        # Wrap in tool class
        tool = DynamicTool(
            name=f"{template.name} ({context.get('industry', 'custom')})",
            description=template.description,
            func=tool_func,
            parameters_schema=template.parameters_schema,
            estimated_cost=template.estimated_cost,
            estimated_latency=template.estimated_latency,
        )

        # Cache
        if cache:
            self.generated_tools[cache_key] = tool

        logger.info(f"Generated tool: {template_id} with context: {list(context.keys())}")

        return tool

    def _get_cache_key(self, template_id: str, context: Dict[str, Any]) -> str:
        """Generate cache key"""
        context_str = str(sorted(context.items()))
        return hashlib.md5(f"{template_id}:{context_str}".encode()).hexdigest()

    def _validate_context(self, template: ToolTemplate, context: Dict[str, Any]):
        """Validate context has required fields"""
        missing = [
            field
            for field in template.context_requirements
            if field not in context
        ]

        if missing:
            raise ValueError(
                f"Missing required context fields for {template.template_id}: {missing}"
            )

    def _generate_code(self, template: ToolTemplate, context: Dict[str, Any]) -> str:
        """Generate code by filling template"""
        code = template.code_template

        # Replace placeholders
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in code:
                # Format value based on type
                if isinstance(value, str):
                    formatted_value = f'"{value}"'
                elif isinstance(value, (dict, list)):
                    formatted_value = str(value)
                else:
                    formatted_value = str(value)

                code = code.replace(placeholder, formatted_value)

        return code

    def _compile_tool(self, code: str, template: ToolTemplate) -> Callable:
        """Compile and validate tool code"""
        try:
            # Parse code
            tree = ast.parse(code)

            # Security check: no dangerous operations
            self._security_check(tree)

            # Compile
            compiled = compile(code, f"<dynamic:{template.template_id}>", "exec")

            # Execute in isolated namespace
            namespace: Dict[str, Any] = {}
            exec(compiled, namespace)

            # Extract function
            func_name = template.code_template.split("async def ")[1].split("(")[0]
            if func_name not in namespace:
                raise ValueError(f"Function {func_name} not found in generated code")

            return namespace[func_name]

        except Exception as e:
            logger.error(f"Failed to compile tool: {e}")
            raise

    def _security_check(self, tree: ast.AST):
        """Security check for generated code"""
        # Check for dangerous operations
        dangerous_nodes = []

        for node in ast.walk(tree):
            # No imports (except allowed ones)
            if isinstance(node, ast.Import):
                dangerous_nodes.append("import")

            # No exec/eval
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ["exec", "eval", "__import__"]:
                        dangerous_nodes.append(node.func.id)

            # No file operations
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ["open", "file"]:
                        dangerous_nodes.append(node.func.id)

        if dangerous_nodes:
            raise SecurityError(
                f"Dangerous operations detected in generated code: {dangerous_nodes}"
            )


class DynamicTool:
    """动态生成的工具"""

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        parameters_schema: Dict[str, Any],
        estimated_cost: float = 0.0,
        estimated_latency: float = 1.0,
    ):
        self.name = name
        self.description = description
        self.func = func
        self.parameters_schema = parameters_schema
        self.estimated_cost = estimated_cost
        self.estimated_latency = estimated_latency

    async def execute(self, **kwargs) -> Any:
        """Execute tool"""
        try:
            result = await self.func(**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"success": False, "error": str(e)}

    def schema(self) -> Dict[str, Any]:
        """Get tool schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema,
            },
        }


class SecurityError(Exception):
    """Security violation in generated code"""
    pass


# Example usage
async def example_usage():
    """Example of dynamic tool generation"""
    generator = DynamicToolGenerator()

    # Generate ROI calculator for SaaS industry
    roi_tool = await generator.generate(
        template_id="roi_calculator",
        context={
            "industry": "SaaS",
            "avg_roi": 2.5,  # 250% average ROI in SaaS
            "implementation_cost": 50000,
        },
    )

    # Use the tool
    result = await roi_tool.execute(
        current_spend=200000,
        expected_improvement=0.30,  # 30% improvement
    )

    print(result)
    # Output: {
    #     "success": True,
    #     "result": {
    #         "industry": "SaaS",
    #         "annual_savings": 60000,
    #         "payback_period_months": 10,
    #         "three_year_roi_percent": 260,
    #         "benchmark_comparison": "above"
    #     }
    # }

    # Generate pricing tool for enterprise customer
    pricing_tool = await generator.generate(
        template_id="dynamic_pricer",
        context={
            "customer_tier": "enterprise",
            "industry": "Finance",
            "relationship_score": 0.8,  # Strong relationship
            "tier_discounts": {
                "startup": 0.05,
                "growth": 0.10,
                "enterprise": 0.20,
            },
            "volume_discounts": {
                100: 0.05,
                500: 0.10,
                1000: 0.15,
            },
        },
    )

    # Use the tool
    result = await pricing_tool.execute(base_price=100, quantity=1000)

    print(result)
    # Output: {
    #     "success": True,
    #     "result": {
    #         "base_price": 100,
    #         "quantity": 1000,
    #         "tier_discount": 0.20,
    #         "volume_discount": 0.15,
    #         "relationship_discount": 0.04,
    #         "total_discount": 0.39,
    #         "final_price": 61000,
    #         "price_per_unit": 61
    #     }
    # }
