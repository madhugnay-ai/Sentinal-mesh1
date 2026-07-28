import type { DragEvent } from 'react';

type NodeLibraryNode = {
  id: string;
  label: string;
  description: string;
};

type NodeLibraryCategoryProps = {
  title: string;
  icon: string;
  nodes: NodeLibraryNode[];
  isExpanded: boolean;
  onToggle: () => void;
  onAddNode: (type: string) => void;
  onDragStart: (event: DragEvent<HTMLButtonElement>, type: string) => void;
};

function NodeLibraryCategory({ title, icon, nodes, isExpanded, onToggle, onAddNode, onDragStart }: NodeLibraryCategoryProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between rounded-2xl px-3 py-3 text-left transition hover:bg-slate-800/70"
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-slate-100">
          <span className="text-base">{icon}</span>
          {title}
        </span>
        <span className="text-sm text-slate-400 transition-transform duration-200" style={{ transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)' }}>
          ▶
        </span>
      </button>

      <div className="overflow-hidden transition-[max-height,opacity] duration-300" style={{ maxHeight: isExpanded ? '420px' : '0px', opacity: isExpanded ? 1 : 0 }}>
        <div className="space-y-2 border-t border-slate-800 px-3 pb-3 pt-2">
          {nodes.map((node) => (
            <button
              key={node.id}
              draggable
              onClick={() => onAddNode(node.id)}
              onDragStart={(event) => onDragStart(event, node.id)}
              className="w-full rounded-xl border border-slate-700 bg-slate-900/80 p-3 text-left transition duration-200 hover:-translate-y-0.5 hover:border-cyan-400 hover:bg-slate-800"
            >
              <div className="font-medium text-slate-100">{node.label}</div>
              <div className="mt-1 text-xs text-slate-400">{node.description}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default NodeLibraryCategory;
