from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from agents.base_agent import BaseAgent
from graph.state import WorkflowState


class BaseLLMProvider:
    def generate_text(self, prompt: str, input_text: str, model: str, temperature: float, max_tokens: int, api_key: str | None = None) -> str:
        raise NotImplementedError


class OpenAIProvider(BaseLLMProvider):
    def generate_text(self, prompt: str, input_text: str, model: str, temperature: float, max_tokens: int, api_key: str | None = None) -> str:
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Missing OpenAI API key")
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": f"{prompt}\n\n{input_text}"}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            payload = response.json()
            return payload["choices"][0]["message"]["content"]


class GeminiProvider(BaseLLMProvider):
    def generate_text(self, prompt: str, input_text: str, model: str, temperature: float, max_tokens: int, api_key: str | None = None) -> str:
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Missing Gemini API key")
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                json={"contents": [{"parts": [{"text": f"{prompt}\n\n{input_text}"}]}], "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}},
            )
            response.raise_for_status()
            payload = response.json()
            return payload["candidates"][0]["content"]["parts"][0]["text"]


class GroqProvider(BaseLLMProvider):
    def generate_text(self, prompt: str, input_text: str, model: str, temperature: float, max_tokens: int, api_key: str | None = None) -> str:
        api_key = api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Missing Groq API key")
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": f"{prompt}\n\n{input_text}"}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            payload = response.json()
            return payload["choices"][0]["message"]["content"]


class LLMAgent(BaseAgent):
    def __init__(self, node_id: str | None = None) -> None:
        self.node_id = node_id

    def _get_provider(self, provider_name: str) -> BaseLLMProvider:
        providers = {
            "OpenAI": OpenAIProvider(),
            "Gemini": GeminiProvider(),
            "Groq": GroqProvider(),
        }
        return providers.get(provider_name, OpenAIProvider())

    def _resolve_input_text(self, state: WorkflowState) -> str:
        if state.get("input_text"):
            return str(state["input_text"])
        if isinstance(state.get("email_messages"), list):
            for message in state["email_messages"]:
                if isinstance(message, dict) and message.get("body"):
                    return str(message["body"])
        return ""

    def execute(self, state: WorkflowState) -> WorkflowState:
        workflow_data = state.get("workflow_data") or {}
        nodes = workflow_data.get("nodes") or []
        node_config: dict[str, Any] | None = None

        for node in nodes if isinstance(nodes, list) else []:
            if isinstance(node, dict) and node.get("id") == state.get("current_node"):
                data = node.get("data") if isinstance(node.get("data"), dict) else {}
                node_config = data
                break

        if node_config is None:
            state["errors"] = ["LLM node configuration missing."]
            state["execution_status"] = "failed"
            return state

        provider_name = str(node_config.get("provider") or "OpenAI")
        model = str(node_config.get("model") or "gpt-4.1-mini")
        prompt = str(node_config.get("prompt") or "")
        temperature = float(node_config.get("temperature") or 0.0)
        max_tokens = int(node_config.get("maxTokens") or 256)
        api_key = node_config.get("apiKey")

        try:
            provider = self._get_provider(provider_name)
            resolved_input = self._resolve_input_text(state)
            # Safe diagnostic logging: only log input length, provider and model.
            input_chars = len(str(resolved_input or ""))
            state.setdefault("execution_log", []).append(
                f"{datetime.now(timezone.utc).isoformat()} LLM input prepared: input_chars={input_chars}, provider={provider_name}, model={model}"
            )
            response_text = provider.generate_text(prompt, resolved_input, model, temperature, max_tokens, api_key)
        except (ValueError, httpx.HTTPError, TimeoutError) as exc:
            state["errors"] = [str(exc)]
            state["execution_status"] = "failed"
            state.setdefault("execution_log", []).append(f"{datetime.now(timezone.utc).isoformat()} LLM execution failed: {exc}")
            return state

        state["llm_output"] = response_text
        state["llm_provider"] = provider_name
        state["llm_model"] = model
        state["llm_prompt"] = prompt
        state["llm_temperature"] = temperature
        state["llm_max_tokens"] = max_tokens
        state["execution_status"] = "completed"
        state.setdefault("execution_log", []).append(
            f"{datetime.now(timezone.utc).isoformat()} LLM execution completed using {provider_name} ({model})."
        )
        return state
