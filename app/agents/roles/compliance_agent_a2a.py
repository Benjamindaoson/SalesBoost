"""
A2A-enabled Compliance Agent

Compliance monitoring agent with A2A communication capabilities.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.a2a.agent_base import A2AAgent
from app.a2a.message_bus import A2AMessageBus
from app.a2a.protocol import A2AMessage

logger = logging.getLogger(__name__)


class ComplianceAgentA2A(A2AAgent):
    """
    A2A-enabled Compliance Agent

    Monitors all agent communications for compliance violations
    and provides real-time alerts.

    Capabilities:
    - compliance_check: Check for compliance violations
    - risk_monitoring: Monitor risk levels
    - policy_enforcement: Enforce company policies
    - audit_trail: Maintain audit trail
    """

    def __init__(
        self,
        agent_id: str,
        message_bus: A2AMessageBus,
        compliance_rules: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Initialize Compliance Agent

        Args:
            agent_id: Unique agent identifier
            message_bus: Message bus instance
            compliance_rules: Compliance rules configuration
            **kwargs: Additional arguments
        """
        super().__init__(
            agent_id=agent_id,
            message_bus=message_bus,
            capabilities=[
                "compliance_check",
                "risk_monitoring",
                "policy_enforcement",
                "audit_trail",
            ],
            agent_type="ComplianceAgent",
            metadata={"version": "2.0", "a2a_enabled": True},
            **kwargs,
        )

        self.compliance_rules = compliance_rules or self._get_default_rules()

        # Violation tracking
        self.violations: List[Dict[str, Any]] = []
        self.audit_log: List[Dict[str, Any]] = []

    def _get_default_rules(self) -> Dict[str, Any]:
        """Get default compliance rules"""
        return {
            "forbidden_phrases": [
                "guaranteed returns",
                "risk-free",
                "100% success",
                "no risk",
                "can't lose",
            ],
            "required_disclosures": [
                "terms and conditions apply",
                "subject to approval",
                "pricing may vary",
            ],
            "sensitive_topics": [
                "personal health information",
                "financial details",
                "social security",
                "credit card",
            ],
            "max_discount": 30,  # Maximum discount percentage
            "approval_required_threshold": 50000,  # Deal value requiring approval
        }

    async def handle_request(self, message: A2AMessage) -> Dict[str, Any]:
        """
        Handle incoming requests

        Supported actions:
        - check_compliance: Check content for compliance
        - check_deal: Check deal for compliance
        - get_violations: Get violation history
        - get_audit_log: Get audit log
        """
        action = message.payload.get("action")
        parameters = message.payload.get("parameters", {})

        if action == "check_compliance":
            return await self._check_compliance(parameters)
        elif action == "check_deal":
            return await self._check_deal(parameters)
        elif action == "get_violations":
            return await self._get_violations(parameters)
        elif action == "get_audit_log":
            return await self._get_audit_log(parameters)
        else:
            raise ValueError(f"Unknown action: {action}")

    async def handle_event(self, message: A2AMessage):
        """
        Handle incoming events

        Monitors all events for compliance issues.
        """
        event_type = message.payload.get("event_type")
        data = message.payload.get("data", {})

        # Log all events for audit trail
        self._log_event(message)

        # Check specific events
        if event_type == "response_generated":
            await self._check_response_compliance(message.from_agent, data)
        elif event_type == "deal_closed":
            await self._check_deal_compliance(message.from_agent, data)
        elif event_type == "customer_message":
            await self._check_customer_interaction(message.from_agent, data)
        else:
            logger.debug(f"Compliance Agent monitoring event: {event_type}")

    async def _check_compliance(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check content for compliance violations

        Args:
            parameters: {
                "content": str,
                "context": dict
            }

        Returns:
            Compliance check result
        """
        content = parameters.get("content", "")
        context = parameters.get("context", {})

        logger.info("Checking compliance")

        violations = []

        # Check for forbidden phrases
        content_lower = content.lower()
        for phrase in self.compliance_rules["forbidden_phrases"]:
            if phrase in content_lower:
                violations.append({
                    "type": "forbidden_phrase",
                    "phrase": phrase,
                    "severity": "high",
                    "message": f"Content contains forbidden phrase: '{phrase}'",
                })

        # Check for sensitive topics
        for topic in self.compliance_rules["sensitive_topics"]:
            if topic in content_lower:
                violations.append({
                    "type": "sensitive_topic",
                    "topic": topic,
                    "severity": "medium",
                    "message": f"Content mentions sensitive topic: '{topic}'",
                })

        # Check for required disclosures (if making claims)
        claim_keywords = ["guarantee", "promise", "ensure", "will"]
        has_claims = any(keyword in content_lower for keyword in claim_keywords)
        has_disclosure = any(
            disclosure in content_lower
            for disclosure in self.compliance_rules["required_disclosures"]
        )

        if has_claims and not has_disclosure:
            violations.append({
                "type": "missing_disclosure",
                "severity": "high",
                "message": "Claims made without required disclosure",
            })

        result = {
            "compliant": len(violations) == 0,
            "violations": violations,
            "risk_level": self._calculate_risk_level(violations),
            "recommendations": self._get_recommendations(violations),
        }

        # Store violations
        if violations:
            self.violations.extend(violations)

        return result

    async def _check_deal(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check deal for compliance

        Args:
            parameters: {
                "deal_info": dict
            }

        Returns:
            Deal compliance check result
        """
        deal_info = parameters.get("deal_info", {})
        deal_value = deal_info.get("value", 0)
        discount = deal_info.get("discount", 0)

        logger.info(f"Checking deal compliance: value={deal_value}, discount={discount}")

        violations = []

        # Check discount limit
        if discount > self.compliance_rules["max_discount"]:
            violations.append({
                "type": "excessive_discount",
                "severity": "high",
                "message": f"Discount {discount}% exceeds maximum {self.compliance_rules['max_discount']}%",
                "requires_approval": True,
            })

        # Check approval threshold
        approval_required = deal_value >= self.compliance_rules["approval_required_threshold"]

        result = {
            "compliant": len(violations) == 0,
            "violations": violations,
            "approval_required": approval_required,
            "risk_level": self._calculate_risk_level(violations),
        }

        return result

    async def _get_violations(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get violation history"""
        limit = parameters.get("limit", 100)
        severity = parameters.get("severity")

        violations = self.violations[-limit:]

        if severity:
            violations = [v for v in violations if v.get("severity") == severity]

        return {
            "violations": violations,
            "total_count": len(self.violations),
            "filtered_count": len(violations),
        }

    async def _get_audit_log(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get audit log"""
        limit = parameters.get("limit", 100)

        return {
            "audit_log": self.audit_log[-limit:],
            "total_entries": len(self.audit_log),
        }

    async def _check_response_compliance(self, agent_id: str, data: Dict[str, Any]):
        """Check response for compliance"""
        response = data.get("response", {})
        message = response.get("message", "")

        # Check compliance
        check_result = await self._check_compliance({"content": message})

        if not check_result["compliant"]:
            # Send alert to agent
            await self.send_event(
                to_agent=agent_id,
                event_type="compliance_alert",
                data={
                    "alert": "Compliance violation detected",
                    "violations": check_result["violations"],
                    "risk_level": check_result["risk_level"],
                    "action_required": "Revise response before sending",
                },
            )

            # Broadcast violation event
            await self.broadcast_event(
                event_type="compliance_violation",
                data={
                    "agent_id": agent_id,
                    "violations": check_result["violations"],
                    "risk_level": check_result["risk_level"],
                },
            )

            logger.warning(
                f"Compliance violation detected for agent {agent_id}: "
                f"{len(check_result['violations'])} violations"
            )

    async def _check_deal_compliance(self, agent_id: str, data: Dict[str, Any]):
        """Check deal for compliance"""
        deal_info = data.get("deal_info", {})

        # Check deal compliance
        check_result = await self._check_deal({"deal_info": deal_info})

        if not check_result["compliant"] or check_result["approval_required"]:
            # Send alert
            await self.send_event(
                to_agent=agent_id,
                event_type="compliance_alert",
                data={
                    "alert": "Deal requires compliance review",
                    "violations": check_result["violations"],
                    "approval_required": check_result["approval_required"],
                    "action_required": "Obtain approval before proceeding",
                },
            )

            logger.warning(f"Deal compliance issue for agent {agent_id}")

    async def _check_customer_interaction(self, agent_id: str, data: Dict[str, Any]):
        """Check customer interaction for compliance"""
        message = data.get("message", "")

        # Check for sensitive information in customer message
        check_result = await self._check_compliance({"content": message})

        if check_result["risk_level"] == "high":
            # Alert agent about sensitive information
            await self.send_event(
                to_agent=agent_id,
                event_type="compliance_alert",
                data={
                    "alert": "Customer shared sensitive information",
                    "risk_level": "high",
                    "action_required": "Handle with care, do not store unnecessarily",
                },
            )

    def _calculate_risk_level(self, violations: List[Dict[str, Any]]) -> str:
        """Calculate overall risk level from violations"""
        if not violations:
            return "low"

        high_severity = sum(1 for v in violations if v.get("severity") == "high")
        medium_severity = sum(1 for v in violations if v.get("severity") == "medium")

        if high_severity > 0:
            return "high"
        elif medium_severity > 1:
            return "medium"
        else:
            return "low"

    def _get_recommendations(self, violations: List[Dict[str, Any]]) -> List[str]:
        """Get recommendations based on violations"""
        recommendations = []

        for violation in violations:
            if violation["type"] == "forbidden_phrase":
                recommendations.append(
                    f"Remove or rephrase: '{violation['phrase']}'"
                )
            elif violation["type"] == "missing_disclosure":
                recommendations.append(
                    "Add required disclosure: 'Terms and conditions apply'"
                )
            elif violation["type"] == "sensitive_topic":
                recommendations.append(
                    f"Avoid discussing: '{violation['topic']}'"
                )
            elif violation["type"] == "excessive_discount":
                recommendations.append(
                    "Reduce discount or obtain manager approval"
                )

        return recommendations

    def _log_event(self, message: A2AMessage):
        """Log event to audit trail"""
        self.audit_log.append({
            "timestamp": message.timestamp,
            "event_type": message.payload.get("event_type"),
            "from_agent": message.from_agent,
            "to_agent": message.to_agent,
            "conversation_id": message.conversation_id,
        })

        # Keep audit log size manageable
        if len(self.audit_log) > 10000:
            self.audit_log = self.audit_log[-5000:]
