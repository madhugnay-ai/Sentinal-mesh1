from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.base_agent import BaseAgent
from agents.llm_agent import GeminiProvider, GroqProvider, OpenAIProvider
from graph.state import WorkflowState


class ClassifierAgent(BaseAgent):
    def _get_provider(self, provider_name: str):
        providers = {
            "OpenAI": OpenAIProvider(),
            "Gemini": GeminiProvider(),
            "Groq": GroqProvider(),
        }
        return providers.get(provider_name, OpenAIProvider())

    def _get_node_config(self, state: WorkflowState) -> dict[str, Any] | None:
        workflow_data = state.get("workflow_data") or {}
        nodes = workflow_data.get("nodes") or []

        for node in nodes if isinstance(nodes, list) else []:
            if isinstance(node, dict) and node.get("id") == state.get("current_node"):
                data = node.get("data")
                if isinstance(data, dict):
                    return data
        return None

    def _normalize_categories(self, categories: Any) -> list[str]:
        if isinstance(categories, str):
            parsed = [item.strip() for item in categories.split(",") if item.strip()]
            return [category.lower() for category in parsed]
        if isinstance(categories, list):
            normalized = []
            for category in categories:
                if isinstance(category, str):
                    cleaned = category.strip()
                    if cleaned:
                        normalized.append(cleaned.lower())
            return normalized
        return []

    def _resolve_input_text(self, state: WorkflowState, input_field: str) -> str:
        field = (input_field or "").strip()
        if field in {"email_subject", "email_subject_and_body", "email_body", "input", "input_text"}:
            if field == "email_subject":
                return str(state.get("email_subject") or "")
            if field == "email_body":
                return str(state.get("email_body") or "")
            if field == "email_subject_and_body":
                subject = str(state.get("email_subject") or "").strip()
                body = str(state.get("email_body") or "").strip()
                parts = [part for part in [subject, body] if part]
                if parts:
                    return "\n\n".join(parts)
                return str(state.get("input_text") or "")
            if field == "input":
                return str(state.get("input_text") or "")
            return str(state.get("input_text") or "")

        if state.get("input_text"):
            return str(state["input_text"])
        if state.get("email_subject"):
            return str(state["email_subject"])
        if state.get("email_body"):
            return str(state["email_body"])
        return ""

    def _build_prompt(self, categories: list[str], instructions: str) -> str:
        category_list = ", ".join(categories)
        base_prompt = instructions or "Classify the incoming content into exactly one configured category."
        return (
            f"{base_prompt}\n\n"
            f"Allowed categories: {category_list}\n"
            "Return exactly one category from the allowed categories and nothing else."
        )

    def execute(self, state: WorkflowState) -> WorkflowState:
        config = self._get_node_config(state)
        if config is None:
            state["errors"] = ["Classifier node configuration missing."]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Classifier node configuration missing."
            )
            return state

        if state.get("execution_status") == "no_messages":
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Classifier skipped due to no_messages."
            )
            state.setdefault("skipped_nodes", []).append(state.get("current_node", "unknown"))
            return state

        categories = self._normalize_categories(config.get("categories"))
        if not categories:
            state["errors"] = ["At least one category is required."]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Classifier failed: at least one category is required."
            )
            return state

        input_field = str(config.get("inputField") or config.get("input_field") or "email_subject_and_body")
        input_text = self._resolve_input_text(state, input_field)
        if not str(input_text or "").strip():
            state["errors"] = ["No input available to classify."]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Classifier failed: no input available."
            )
            return state

        provider_name = str(config.get("provider") or "Groq")
        model = str(config.get("model") or "llama-3.1-8b-instant")
        temperature = float(config.get("temperature") or 0.0)
        max_tokens = int(config.get("maxTokens") or 128)
        api_key = config.get("apiKey")
        prompt = self._build_prompt(categories, str(config.get("instructions") or "Classify the incoming content into exactly one configured category."))

        try:
            provider = self._get_provider(provider_name)
            response_text = provider.generate_text(prompt, input_text, model, temperature, max_tokens, api_key)
        except Exception as exc:  # pragma: no cover - defensive for runtime/provider failures
            state["errors"] = [str(exc)]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Classifier execution failed: {exc}"
            )
            return state

        normalized_response = str(response_text or "").strip().lower()
        if normalized_response not in set(categories):
            state["errors"] = [
                f"Invalid classification '{response_text}'. Expected one of: {', '.join(categories)}"
            ]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Classifier failed: invalid classification '{response_text}'."
            )
            return state

        state["classification"] = normalized_response
        state["classifier_input_field"] = input_field
        state["classifier_categories"] = categories
        state["classifier_provider"] = provider_name
        state["classifier_model"] = model
        state["execution_status"] = "completed"
        state.setdefault("execution_log", []).append(
            f"{datetime.now(timezone.utc).isoformat()} Classifier completed: category={normalized_response}"
        )
        return state
