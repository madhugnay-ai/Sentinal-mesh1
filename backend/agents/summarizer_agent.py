from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from agents.base_agent import BaseAgent
from agents.llm_agent import GeminiProvider, GroqProvider, OpenAIProvider
from graph.state import WorkflowState


class SummarizerAgent(BaseAgent):
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

    def _set_failure_state(self, state: WorkflowState, errors: list[str] | str, log_message: str) -> WorkflowState:
        state["errors"] = [errors] if isinstance(errors, str) else list(errors)
        state["execution_status"] = "failed"
        node_id = state.get("current_node")
        if isinstance(node_id, str):
            failed_nodes = [node for node in list(state.get("failed_node_ids") or []) if isinstance(node, str)]
            if node_id not in failed_nodes:
                failed_nodes.append(node_id)
            state["failed_node_ids"] = failed_nodes
        state.setdefault("execution_log", []).append(log_message)
        return state

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
            return str(state.get("input_text") or "")

        if state.get("input_text"):
            return str(state["input_text"])
        if state.get("email_subject"):
            return str(state["email_subject"])
        if state.get("email_body"):
            return str(state["email_body"])
        return ""

    def _build_prompt(self, instructions: str) -> str:
        return instructions or "Summarize the incoming content clearly and concisely. Preserve the important facts, issue, impact, and requested action. Do not invent information."

    def execute(self, state: WorkflowState) -> WorkflowState:
        config = self._get_node_config(state)
        if config is None:
            return self._set_failure_state(
                state,
                ["Summarizer node configuration missing."],
                f"{datetime.now(timezone.utc).isoformat()} Summarizer node configuration missing.",
            )

        if state.get("execution_status") == "no_messages":
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Summarizer skipped due to no_messages."
            )
            state.setdefault("skipped_nodes", []).append(state.get("current_node", "unknown"))
            return state

        input_field = str(config.get("inputField") or config.get("input_field") or "email_subject_and_body")
        input_text = self._resolve_input_text(state, input_field)
        if not str(input_text or "").strip():
            return self._set_failure_state(
                state,
                ["No input available to summarize."],
                f"{datetime.now(timezone.utc).isoformat()} Summarizer failed: no input available.",
            )

        provider_name = str(config.get("provider") or "Groq")
        model = str(config.get("model") or "llama-3.1-8b-instant")
        temperature = float(config.get("temperature") or 0.2)
        max_tokens = int(config.get("maxTokens") or 256)
        api_key = config.get("apiKey")
        prompt = self._build_prompt(str(config.get("instructions") or "Summarize the incoming content clearly and concisely. Preserve the important facts, issue, impact, and requested action. Do not invent information."))

        try:
            provider = self._get_provider(provider_name)
            response_text = provider.generate_text(prompt, input_text, model, temperature, max_tokens, api_key)
        except Exception as exc:  # pragma: no cover - defensive for runtime/provider failures
            return self._set_failure_state(
                state,
                [str(exc)],
                f"{datetime.now(timezone.utc).isoformat()} Summarizer execution failed: {exc}",
            )

        state["summary"] = str(response_text or "")
        state["summary_input_field"] = input_field
        state["summary_provider"] = provider_name
        state["summary_model"] = model
        state["execution_status"] = "completed"
        state.setdefault("execution_log", []).append(
            f"{datetime.now(timezone.utc).isoformat()} Summarizer completed using {provider_name} ({model})."
        )
        return state
