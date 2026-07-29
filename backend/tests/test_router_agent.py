import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.agent_registry import AgentRegistry
from agents.router_agent import RouterAgent
from agents.supervisor import SupervisorAgent
from graph.graph_builder import GraphBuilder


def make_state(current_node: str, workflow_data: dict, initial_state: dict | None = None) -> dict:
    state = {
        "workflow_id": "wf-test",
        "current_node": current_node,
        "execution_status": "pending",
        "execution_log": [],
        "workflow_data": workflow_data,
    }
    if initial_state:
        state.update(initial_state)
    return state


def build_router_node(routes, default_route="default", field="workflow_status") -> dict:
    return {
        "id": "router1",
        "data": {
            "kind": "router",
            "field": field,
            "routes": routes,
            "defaultRoute": default_route,
        },
    }


def test_router_agent_selects_first_matching_route() -> None:
    agent = RouterAgent()
    workflow = {"nodes": [build_router_node([
        {"route": "critical", "operator": "equals", "value": "CRITICAL"},
        {"route": "normal", "operator": "equals", "value": "NORMAL"},
    ])], "edges": []}
    state = make_state("router1", workflow, {"workflow_status": "CRITICAL"})

    result = agent.execute(state)

    assert result["router_result"] == "critical"
    assert result["execution_status"] == "completed"
    assert "Router evaluated" in result["execution_log"][-1]


def test_router_agent_uses_default_route_when_no_rules_match() -> None:
    agent = RouterAgent()
    workflow = {"nodes": [build_router_node([
        {"route": "critical", "operator": "equals", "value": "CRITICAL"},
    ], default_route="default")], "edges": []}
    state = make_state("router1", workflow, {"workflow_status": "UNKNOWN"})

    result = agent.execute(state)

    assert result["router_result"] == "default"
    assert result["execution_status"] == "completed"


def test_router_agent_invalid_operator_fails() -> None:
    agent = RouterAgent()
    workflow = {"nodes": [build_router_node([
        {"route": "critical", "operator": "unsupported", "value": "CRITICAL"},
    ], default_route="default")], "edges": []}
    state = make_state("router1", workflow, {"workflow_status": "CRITICAL"})

    result = agent.execute(state)

    assert result["execution_status"] == "failed"
    assert "Unsupported router operator" in result["errors"][0]


def test_router_agent_selects_second_route_when_first_does_not_match() -> None:
    agent = RouterAgent()
    workflow = {"nodes": [build_router_node([
        {"route": "critical", "operator": "equals", "value": "CRITICAL"},
        {"route": "normal", "operator": "equals", "value": "NORMAL"},
    ], default_route="default")], "edges": []}
    state = make_state("router1", workflow, {"workflow_status": "NORMAL"})

    result = agent.execute(state)

    assert result["router_result"] == "normal"


def test_router_agent_first_match_wins() -> None:
    agent = RouterAgent()
    workflow = {"nodes": [build_router_node([
        {"route": "first", "operator": "contains", "value": "AL"},
        {"route": "second", "operator": "contains", "value": "L"},
    ], default_route="default")], "edges": []}
    state = make_state("router1", workflow, {"workflow_status": "ALPHA"})

    result = agent.execute(state)

    assert result["router_result"] == "first"


def test_router_agent_matches_support_route_case_insensitively() -> None:
    agent = RouterAgent()
    workflow = {"nodes": [build_router_node([
        {"route": "support", "operator": "contains", "value": "SUPPORT"},
    ], default_route="general", field="email_subject")], "edges": []}
    state = make_state("router1", workflow, {"email_subject": "Please support this issue"})

    result = agent.execute(state)

    assert result["router_result"] == "support"
    assert result["execution_status"] == "completed"


def test_router_agent_matches_general_route() -> None:
    agent = RouterAgent()
    workflow = {"nodes": [build_router_node([
        {"route": "critical", "operator": "contains", "value": "CRITICAL"},
        {"route": "support", "operator": "contains", "value": "SUPPORT"},
        {"route": "general", "operator": "contains", "value": "GENERAL"},
    ], default_route="general", field="email_subject")], "edges": []}
    state = make_state("router1", workflow, {"email_subject": "General assistance needed"})

    result = agent.execute(state)

    assert result["router_result"] == "general"
    assert result["execution_status"] == "completed"


