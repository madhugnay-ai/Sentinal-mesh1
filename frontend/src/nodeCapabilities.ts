import type { WorkflowNode } from './types/workflow';

export type NodeCapability = {
  label: string;
  implemented: boolean;
  executable: boolean;
};

export function normalizeNodeKind(kind?: string): string {
  return (kind ?? '')
    .trim()
    .toLowerCase()
    .replace(/[\s_]+/g, '-')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

const capabilities: Record<string, NodeCapability> = {
  'email-trigger': { label: 'Email Trigger', implemented: true, executable: true },
  'requirement-validation': { label: 'Requirement Validation', implemented: true, executable: true },
  inventory: { label: 'Inventory', implemented: true, executable: true },
  'vendor-selection': { label: 'Vendor Selection', implemented: true, executable: true },
  'budget-validation': { label: 'Budget Validation', implemented: true, executable: true },
  'purchase-order': { label: 'Purchase Order', implemented: true, executable: true },
  supervisor: { label: 'Supervisor', implemented: true, executable: true },
  'failure-detection': { label: 'Failure Detection', implemented: true, executable: true },
  'rag-incident-memory': { label: 'RAG Incident Memory', implemented: true, executable: true },
  'auto-healing': { label: 'Auto Healing', implemented: true, executable: true },
  approval: { label: 'Approval', implemented: true, executable: true },
  llm: { label: 'LLM', implemented: true, executable: true },
  'send-email': { label: 'Send Email', implemented: true, executable: true },
  condition: { label: 'Condition', implemented: true, executable: true },
  router: { label: 'Router', implemented: true, executable: true },
  extractor: { label: 'Extractor', implemented: true, executable: true },
  classifier: { label: 'Classifier', implemented: true, executable: true },
  summarizer: { label: 'Summarizer', implemented: false, executable: false },
  scheduler: { label: 'Scheduler', implemented: false, executable: false },
  webhook: { label: 'Webhook', implemented: false, executable: false },
  'file-upload': { label: 'File Upload', implemented: false, executable: false },
  'http-api': { label: 'HTTP API', implemented: false, executable: false },
  calendar: { label: 'Calendar', implemented: false, executable: false },
  database: { label: 'Database', implemented: false, executable: false },
};

export function getNodeCapability(kind?: string): NodeCapability {
  const normalizedKind = normalizeNodeKind(kind);
  if (!normalizedKind) {
    return { label: 'Unknown', implemented: false, executable: false };
  }

  return capabilities[normalizedKind] ?? {
    label: kind,
    implemented: false,
    executable: false,
  };
}

export function getExecutionEligibility(nodes: WorkflowNode[]) {
  const unsupportedNodeTypes = Array.from(
    new Set(
      nodes
        .map((node) => node.data.kind)
        .filter((kind): kind is string => Boolean(kind))
        .filter((kind) => !getNodeCapability(kind).implemented)
        .map((kind) => getNodeCapability(kind).label),
    ),
  );

  return {
    canExecute: nodes.length > 0 && unsupportedNodeTypes.length === 0,
    unsupportedNodeTypes,
  };
}
