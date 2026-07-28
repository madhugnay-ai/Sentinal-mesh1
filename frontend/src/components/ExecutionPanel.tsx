import WorkflowHealthCard from './WorkflowHealthCard';
import IncidentPanel from './IncidentPanel';
import HealingPanel from './HealingPanel';
import ExecutionLog from './ExecutionLog';
import type { WorkflowExecutionResult } from '../types/workflow';

type ExecutionPanelProps = {
  result: WorkflowExecutionResult | null;
  isExecuting: boolean;
  errorMessage: string | null;
};

function ExecutionPanel({ result, isExecuting, errorMessage }: ExecutionPanelProps) {
  return (
    <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-xl sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="text-lg font-semibold text-slate-100">Execution Results</h3>
        {isExecuting ? (
          <div className="flex items-center gap-2 rounded-full bg-cyan-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-cyan-300">
            <span className="h-3 w-3 animate-spin rounded-full border-2 border-cyan-300 border-t-transparent" />
            Executing...
          </div>
        ) : null}
      </div>

      {errorMessage ? (
        <div className="rounded-xl border border-rose-700 bg-rose-500/10 px-3 py-3 text-sm text-rose-200">{errorMessage}</div>
      ) : null}

      {result ? (
        <div className="space-y-4">
          <WorkflowHealthCard result={result} />
          <IncidentPanel result={result} />
          <HealingPanel result={result} />
          <ExecutionLog executionLog={result.execution_log} />
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-800 bg-slate-950/70 px-4 py-4 text-sm text-slate-400">
          Execute a workflow to view status, health, incidents, and healing guidance.
        </div>
      )}
    </div>
  );
}

export default ExecutionPanel;
