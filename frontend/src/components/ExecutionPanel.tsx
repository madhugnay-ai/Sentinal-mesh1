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
  const nodeOutputs = result?.node_outputs?.filter((entry) => entry && typeof entry.outputs === 'object' && Object.keys(entry.outputs).length > 0) ?? [];
  const fallbackOutputs = [
    ...(result?.extracted_data ? [{ title: 'Extracted Data', value: result.extracted_data }] : []),
    ...(result?.classification ? [{ title: 'Classification', value: result.classification }] : []),
    ...(result?.summary ? [{ title: 'Summary', value: result.summary }] : []),
  ];

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
          {(nodeOutputs.length > 0 || fallbackOutputs.length > 0) ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
              <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Node Outputs</h4>
              {nodeOutputs.map((entry, index) => (
                <div key={`${entry.node_id ?? 'node'}-${index}`} className="mt-3 rounded-xl border border-slate-800/70 bg-slate-900/60 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {entry.node_type || 'Node'}
                    </p>
                    {entry.node_id ? (
                      <p className="text-[11px] uppercase tracking-wide text-slate-600">{entry.node_id}</p>
                    ) : null}
                  </div>
                  {Object.entries(entry.outputs).map(([key, value]) => (
                    <div key={key} className="mt-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{key}</p>
                      {typeof value === 'string' ? (
                        <p className="mt-2 text-sm text-slate-200">{value}</p>
                      ) : (
                        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-sm text-slate-200">
                          {JSON.stringify(value, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              ))}
              {nodeOutputs.length === 0
                ? fallbackOutputs.map((entry) => (
                    <div key={entry.title} className="mt-3 rounded-xl border border-slate-800/70 bg-slate-900/60 p-3">
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{entry.title}</p>
                      {typeof entry.value === 'string' ? (
                        <p className="mt-2 text-sm text-slate-200">{entry.value}</p>
                      ) : (
                        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-sm text-slate-200">
                          {JSON.stringify(entry.value, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))
                : null}
            </div>
          ) : null}
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
