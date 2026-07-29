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
  recipientEmail?: string;
  subject?: string;
  body?: string;
  useLlmOutput?: boolean;
  field?: string;
  operator?: string;
  value?: string;
  executionState?: 'waiting' | 'current' | 'success' | 'failed';
};

export type WorkflowNode = Node<WorkflowNodeData>;
export type WorkflowEdge = Edge;

export type WorkflowPayload = {
  name: string;
  description: string;
  nodes: Array<{
    id: string;
    type: string | undefined;
    position: { x: number; y: number };
    data: WorkflowNodeData;
  }>;
  edges: WorkflowEdge[];
};

export type WorkflowNodeField = 'label' | 'nodeType' | 'description' | 'config' | 'emailAccount' | 'folder' | 'unreadOnly' | 'subjectFilter' | 'gmailConnectionStatus' | 'provider' | 'model' | 'prompt' | 'temperature' | 'maxTokens' | 'recipientEmail' | 'subject' | 'body' | 'useLlmOutput' | 'field' | 'operator' | 'value';

export type WorkflowNodeValue = string | boolean | number;

export type WorkflowRecord = {
  workflow_id: string;
  name: string;
  description: string;
  nodes: WorkflowPayload['nodes'];
  edges: WorkflowEdge[];
  created_at: string;
  updated_at: string;
};

export type WorkflowExecutionResult = {
  execution_status: string;
  workflow_health: string;
  workflow_summary: string;
  completed_stages: string[];
  failed_stages: string[];
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
  execution_log: string[];
};
