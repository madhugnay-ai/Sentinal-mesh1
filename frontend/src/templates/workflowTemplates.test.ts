import { workflowTemplates } from './workflowTemplates';

declare function describe(name: string, fn: () => void): void;
declare function it(name: string, fn: () => void): void;
declare function expect(actual: unknown): { toEqual(expected: unknown): void };

const supportedKinds = new Set([
  'email-trigger',
  'llm',
  'send-email',
  'requirement-validation',
  'inventory',
  'vendor-selection',
  'budget-validation',
  'approval',
  'purchase-order',
  'supervisor',
  'failure-detection',
  'rag-incident-memory',
  'auto-healing',
]);

const supportedLabelsByKind: Record<string, string> = {
  'email-trigger': 'Email Trigger',
  llm: 'LLM',
  'send-email': 'Send Email',
  'requirement-validation': 'Requirement Validation',
  inventory: 'Inventory',
  'vendor-selection': 'Vendor Selection',
  'budget-validation': 'Budget Validation',
  approval: 'Approval',
  'purchase-order': 'Purchase Order',
  supervisor: 'Supervisor',
  'failure-detection': 'Failure Detection',
  'rag-incident-memory': 'RAG Incident Memory',
  'auto-healing': 'Auto Healing',
};

describe('workflow template node kind mappings', () => {
  it('uses consistent kinds for supported node labels', () => {
    const mismatches: string[] = [];

    workflowTemplates.forEach((template) => {
      template.nodes.forEach((node) => {
        const expectedLabel = supportedLabelsByKind[node.data.kind];
        if (supportedKinds.has(node.data.kind) && expectedLabel && node.data.label !== expectedLabel) {
          mismatches.push(`Template ${template.id} node ${node.id} has kind ${node.data.kind} but label ${node.data.label}`);
        }
      });
    });

    expect(mismatches).toEqual([]);
  });

  it('does not map unsupported visual nodes to implemented backend kinds', () => {
    const placeholderKinds = new Set([
      'scheduler',
      'webhook',
      'file-upload',
      'extractor',
      'classifier',
      'summarizer',
      'condition',
      'router',
      'loop',
      'calendar',
      'http-api',
      'database',
    ]);

    const badMappings: string[] = [];
    workflowTemplates.forEach((template) => {
      template.nodes.forEach((node) => {
        if (placeholderKinds.has(node.data.kind) && supportedKinds.has(node.data.kind)) {
          badMappings.push(`Template ${template.id} node ${node.id} maps placeholder kind ${node.data.kind} to a supported backend type`);
        }
      });
    });

    expect(badMappings).toEqual([]);
  });
});
