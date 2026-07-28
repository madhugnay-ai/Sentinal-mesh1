import type { WorkflowEdge, WorkflowNode } from '../types/workflow';

export type WorkflowTemplate = {
  id: string;
  name: string;
  description: string;
  icon: string;
  comingSoon?: boolean;
  executable?: boolean;
  initialName?: string;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
};

function createNode(
  id: string,
  kind: string,
  label: string,
  nodeType: string,
  description: string,
  config: string,
  position: { x: number; y: number },
): WorkflowNode {
  return {
    id,
    type: 'workflowNode',
    position,
    data: {
      label,
      nodeType,
      description,
      config,
      kind,
    },
  };
}

const procurementNodes: WorkflowNode[] = [
  createNode(
    'requirement-validation-1',
    'requirement-validation',
    'Requirement Validation',
    'Requirement Validation',
    'Validate incoming requirements before proceeding.',
    'Rule: must include business owner',
    { x: 80, y: 80 },
  ),
  createNode(
    'approval-1',
    'approval',
    'Approval',
    'Approval',
    'Review and authorize the request.',
    'Approver: Finance Lead',
    { x: 360, y: 220 },
  ),
];

const procurementEdges: WorkflowEdge[] = [{ id: 'e1', source: 'requirement-validation-1', target: 'approval-1' }];

function createTemplateNodes(nodes: WorkflowNode[]) {
  return nodes;
}

function createTemplateEdges(edges: WorkflowEdge[]) {
  return edges;
}

