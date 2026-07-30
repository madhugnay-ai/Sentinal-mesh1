import type { WorkflowExecutionResult } from '../types/workflow';

type WorkflowHealthCardProps = {
  result: WorkflowExecutionResult;
};

const healthBadgeStyles: Record<string, string> = {
  Healthy: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
  Warning: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
  Failed: 'bg-rose-500/15 text-rose-300 border-rose-500/40',
  Running: 'bg-sky-500/15 text-sky-300 border-sky-500/40',
};

const executionStatusStyles: Record<string, string> = {
  validated: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
  approved: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
  generated: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
  failed: 'bg-rose-500/15 text-rose-300 border-rose-500/40',
  rejected: 'bg-rose-500/15 text-rose-300 border-rose-500/40',
  running: 'bg-sky-500/15 text-sky-300 border-sky-500/40',
  pending: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
  pending_manager_approval: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
};

function getStatusIcon(status: string) {
  if (status === 'Healthy') return '✓';
  if (status === 'Warning') return '⚠';
  if (status === 'Failed') return '✕';
  if (status === 'Running') return '↻';
  return '•';
}

function getExecutionStatusIcon(status: string) {
  if (status === 'validated' || status === 'approved' || status === 'generated') return '✓';
  if (status === 'failed' || status === 'rejected') return '✕';
  if (status === 'running' || status === 'pending') return '↻';
  if (status === 'pending_manager_approval') return '⚠';
  return '•';
}

function WorkflowHealthCard({ result }: WorkflowHealthCardProps) {
  const firstIncident = result.incident_matches[0];
  const healthClass = healthBadgeStyles[result.workflow_health] ?? 'bg-slate-500/15 text-slate-300 border-slate-500/40';
  const executionClass = executionStatusStyles[result.execution_status] ?? 'bg-slate-500/15 text-slate-300 border-slate-500/40';
  const totalStages = result.completed_stages.length + result.failed_stages.length + (result.skipped_stages?.length ?? 0);
  const progressPercent = totalStages === 0 ? 0 : Math.round((result.completed_stages.length / totalStages) * 100);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 shadow-xl transition duration-200 hover:border-cyan-500/40 hover:shadow-2xl sm:p-5">
      <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-400">Monitoring Overview</p>
          <h3 className="mt-2 text-lg font-semibold text-slate-100">Workflow Health</h3>
        </div>
        <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${healthClass}`}>
          <span>{getStatusIcon(result.workflow_health)}</span>
          {result.workflow_health}
        </span>
      </div>

      <div className="grid gap-3 lg:grid-cols-4">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3 transition hover:-translate-y-0.5 hover:border-cyan-500/40">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-slate-400">
            <span className="text-base">🧭</span>
            Workflow Health
          </div>
          <div className="mt-3 text-2xl font-semibold text-slate-100">{result.workflow_health}</div>
          <div className={`mt-3 inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold ${healthClass}`}>
            <span>{getStatusIcon(result.workflow_health)}</span>
            {result.workflow_health}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3 transition hover:-translate-y-0.5 hover:border-cyan-500/40">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-slate-400">
            <span className="text-base">⚙️</span>
            Execution Status
          </div>
          <div className="mt-3 text-2xl font-semibold text-slate-100">{result.execution_status}</div>
          <div className={`mt-3 inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold ${executionClass}`}>
            <span>{getExecutionStatusIcon(result.execution_status)}</span>
            {result.execution_status}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3 transition hover:-translate-y-0.5 hover:border-cyan-500/40">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-slate-400">
            <span className="text-base">🚨</span>
            Severity
          </div>
          <div className="mt-3 text-2xl font-semibold text-slate-100">{firstIncident?.severity ?? result.failure_severity ?? 'None'}</div>
          <div className="mt-3 text-xs text-slate-500">Latest incident signal</div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3 transition hover:-translate-y-0.5 hover:border-cyan-500/40">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.25em] text-slate-400">
            <span className="text-base">🧩</span>
            Failure Category
          </div>
          <div className="mt-3 text-2xl font-semibold text-slate-100">{firstIncident?.failure_category ?? result.failure_category ?? 'None'}</div>
          <div className="mt-3 text-xs text-slate-500">Detected issue class</div>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-slate-200">Stage Progress</p>
            <p className="text-xs text-slate-400">Completed vs failed workflow stages</p>
          </div>
          <div className="text-sm font-semibold text-slate-100">{progressPercent}%</div>
        </div>

        <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800">
          <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500" style={{ width: `${progressPercent}%` }} />
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <div className="text-xs uppercase tracking-[0.25em] text-slate-400">Completed Stages</div>
            <div className="mt-2 text-sm text-slate-100">{result.completed_stages.length}</div>
            <div className="mt-3 flex flex-wrap gap-2">
              {result.completed_stages.length ? (
                result.completed_stages.map((stage) => (
                  <span key={stage} className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-300">
                    {stage}
                  </span>
                ))
              ) : (
                <span className="rounded-full border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-400">None</span>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <div className="text-xs uppercase tracking-[0.25em] text-slate-400">Failed Stages</div>
            <div className="mt-2 text-sm text-slate-100">{result.failed_stages.length}</div>
            <div className="mt-3 flex flex-wrap gap-2">
              {result.failed_stages.length ? (
                result.failed_stages.map((stage) => (
                  <span key={stage} className="rounded-full border border-rose-500/40 bg-rose-500/10 px-2.5 py-1 text-xs font-medium text-rose-300">
                    {stage}
                  </span>
                ))
              ) : (
                <span className="rounded-full border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-400">None</span>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
            <div className="text-xs uppercase tracking-[0.25em] text-slate-400">Total Stages</div>
            <div className="mt-2 text-sm text-slate-100">{totalStages}</div>
            <div className="mt-3 text-xs text-slate-500">Progress is based on completed stages over total observed stages.</div>
          </div>
        </div>
      </div>

      <div className="mt-5 rounded-2xl border border-slate-800/80 bg-slate-900/70 p-4">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-200">
          <span className="text-base">ℹ️</span>
          Workflow Summary
        </div>
        <p className="mt-3 text-sm leading-6 text-slate-300">{result.workflow_summary}</p>
      </div>
    </div>
  );
}

export default WorkflowHealthCard;
