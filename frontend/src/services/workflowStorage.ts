import type { WorkflowEdge, WorkflowNode, WorkflowPayload } from '../types/workflow';

const storageKey = 'sentinelmesh-workflow';

export function saveWorkflowToStorage(nodes: WorkflowNode[], edges: WorkflowEdge[]) {
  const payload: WorkflowPayload = {
    name: 'Procurement Workflow',
    description: 'Workflow stored locally in SentinelMesh Studio.',
    nodes: nodes.map(({ id, type, position, data }) => ({ id, type, position, data })),
    edges,
  };
  localStorage.setItem(storageKey, JSON.stringify(payload));
  return payload;
}

export function loadWorkflowFromStorage(): { name: string; nodes: WorkflowNode[]; edges: WorkflowEdge[] } | null {
  const stored = localStorage.getItem(storageKey);
  if (!stored) {
    return null;
  }

  const parsed = JSON.parse(stored) as WorkflowPayload;
  return {
    name: parsed.name ?? '',
    nodes: parsed.nodes as WorkflowNode[],
    edges: parsed.edges,
  };
}

export function exportWorkflowJson(name: string, nodes: WorkflowNode[], edges: WorkflowEdge[]) {
  const payload = saveWorkflowToStorage(nodes, edges);
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${name || 'workflow'}.json`;
  link.click();
  URL.revokeObjectURL(url);
}
