import type { WorkflowExecutionResult } from '../types/workflow';

type IncidentPanelProps = {
  result: WorkflowExecutionResult;
};

const severityBadgeStyles: Record<string, string> = {
  Critical: 'bg-rose-500/15 text-rose-300 border-rose-500/40',
  High: 'bg-orange-500/15 text-orange-300 border-orange-500/40',
  Medium: 'bg-amber-500/15 text-amber-300 border-amber-500/40',
  Low: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40',
};

function IncidentPanel({ result }: IncidentPanelProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 shadow-xl sm:p-5">
      <h3 className="mb-4 text-lg font-semibold text-slate-100">Incident Matches</h3>
      <div className="space-y-3 text-sm text-slate-300">
        {result.incident_matches.length ? (
          result.incident_matches.map((incident, index) => (
            <div key={`${incident.incident_id ?? 'incident'}-${index}`} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
              <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="text-base font-semibold text-cyan-300">{incident.incident_id ?? `Incident ${index + 1}`}</div>
                <span className={`inline-flex w-fit rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${severityBadgeStyles[incident.severity] ?? 'bg-slate-500/15 text-slate-300 border-slate-500/40'}`}>
                  {incident.severity}
                </span>
              </div>

              <div className="grid gap-2 text-sm sm:grid-cols-2">
                <div className="rounded-xl bg-slate-950/70 px-3 py-2">
                  <div className="text-xs uppercase tracking-wide text-slate-500">Failure Category</div>
                  <div className="mt-1 font-medium text-slate-100">{incident.failure_category}</div>
                </div>

                <div className="rounded-xl bg-slate-950/70 px-3 py-2">
                  <div className="text-xs uppercase tracking-wide text-slate-500">Severity</div>
                  <div className="mt-1 font-medium text-slate-100">{incident.severity}</div>
                </div>

                <div className="rounded-xl bg-slate-950/70 px-3 py-2 sm:col-span-2">
                  <div className="text-xs uppercase tracking-wide text-slate-500">Root Cause</div>
                  <div className="mt-1 font-medium text-slate-100">{incident.root_cause ?? 'Not provided'}</div>
                </div>

                <div className="rounded-xl bg-slate-950/70 px-3 py-2 sm:col-span-2">
                  <div className="text-xs uppercase tracking-wide text-slate-500">Recommended Action</div>
                  <div className="mt-1 font-medium text-slate-100">{incident.recommended_action ?? incident.resolution ?? 'Not provided'}</div>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-slate-400">No incident matches found.</div>
        )}
      </div>
    </div>
  );
}

export default IncidentPanel;
