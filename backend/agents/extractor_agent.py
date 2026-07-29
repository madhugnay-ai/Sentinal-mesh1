from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from agents.base_agent import BaseAgent
from agents.llm_agent import GeminiProvider, GroqProvider, OpenAIProvider
from graph.state import WorkflowState


class ExtractorAgent(BaseAgent):
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

    def _normalize_fields(self, fields: Any) -> list[str]:
        if isinstance(fields, str):
            return [item.strip() for item in fields.split(",") if item.strip()]
        if isinstance(fields, list):
            return [str(item).strip() for item in fields if str(item).strip()]
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
            return str(state.get("input_text") or "")

        if state.get("input_text"):
            return str(state["input_text"])
        if state.get("email_subject"):
            return str(state["email_subject"])
        if state.get("email_body"):
            return str(state["email_body"])
        return ""

    def _build_prompt(self, fields: list[str], instructions: str) -> str:
        field_list = ", ".join(fields)
        base_prompt = instructions or "Extract the requested fields into a structured JSON object."
        return (
            f"{base_prompt}\n\n"
            f"Requested fields: {field_list}\n"
            "Return ONLY valid JSON with string values when possible."
        )

    def _parse_json(self, response_text: str) -> dict[str, Any]:
        text = (response_text or "").strip()
        if not text:
            raise ValueError("Invalid JSON: empty response")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError("Invalid JSON: expected an object")
        return payload

    def execute(self, state: WorkflowState) -> WorkflowState:
        config = self._get_node_config(state)
        if config is None:
            state["errors"] = ["Extractor node configuration missing."]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Extractor node configuration missing."
            )
            return state

        if state.get("execution_status") == "no_messages":
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Extractor skipped due to no_messages."
            )
            state.setdefault("skipped_nodes", []).append(state.get("current_node", "unknown"))
            return state

        fields = self._normalize_fields(config.get("extractionFields") or config.get("fields") or config.get("extraction_fields"))
        if not fields:
            state["errors"] = ["At least one extraction field is required."]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Extractor failed: at least one extraction field is required."
            )
            return state

        input_field = str(config.get("inputField") or config.get("input_field") or "email_subject_and_body")
        input_text = self._resolve_input_text(state, input_field)
        if not str(input_text or "").strip():
            state["errors"] = ["No input available to extract."]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Extractor failed: no input available."
            )
            return state

        provider_name = str(config.get("provider") or "Groq")
        model = str(config.get("model") or "llama-3.1-8b-instant")
        temperature = float(config.get("temperature") or 0.0)
        max_tokens = int(config.get("maxTokens") or 256)
        api_key = config.get("apiKey")
        prompt = self._build_prompt(fields, str(config.get("instructions") or "Extract the requested fields into a structured JSON object."))

        try:
            provider = self._get_provider(provider_name)
            response_text = provider.generate_text(prompt, input_text, model, temperature, max_tokens, api_key)
            parsed_payload = self._parse_json(response_text)
        except Exception as exc:  # pragma: no cover - defensive for runtime/provider failures
            state["errors"] = [str(exc)]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} Extractor execution failed: {exc}"
            )
            return state

        filtered_payload = {
            key: value for key, value in parsed_payload.items() if str(key).strip() in {field.strip() for field in fields}
        }
        state["extracted_data"] = filtered_payload
        state["extractor_input_field"] = input_field
        state["extractor_fields"] = fields
        state["extractor_provider"] = provider_name
        state["extractor_model"] = model
        state["execution_status"] = "completed"
        state.setdefault("execution_log", []).append(
            f"{datetime.now(timezone.utc).isoformat()} Extractor completed: fields={','.join(fields)}"
        )
        return state
