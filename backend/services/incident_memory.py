from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import List, Dict


class IncidentMemoryService:
    def __init__(self, incidents_path: Path | None = None) -> None:
        self._incidents_path = (
            incidents_path or Path(__file__).resolve().parents[1] / "data" / "incidents.json"
        )
        self._incidents: List[Dict[str, object]] = self._load_incidents()

    def _load_incidents(self) -> List[Dict[str, object]]:
        if not self._incidents_path.exists():
            return []

        try:
            with self._incidents_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except json.JSONDecodeError:
            return []

        return payload if isinstance(payload, list) else []

    def _save_incidents(self) -> None:
        try:
            # Ensure parent exists
            self._incidents_path.parent.mkdir(parents=True, exist_ok=True)
            with self._incidents_path.open("w", encoding="utf-8") as handle:
                json.dump(self._incidents, handle, indent=2)
        except OSError:
            # Best-effort: do not raise in production retrieval path
            return

    def _severity_rank(self, severity: str | None) -> int:
        severity_order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
        return severity_order.get(severity or "", 0)

    def store_incident(self, incident: Dict[str, object]) -> Dict[str, object]:
        # Assign an id if missing
        if not incident.get("incident_id"):
            incident = {**incident, "incident_id": f"INC-{uuid.uuid4().hex[:8].upper()}"}
        # normalize some fields
        if "severity" not in incident:
            incident = {**incident, "severity": "Medium"}
        self._incidents.append(incident)
        self._save_incidents()
        return incident

    def retrieve_incidents(
        self,
        failure_category: str | None,
        severity: str | None,
        recoverable: bool | None,
        workflow_health: str | None,
    ) -> List[Dict[str, object]]:
        if not self._incidents or not failure_category:
            return []

        # flexible matching: prefer exact case-insensitive match, fallback to substring
        fc = str(failure_category).strip().lower()

        def category_match(incident_fc: object) -> bool:
            if not incident_fc:
                return False
            incident_val = str(incident_fc).strip().lower()
            if incident_val == fc:
                return True
            if fc in incident_val or incident_val in fc:
                return True
            return False

        category_matches = [incident for incident in self._incidents if category_match(incident.get("failure_category"))]
        if not category_matches:
            # try fuzzy symptom match: look for category token in symptoms
            token = fc
            symptom_matches = []
            for incident in self._incidents:
                symptoms = incident.get("symptoms") or []
                try:
                    if any(token in str(s).lower() for s in symptoms):
                        symptom_matches.append(incident)
                except Exception:
                    continue
            if symptom_matches:
                category_matches = symptom_matches

        if not category_matches:
            return []

        severity_rank = self._severity_rank(severity)
        scored: List[tuple[int, Dict[str, object]]] = []
        for incident in category_matches:
            incident_severity = str(incident.get("severity") or "")
            incident_recoverable = bool(incident.get("recoverable"))
            incident_workflow_health = str(incident.get("workflow_health") or "")

            # preference scoring
            severity_score = 3 if incident_severity == severity else 0
            recoverable_score = 2 if (recoverable is not None and incident_recoverable == recoverable) else 0
            workflow_score = 1 if workflow_health and incident_workflow_health == workflow_health else 0
            rank_score = self._severity_rank(incident_severity) - severity_rank

            total_score = severity_score + recoverable_score + workflow_score - abs(rank_score)
            scored.append((total_score, incident))

        scored.sort(key=lambda item: (-item[0], item[1].get("incident_id", "")))
        return [incident for _, incident in scored[:3]]
