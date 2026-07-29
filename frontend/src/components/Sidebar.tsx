import { useState, type DragEvent } from 'react';
import NodeLibraryCategory from './NodeLibraryCategory';

type NodeTemplate = {
  id: string;
  label: string;
  description: string;
};

type SidebarProps = {
  onAddNode: (type: string) => void;
};

type CategoryDefinition = {
  id: string;
  title: string;
  icon: string;
  nodes: NodeTemplate[];
};

const categories: CategoryDefinition[] = [
  {
    id: 'triggers',
    title: 'Triggers',
    icon: '📥',
    nodes: [
      { id: 'email-trigger', label: 'Email Trigger', description: 'Start from inbound email' },
      { id: 'scheduler', label: 'Scheduler', description: 'Run on a schedule' },
      { id: 'webhook', label: 'Webhook', description: 'Accept incoming webhooks' },
      { id: 'file-upload', label: 'File Upload', description: 'Start from uploaded files' },
    ],
  },
  {
    id: 'ai',
    title: 'AI',
    icon: '🤖',
    nodes: [
      { id: 'llm', label: 'LLM', description: 'Generate or reason with AI' },
      { id: 'extractor', label: 'Extractor', description: 'Extract structured data' },
      { id: 'classifier', label: 'Classifier', description: 'Classify content semantically with AI' },
      { id: 'summarizer', label: 'Summarizer', description: 'Condense long content' },
    ],
  },
  {
    id: 'logic',
    title: 'Logic',
    icon: '🔀',
    nodes: [
      { id: 'condition', label: 'Condition', description: 'Branch on a rule' },
      { id: 'router', label: 'Router', description: 'Route to multiple paths' },
      { id: 'loop', label: 'Loop', description: 'Repeat until complete' },
    ],
  },
  {
    id: 'integrations',
    title: 'Integrations',
    icon: '🔧',
    nodes: [
      { id: 'send-email', label: 'Send Email', description: 'Send an SMTP email from workflow output' },
      { id: 'calendar', label: 'Calendar', description: 'Create calendar events' },
      { id: 'http-api', label: 'HTTP API', description: 'Call external APIs' },
      { id: 'database', label: 'Database', description: 'Read or write data' },
    ],
  },
  {
    id: 'human',
    title: 'Human',
    icon: '👤',
    nodes: [{ id: 'approval', label: 'Approval', description: 'Route for approval' }],
  },
  {
    id: 'monitoring',
    title: 'Monitoring',
    icon: '📊',
    nodes: [
      { id: 'supervisor', label: 'Supervisor', description: 'Monitor workflow health' },
      { id: 'failure-detection', label: 'Failure Detection', description: 'Detect workflow failures' },
      { id: 'rag-incident-memory', label: 'RAG Incident Memory', description: 'Recall prior incidents' },
      { id: 'auto-healing', label: 'Auto Healing', description: 'Recover from issues' },
    ],
  },
  {
    id: 'procurement',
    title: 'Procurement',
    icon: '📦',
    nodes: [
      { id: 'requirement-validation', label: 'Requirement Validation', description: 'Validate incoming requirements' },
      { id: 'inventory', label: 'Inventory', description: 'Review current inventory' },
      { id: 'vendor-selection', label: 'Vendor Selection', description: 'Select the best vendor' },
      { id: 'budget-validation', label: 'Budget Validation', description: 'Validate cost constraints' },
      { id: 'purchase-order', label: 'Purchase Order', description: 'Create purchase order' },
    ],
  },
];

function Sidebar({ onAddNode }: SidebarProps) {
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({
    triggers: true,
    ai: true,
    logic: true,
    integrations: true,
    human: true,
    monitoring: true,
    procurement: true,
  });

  const handleToggle = (categoryId: string) => {
    setExpandedCategories((current) => ({ ...current, [categoryId]: !current[categoryId] }));
  };

  const handleDragStart = (event: DragEvent<HTMLButtonElement>, type: string) => {
    event.dataTransfer.setData('application/reactflow', type);
    event.dataTransfer.effectAllowed = 'copy';
  };

  return (
    <aside className="h-full w-full shrink-0 rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-xl">
      <h3 className="text-lg font-medium">Node Library</h3>
      <p className="mt-2 text-sm text-slate-400">Drag a node type into the canvas to begin.</p>
      <div className="mt-4 space-y-3">
        {categories.map((category) => (
          <NodeLibraryCategory
            key={category.id}
            title={category.title}
            icon={category.icon}
            nodes={category.nodes}
            isExpanded={expandedCategories[category.id] ?? true}
            onToggle={() => handleToggle(category.id)}
            onAddNode={onAddNode}
            onDragStart={handleDragStart}
          />
        ))}
      </div>
    </aside>
  );
}

export default Sidebar;
