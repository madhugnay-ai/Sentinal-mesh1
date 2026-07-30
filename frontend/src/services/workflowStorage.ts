import type { SavedWorkflow, WorkflowEdge, WorkflowNode, WorkflowPayload, WorkflowStorageEnvelope } from '../types/workflow';
import { normalizeClassifierCategory } from '../utils/classifierHandles';

const storageKey = 'sentinelmesh-workflow';
const workflowCollectionKey = 'sentinelmesh-workflows';

function createWorkflowId() {
  return `workflow-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function dedupeWorkflows(workflows: SavedWorkflow[]): SavedWorkflow[] {
  const uniqueWorkflows = new Map<string, SavedWorkflow>();

  workflows.forEach((workflow) => {
    if (!workflow?.id) {
      return;
    }

    uniqueWorkflows.set(workflow.id, workflow);
  });

  return Array.from(uniqueWorkflows.values());
}

function readWorkflowStorageEnvelope(): WorkflowStorageEnvelope {
  if (typeof window === 'undefined') {
    return { currentWorkflowId: null, workflows: [] };
  }

  const stored = window.localStorage.getItem(workflowCollectionKey);
  if (!stored) {
    return { currentWorkflowId: null, workflows: [] };
  }

  try {
    const parsed = JSON.parse(stored) as Partial<WorkflowStorageEnvelope>;
    return {
      currentWorkflowId: parsed.currentWorkflowId ?? null,
      workflows: dedupeWorkflows(Array.isArray(parsed.workflows) ? parsed.workflows : []),
    };
  } catch {
    return { currentWorkflowId: null, workflows: [] };
  }
}

function writeWorkflowStorageEnvelope(envelope: WorkflowStorageEnvelope) {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(workflowCollectionKey, JSON.stringify(envelope));
}

function toPayloadNodes(nodes: WorkflowNode[]): WorkflowNode[] {
  return nodes.map((node) => ({ ...node }));
}

function toWorkflowNodes(nodes: WorkflowNode[]): WorkflowNode[] {
  return nodes.map((node) => ({ ...node }));
}

export function normalizeWorkflowEdges(nodes: WorkflowNode[], edges: WorkflowEdge[]): WorkflowEdge[] {
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));

  return edges.map((edge) => {
    if (!edge || typeof edge !== 'object') {
      return edge;
    }

    const sourceNode = nodeMap.get(edge.source);
    const sourceKind = sourceNode?.data?.kind?.toLowerCase();
    const categories = Array.isArray(sourceNode?.data?.categories)
      ? sourceNode.data.categories.filter((category): category is string => typeof category === 'string' && category.trim().length > 0)
      : [];

    if (sourceKind === 'classifier') {
      const existingHandle = normalizeClassifierCategory(edge.sourceHandle);
      const fallbackHandle = normalizeClassifierCategory(categories[0]);

      if (existingHandle) {
        return {
          ...edge,
          sourceHandle: existingHandle,
        };
      }

      if (fallbackHandle) {
        return {
          ...edge,
          sourceHandle: fallbackHandle,
        };
      }
    }

    return edge;
  });
}

export function saveWorkflowToStorage(
  nodes: WorkflowNode[],
  edges: WorkflowEdge[],
  options?: { workflowId?: string | null; name?: string; description?: string },
): SavedWorkflow {
  const envelope = readWorkflowStorageEnvelope();
  const workflowId = options?.workflowId ?? envelope.currentWorkflowId ?? createWorkflowId();
  const now = new Date().toISOString();
  const existingWorkflow = envelope.workflows.find((workflow) => workflow.id === workflowId);
  const workflowName = options?.name?.trim() || existingWorkflow?.name || 'Procurement Workflow';
  const description = options?.description?.trim() || existingWorkflow?.description || 'Workflow stored locally in SentinelMesh Studio.';

  const payload: WorkflowPayload = {
    name: workflowName,
    description,
    nodes: toPayloadNodes(nodes),
    edges: normalizeWorkflowEdges(nodes, edges),
  };

  const workflow: SavedWorkflow = {
    id: workflowId,
    name: workflowName,
    description,
    nodes: payload.nodes,
    edges: payload.edges,
    createdAt: existingWorkflow?.createdAt ?? now,
    updatedAt: now,
  };

  const nextWorkflows = dedupeWorkflows([...envelope.workflows.filter((item) => item.id !== workflowId), workflow]);

  writeWorkflowStorageEnvelope({ currentWorkflowId: workflowId, workflows: nextWorkflows });

  if (typeof window !== 'undefined') {
    window.localStorage.setItem(storageKey, JSON.stringify(payload));
  }

  return workflow;
}

export function loadWorkflowFromStorage(workflowId?: string | null): SavedWorkflow | null {
  const envelope = readWorkflowStorageEnvelope();
  const selectedWorkflow = workflowId
    ? envelope.workflows.find((workflow) => workflow.id === workflowId)
    : envelope.currentWorkflowId
      ? envelope.workflows.find((workflow) => workflow.id === envelope.currentWorkflowId)
      : envelope.workflows.length > 0
        ? envelope.workflows[envelope.workflows.length - 1]
        : null;

  if (selectedWorkflow) {
    return {
      ...selectedWorkflow,
      nodes: toWorkflowNodes(selectedWorkflow.nodes),
      edges: normalizeWorkflowEdges(toWorkflowNodes(selectedWorkflow.nodes), selectedWorkflow.edges ?? []),
    };
  }

  if (typeof window === 'undefined') {
    return null;
  }

  const stored = window.localStorage.getItem(storageKey);
  if (!stored) {
    return null;
  }

  const parsed = JSON.parse(stored) as WorkflowPayload;
  const migratedWorkflow: SavedWorkflow = {
    id: workflowId ?? createWorkflowId(),
    name: parsed.name ?? '',
    description: parsed.description ?? '',
    nodes: toPayloadNodes(parsed.nodes as WorkflowNode[]),
    edges: normalizeWorkflowEdges(parsed.nodes as WorkflowNode[], parsed.edges ?? []),
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  const nextWorkflows = dedupeWorkflows([...envelope.workflows.filter((item) => item.id !== migratedWorkflow.id), migratedWorkflow]);
  writeWorkflowStorageEnvelope({ currentWorkflowId: migratedWorkflow.id, workflows: nextWorkflows });

  return migratedWorkflow;
}

export function listWorkflowsFromStorage(): SavedWorkflow[] {
  const envelope = readWorkflowStorageEnvelope();
  return dedupeWorkflows(envelope.workflows)
    .map((workflow) => ({
      ...workflow,
      nodes: toWorkflowNodes(workflow.nodes),
      edges: normalizeWorkflowEdges(toWorkflowNodes(workflow.nodes), workflow.edges ?? []),
    }))
    .sort((left, right) => (left.updatedAt ?? '').localeCompare(right.updatedAt ?? ''));
}

export function exportWorkflowJson(name: string, nodes: WorkflowNode[], edges: WorkflowEdge[]) {
  const payload = saveWorkflowToStorage(nodes, edges, { name });
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${name || 'workflow'}.json`;
  link.click();
  URL.revokeObjectURL(url);
}
