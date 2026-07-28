import { Handle, Position, type NodeProps } from 'reactflow';
import type { WorkflowNodeData } from '../types/workflow';

const palette: Record<string, { color: string; icon: string }> = {
  'requirement-validation': { color: 'from-cyan-500 to-sky-600', icon: '✓' },
  inventory: { color: 'from-violet-500 to-indigo-600', icon: '▣' },
  'vendor-selection': { color: 'from-amber-500 to-orange-600', icon: '⛭' },
  'budget-validation': { color: 'from-emerald-500 to-green-600', icon: '$' },
  approval: { color: 'from-fuchsia-500 to-pink-600', icon: '⚑' },
  'purchase-order': { color: 'from-rose-500 to-red-600', icon: '⟡' },
  'email-trigger': { color: 'from-blue-500 to-cyan-600', icon: '✉' },
};

function WorkflowNode({ data, selected }: NodeProps<WorkflowNodeData>) {
  const style = palette[data.kind] ?? palette['requirement-validation'];
  const executionState = data.executionState ?? 'waiting';
  const stateClasses: Record<NonNullable<WorkflowNodeData['executionState']>, string> = {
    waiting: 'border-slate-700 bg-slate-900/95',
    current: 'border-cyan-400 bg-cyan-500/10 shadow-[0_0_0_1px_rgba(34,211,238,0.25),0_0_24px_rgba(34,211,238,0.2)] animate-pulse',
    success: 'border-emerald-400/70 bg-emerald-500/10',
    failed: 'border-rose-400/70 bg-rose-500/10',
  };

  const stateBadge = {
    waiting: 'Waiting',
    current: 'Running',
    success: 'Completed',
    failed: 'Failed',
  }[executionState as NonNullable<WorkflowNodeData['executionState']>] ?? 'Waiting';

  return (
    <div
      className={`min-w-[220px] rounded-2xl border p-3 shadow-xl ${stateClasses[executionState]} ${selected ? 'ring-2 ring-cyan-400' : ''}`}
    >
      <Handle type="target" position={Position.Left} className="!bg-cyan-400" />
      <div className="flex items-center justify-between gap-2">
        <div className={`rounded-xl bg-gradient-to-r ${style.color} px-3 py-2 text-sm font-semibold text-white`}>
          <div className="flex items-center gap-2">
            <span className="text-base">{style.icon}</span>
            <span>{data.label}</span>
          </div>
        </div>
        <span className="rounded-full border border-slate-700 bg-slate-950/70 px-2 py-1 text-[10px] uppercase tracking-[0.24em] text-slate-300">
          {stateBadge}
        </span>
      </div>
      <div className="mt-2 text-sm text-slate-300">
        <p className="font-medium text-slate-200">{data.nodeType}</p>
        <p className="mt-1 text-xs text-slate-400">{data.description}</p>
        <p className="mt-2 rounded-lg bg-slate-800/80 px-2 py-1 text-[11px] text-slate-300">{data.config}</p>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-cyan-400" />
    </div>
  );
}

export default WorkflowNode;