export const workflowTemplates: WorkflowTemplate[] = [
  {
    id: 'procurement',
    name: 'Procurement Workflow',
    description: 'The existing multi-step procurement flow with validation and approval.',
    icon: '📦',
    executable: true,
    initialName: 'Procurement Workflow',
    nodes: procurementNodes,
    edges: procurementEdges,
  },
  {
    id: 'bakery',
    name: 'Bakery Order Automation',
    description: 'Coordinate incoming orders, baking prep, and delivery scheduling.',
    icon: '🍞',
    executable: false,
    initialName: 'Bakery Order Automation',
    nodes: createTemplateNodes([
      createNode('bakery-trigger', 'email-trigger', 'Email Trigger', 'Email Trigger', 'Receive incoming order requests from customers.', 'Starts the bakery workflow', { x: 80, y: 80 }),
      createNode('bakery-extractor', 'extractor', 'Order Extractor', 'Order Extractor', 'Extract product quantities and delivery details.', 'Parses the incoming order data', { x: 320, y: 80 }),
      createNode('bakery-inventory', 'inventory', 'Inventory Check', 'Inventory Check', 'Validate ingredients and stock availability.', 'Checks the bakery supply inventory', { x: 560, y: 80 }),
      createNode('bakery-schedule', 'scheduler', 'Schedule Baking', 'Schedule Baking', 'Plan production and baking windows.', 'Coordinates oven schedule and preparation', { x: 800, y: 80 }),
      createNode('bakery-confirmation', 'send-email', 'Send Confirmation Email', 'Send Confirmation Email', 'Notify the customer that the order is confirmed.', 'Sends the final order confirmation', { x: 1040, y: 80 }),
    ]),
    edges: createTemplateEdges([
      { id: 'bakery-e1', source: 'bakery-trigger', target: 'bakery-extractor' },
      { id: 'bakery-e2', source: 'bakery-extractor', target: 'bakery-inventory' },
      { id: 'bakery-e3', source: 'bakery-inventory', target: 'bakery-schedule' },
      { id: 'bakery-e4', source: 'bakery-schedule', target: 'bakery-confirmation' },
    ]),
  },
  {
    id: 'hr',
    name: 'HR Resume Screening',
    description: 'Route resumes through intake, screening, and interview coordination.',
    icon: '👨‍💼',
    executable: false,
    initialName: 'HR Resume Screening',
    nodes: createTemplateNodes([
      createNode('hr-upload', 'file-upload', 'Resume Upload', 'Resume Upload', 'Collect submitted resumes from candidates.', 'Receives candidate application files', { x: 80, y: 260 }),
      createNode('hr-parser', 'extractor', 'Resume Parser', 'Resume Parser', 'Extract structured data from each resume.', 'Parses education and experience details', { x: 320, y: 260 }),
      createNode('hr-skill', 'classifier', 'Skill Matcher', 'Skill Matcher', 'Compare candidate skills with role requirements.', 'Matches qualifications to the role', { x: 560, y: 260 }),
      createNode('hr-ranking', 'approval', 'Candidate Ranking', 'Candidate Ranking', 'Rank candidates by fit and experience.', 'Produces a ranked shortlist', { x: 800, y: 260 }),
      createNode('hr-notify', 'send-email', 'Notify HR', 'Notify HR', 'Alert the recruiting team about the shortlist.', 'Sends the shortlist to HR', { x: 1040, y: 260 }),
    ]),
    edges: createTemplateEdges([
      { id: 'hr-e1', source: 'hr-upload', target: 'hr-parser' },
      { id: 'hr-e2', source: 'hr-parser', target: 'hr-skill' },
      { id: 'hr-e3', source: 'hr-skill', target: 'hr-ranking' },
      { id: 'hr-e4', source: 'hr-ranking', target: 'hr-notify' },
    ]),
  },
  {
    id: 'email',
    name: 'Email Processing',
    description: 'Automate triage and routing for incoming customer email requests.',
    icon: '📧',
    executable: false,
    initialName: 'Email Processing',
    nodes: createTemplateNodes([
      createNode('email-trigger', 'email-trigger', 'Email Trigger', 'Email Trigger', 'Receive a new inbound email.', 'Starts the email processing flow', { x: 80, y: 450 }),
      createNode('email-classifier', 'classifier', 'Email Classifier', 'Email Classifier', 'Identify whether the email is a request, complaint, or follow-up.', 'Classifies the intent of the incoming email', { x: 320, y: 450 }),
      createNode('email-route', 'router', 'Route Email', 'Route Email', 'Send the email to the correct team or queue.', 'Routes the message to the appropriate workflow', { x: 560, y: 450 }),
      createNode('email-reply', 'send-email', 'Auto Reply', 'Auto Reply', 'Send an acknowledgement or next-step message.', 'Generates the auto response', { x: 800, y: 450 }),
    ]),
    edges: createTemplateEdges([
      { id: 'email-e1', source: 'email-trigger', target: 'email-classifier' },
      { id: 'email-e2', source: 'email-classifier', target: 'email-route' },
      { id: 'email-e3', source: 'email-route', target: 'email-reply' },
    ]),
  },
  {
    id: 'support',
    name: 'Customer Support',
    description: 'Handle support tickets with triage, escalation, and resolution steps.',
    icon: '💬',
    executable: false,
    initialName: 'Customer Support',
    nodes: createTemplateNodes([
      createNode('support-email', 'email-trigger', 'Customer Email', 'Customer Email', 'Receive the customer support request.', 'Starts the support workflow', { x: 80, y: 640 }),
      createNode('support-intent', 'classifier', 'Intent Detection', 'Intent Detection', 'Detect the customer intent and issue category.', 'Assigns the issue category', { x: 320, y: 640 }),
      createNode('support-kb', 'extractor', 'Knowledge Base', 'Knowledge Base', 'Look up relevant support guidance.', 'Finds the best known-answer content', { x: 560, y: 640 }),
      createNode('support-response', 'llm', 'Generate Response', 'Generate Response', 'Compose a reply that addresses the request.', 'Generates the draft support reply', { x: 800, y: 640 }),
      createNode('support-send', 'send-email', 'Send Reply', 'Send Reply', 'Deliver the final response to the customer.', 'Sends the support reply', { x: 1040, y: 640 }),
    ]),
    edges: createTemplateEdges([
      { id: 'support-e1', source: 'support-email', target: 'support-intent' },
      { id: 'support-e2', source: 'support-intent', target: 'support-kb' },
      { id: 'support-e3', source: 'support-kb', target: 'support-response' },
      { id: 'support-e4', source: 'support-response', target: 'support-send' },
    ]),
  },
  {
    id: 'blank',
    name: 'Blank Workflow',
    description: 'Start from a clean canvas for a new process design.',
    icon: '➕',
    executable: false,
    initialName: 'Blank Workflow',
    nodes: [],
    edges: [],
  },
];
