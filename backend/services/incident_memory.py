from __future__ import annotations

import json
from pathlib import Path


class IncidentMemoryService:
    def __init__(self, incidents_path: Path | None = None) -> None:
        self._incidents_path = incidents_path or Path(__file__).resolve().parents[1] / "data" / "incidents.json"
        self._incidents: list[dict[str, object]] = self._load_incidents()

    def _load_incidents(self) -> list[dict[str, object]]:
        if not self._incidents_path.exists():
            return []

        try:
            with self._incidents_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except json.JSONDecodeError:
            return []

        return payload if isinstance(payload, list) else []

    def _severity_rank(self, severity: str | None) -> int:
        severity_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        return severity_order.get(severity or "", 0)

    def retrieve_incidents(
        self,
        failure_category: str | None,
        severity: str | None,
        recoverable: bool | None,
        workflow_health: str | None,
    ) -> list[dict[str, object]]:
        if not self._incidents or not failure_category:
            return []

        category_matches = [incident for incident in self._incidents if incident.get("failure_category") == failure_category]
        if not category_matches:
            return []

        severity_rank = self._severity_rank(severity)
        scored: list[tuple[int, dict[str, object]]] = []
        for incident in category_matches:
            incident_severity = str(incident.get("severity") or "")
            incident_recoverable = bool(incident.get("recoverable"))
            incident_workflow_health = str(incident.get("workflow_health") or "")

            severity_score = 3 if incident_severity == severity else 0
            recoverable_score = 2 if recoverable is not None and incident_recoverable == recoverable else 0
            workflow_score = 1 if workflow_health and incident_workflow_health == workflow_health else 0
            rank_score = self._severity_rank(incident_severity) - severity_rank

            total_score = severity_score + recoverable_score + workflow_score - abs(rank_score)
            scored.append((total_score, incident))

        scored.sort(key=lambda item: (-item[0], item[1].get("incident_id", "")))
        return [incident for _, incident in scored[:3]]
