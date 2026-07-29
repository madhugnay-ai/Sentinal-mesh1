from __future__ import annotations

from agents.approval import ApprovalAgent
from agents.auto_healing import AutoHealingAgent
from agents.base_agent import BaseAgent
from agents.email_trigger import EmailTriggerAgent
from agents.budget_validation import BudgetValidationAgent
from agents.classifier_agent import ClassifierAgent
from agents.condition_agent import ConditionAgent
from agents.extractor_agent import ExtractorAgent
from agents.llm_agent import LLMAgent
from agents.router_agent import RouterAgent
from agents.send_email_agent import SendEmailAgent
from agents.failure_detection import FailureDetectionAgent
from agents.inventory import InventoryAgent
from agents.purchase_order import PurchaseOrderAgent
from agents.rag_incident_memory import RAGIncidentMemoryAgent
from agents.requirement_validation import RequirementValidationAgent
from agents.supervisor import SupervisorAgent
from agents.vendor_selection import VendorSelectionAgent
from constants import node_types


class AgentRegistry:
    def __init__(self) -> None:
        self._registry: dict[str, BaseAgent] = {
            node_types.REQUIREMENT_VALIDATION: RequirementValidationAgent(),
            node_types.INVENTORY: InventoryAgent(),
            node_types.VENDOR_SELECTION: VendorSelectionAgent(),
            node_types.BUDGET_VALIDATION: BudgetValidationAgent(),
            node_types.APPROVAL: ApprovalAgent(),
            node_types.PURCHASE_ORDER: PurchaseOrderAgent(),
            "Email Trigger": EmailTriggerAgent(),
            "LLM": LLMAgent(),
            node_types.CONDITION: ConditionAgent(),
            node_types.ROUTER: RouterAgent(),
            node_types.CLASSIFIER: ClassifierAgent(),
            node_types.EXTRACTOR: ExtractorAgent(),
            node_types.SEND_EMAIL: SendEmailAgent(),
            node_types.SUPERVISOR: SupervisorAgent(),
            node_types.FAILURE_DETECTION: FailureDetectionAgent(),
            node_types.RAG_INCIDENT_MEMORY: RAGIncidentMemoryAgent(),
            node_types.AUTO_HEALING: AutoHealingAgent(),
        }

    def get_agent(self, node_type: str | None) -> BaseAgent | None:
        if not node_type:
            return None
        return self._registry.get(node_type)
