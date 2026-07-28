import type { WorkflowExecutionResult } from '../types/workflow';

type HealingPanelProps = {
  result: WorkflowExecutionResult;
};

const healingStatusStyles: Record<string, string> = {
  Recommended: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
  'Not Required': 'bg-slate-500/15 text-slate-300 border-slate-500/40',
  'Not Recommended': 'bg-rose-500/15 text-rose-300 border-rose-500/40',
};

function HealingPanel({ result }: HealingPanelProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 shadow-xl sm:p-5">
      <h3 className="mb-4 text-lg font-semibold text-slate-100">Healing Recommendation</h3>
      <div className="space-y-3 text-sm text-slate-300">
        <div className="rounded-2xl bg-slate-900/80 p-4">
          <div className="mb-2 text-xs uppercase tracking-wide text-slate-500">Recommended Resolution</div>
          <div className="text-base font-medium text-slate-100">{result.recommended_resolution}</div>
        </div>

        <div className="rounded-2xl bg-slate-900/80 p-4">
          <div className="mb-2 text-xs uppercase tracking-wide text-slate-500">Healing Strategy</div>
          <span className="inline-flex rounded-full border border-violet-500/40 bg-violet-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-violet-300">
            {result.healing_strategy}
          </span>
        </div>

        <div className="rounded-2xl bg-slate-900/80 p-4">
          <div className="mb-2 text-xs uppercase tracking-wide text-slate-500">Healing Status</div>
          <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${healingStatusStyles[result.healing_status] ?? 'bg-slate-500/15 text-slate-300 border-slate-500/40'}`}>
            {result.healing_status}
          </span>
        </div>
      </div>
    </div>
  );
}

export default HealingPanel;
