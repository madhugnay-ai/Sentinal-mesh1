import type { Edge, Node } from 'reactflow';

export type WorkflowNodeData = {
  label: string;
  nodeType: string;
  description: string;
  config: string;
  kind: string;
  emailAccount?: string;
  folder?: string;
  unreadOnly?: boolean;
  subjectFilter?: string;
  gmailConnected?: boolean;
  gmailConnectionStatus?: string;
  provider?: string;
  model?: string;
  prompt?: string;
  temperature?: number;
  maxTokens?: number;
  inputField?: string;
  categories?: string[];
  extractionFields?: string[];
  instructions?: string;
  recipientEmail?: string;
  subject?: string;
  body?: string;
  useLlmOutput?: boolean;
  field?: string;
  operator?: string;
  value?: string;
  defaultRoute?: string;
  routes?: Array<{ route: string; operator: string; value: string }>;
  executionState?: 'waiting' | 'current' | 'success' | 'failed';
};

export type WorkflowNode = Node<WorkflowNodeData>;
export type WorkflowEdge = Edge;

export type WorkflowPayload = {
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
};

export type WorkflowNodeField =
  | 'label'
  | 'nodeType'
  | 'description'
  | 'config'
  | 'emailAccount'
  | 'folder'
  | 'unreadOnly'
  | 'subjectFilter'
  | 'gmailConnectionStatus'
  | 'provider'
  | 'model'
  | 'prompt'
  | 'temperature'
  | 'maxTokens'
  | 'inputField'
  | 'categories'
  | 'extractionFields'
  | 'instructions'
  | 'recipientEmail'
  | 'subject'
  | 'body'
  | 'useLlmOutput'
  | 'field'
  | 'operator'
  | 'value'
  | 'defaultRoute'
  | 'routes';

export type WorkflowNodeValue = string | boolean | number | string[] | Array<Record<string, string>>;

export type WorkflowRecord = {
  workflow_id: string;
  name: string;
  description: string;
  nodes: WorkflowPayload['nodes'];
  edges: WorkflowEdge[];
  created_at: string;
  updated_at: string;
};

export type SavedWorkflow = {
  id: string;
  name: string;
  description: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  createdAt?: string;
  updatedAt?: string;
};

export type WorkflowStorageEnvelope = {
  currentWorkflowId: string | null;
  workflows: SavedWorkflow[];
};

export type WorkflowExecutionResult = {
  execution_status: string;
  workflow_health: string;
  workflow_summary: string;
  completed_stages: string[];
  failed_stages: string[];
  skipped_stages?: string[];
  executed_node_ids?: string[];
  failed_node_ids?: string[];
  skipped_node_ids?: string[];
  current_node_id?: string | null;
  failure_category?: string;
  failure_severity?: string;
  incident_matches: Array<{
    incident_id?: string;
    failure_category: string;
    severity: string;
    root_cause?: string;
    resolution?: string;
    recommended_action?: string;
  }>;
  recommended_resolution: string;
  healing_strategy: string;
  healing_status: string;
  node_outputs?: Array<{
    node_id?: string | null;
    node_type?: string;
    outputs: Record<string, unknown>;
  }>;
  classification?: string | null;
  extracted_data?: Record<string, unknown> | null;
  summary?: string | null;
  execution_log: string[];
};