def test_router_graph_builder_executes_selected_branch_and_skips_others(monkeypatch) -> None:
    class DummyAgent:
        def __init__(self) -> None:
            self.executed_nodes: list[str] = []

        def execute(self, state):
            self.executed_nodes.append(state["current_node"])
            state.setdefault("execution_log", []).append("dummy executed")
            state["execution_status"] = "completed"
            return state

    dummy_agent = DummyAgent()
    original_get = AgentRegistry.get_agent

    def fake_get(self, node_type):
        if node_type == "Router":
            return RouterAgent()
        if node_type == "Send Email":
            return dummy_agent
        return original_get(self, node_type)

    monkeypatch.setattr(AgentRegistry, "get_agent", fake_get)

    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-router-branch",
        "nodes": [
            {
                "id": "router1",
                "data": {
                    "kind": "router",
                    "field": "workflow_status",
                    "defaultRoute": "default",
                    "routes": [
                        {"route": "critical", "operator": "equals", "value": "CRITICAL"},
                        {"route": "normal", "operator": "equals", "value": "NORMAL"},
                    ],
                },
            },
            {"id": "critical_target", "data": {"kind": "send-email"}},
            {"id": "normal_target", "data": {"kind": "send-email"}},
            {"id": "default_target", "data": {"kind": "send-email"}},
        ],
        "edges": [
            {"source": "router1", "sourceHandle": "critical", "target": "critical_target"},
            {"source": "router1", "sourceHandle": "normal", "target": "normal_target"},
            {"source": "router1", "sourceHandle": "default", "target": "default_target"},
        ],
    }
    state = make_state("router1", workflow, {"workflow_status": "NORMAL"})

    graph = builder.build_graph(workflow)
    final_state = graph.invoke(state)

    assert "normal_target" in dummy_agent.executed_nodes
    assert "critical_target" not in dummy_agent.executed_nodes
    assert "default_target" not in dummy_agent.executed_nodes
    assert final_state["router_result"] == "normal"


def test_router_graph_builder_terminates_safely_when_no_matching_branch_exists(monkeypatch) -> None:
    class DummyAgent:
        def __init__(self) -> None:
            self.executed_nodes: list[str] = []

        def execute(self, state):
            self.executed_nodes.append(state["current_node"])
            state.setdefault("execution_log", []).append("dummy executed")
            state["execution_status"] = "completed"
            return state

    dummy_agent = DummyAgent()
    original_get = AgentRegistry.get_agent

    def fake_get(self, node_type):
        if node_type == "Router":
            return RouterAgent()
        if node_type == "Send Email":
            return dummy_agent
        return original_get(self, node_type)

    monkeypatch.setattr(AgentRegistry, "get_agent", fake_get)

    builder = GraphBuilder()
    workflow = {
        "workflow_id": "wf-router-end",
        "nodes": [
            {
                "id": "router1",
                "data": {
                    "kind": "router",
                    "field": "email_subject",
                    "defaultRoute": "general",
                    "routes": [{"route": "support", "operator": "contains", "value": "SUPPORT"}],
                },
            },
            {"id": "support_target", "data": {"kind": "send-email"}},
            {"id": "general_target", "data": {"kind": "send-email"}},
        ],
        "edges": [
            {"source": "router1", "sourceHandle": "default", "target": "general_target"},
        ],
    }
    state = make_state("router1", workflow, {"email_subject": "Please support this issue"})

    graph = builder.build_graph(workflow)
    final_state = graph.invoke(state)

    assert final_state["router_result"] == "support"
    assert "support_target" not in dummy_agent.executed_nodes
    assert "general_target" not in dummy_agent.executed_nodes


def test_supervisor_marks_only_selected_router_branch_as_completed() -> None:
    workflow = {
        "workflow_id": "wf-router-monitor",
        "nodes": [
            {"id": "email-1", "data": {"kind": "email-trigger", "label": "Email Trigger"}},
            {"id": "router1", "data": {"kind": "router", "label": "Router"}},
            {"id": "critical_target", "data": {"kind": "send-email", "label": "Critical Handler"}},
            {"id": "normal_target", "data": {"kind": "send-email", "label": "Normal Handler"}},
            {"id": "default_target", "data": {"kind": "send-email", "label": "Default Handler"}},
        ],
        "edges": [
            {"source": "router1", "sourceHandle": "critical", "target": "critical_target"},
            {"source": "router1", "sourceHandle": "normal", "target": "normal_target"},
            {"source": "router1", "sourceHandle": "default", "target": "default_target"},
        ],
    }
    state = make_state("router1", workflow, {
        "execution_status": "completed",
        "executed_nodes": ["email-1", "router1"],
        "router_result": "normal",
    })

    result = SupervisorAgent().execute(state)

    assert "Router" in result["completed_stages"]
    assert "Normal Handler" in result["completed_stages"]
    assert "Critical Handler" in result["skipped_stages"]
    assert "Default Handler" in result["skipped_stages"]
