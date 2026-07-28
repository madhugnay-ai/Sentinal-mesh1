type ExecutionLogProps = {
  executionLog: string[];
};

type LogTone = {
  icon: string;
  label: string;
  border: string;
  surface: string;
  dot: string;
};

function getLogTone(entry: string): LogTone {
  const text = entry.toLowerCase();

  if (/retrieved|workflow health|auto-healing|failure detected/.test(text)) {
    return {
      icon: 'ℹ️',
      label: 'Info',
      border: 'border-cyan-500/40',
      surface: 'bg-cyan-500/10',
      dot: 'bg-cyan-400',
    };
  }

  if (/failed|rejected|not generated|error/.test(text)) {
    return {
      icon: '❌',
      label: 'Failure',
      border: 'border-rose-500/40',
      surface: 'bg-rose-500/10',
      dot: 'bg-rose-400',
    };
  }

  if (/passed|completed|approved|generated|healthy/.test(text)) {
    return {
      icon: '✅',
      label: 'Success',
      border: 'border-emerald-500/40',
      surface: 'bg-emerald-500/10',
      dot: 'bg-emerald-400',
    };
  }

  return {
    icon: 'ℹ️',
    label: 'Info',
    border: 'border-cyan-500/40',
    surface: 'bg-cyan-500/10',
    dot: 'bg-cyan-400',
  };
}

function formatLogEntry(entry: string) {
  const timestampMatch = entry.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)/);

  if (!timestampMatch) {
    return {
      timestampText: null,
      tooltipText: null,
      message: entry,
    };
  }

  const rawTimestamp = timestampMatch[1];
  const parsedTimestamp = new Date(rawTimestamp);

  if (Number.isNaN(parsedTimestamp.getTime())) {
    return {
      timestampText: null,
      tooltipText: null,
      message: entry,
    };
  }

  const timeText = parsedTimestamp.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
  const dateText = parsedTimestamp.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

  return {
    timestampText: timeText,
    tooltipText: dateText,
    message: entry.replace(rawTimestamp, '').trim(),
  };
}

function ExecutionLog({ executionLog }: ExecutionLogProps) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 shadow-xl sm:p-5">
      <h3 className="mb-4 text-lg font-semibold text-slate-100">Execution Log</h3>
      <div className="max-h-96 overflow-y-auto pr-1">
        {executionLog.length ? (
          <div className="relative ml-1 space-y-3">
            <div className="absolute left-[1.05rem] top-0 h-full w-px bg-slate-800" />
            {executionLog.map((entry, index) => {
              const tone = getLogTone(entry);
              const { timestampText, tooltipText, message } = formatLogEntry(entry);

              return (
                <div key={`${entry}-${index}`} className={`relative flex items-start gap-3 rounded-2xl border px-3 py-3 ${tone.border} ${tone.surface}`}>
                  <div className={`mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${tone.dot} text-sm`}>
                    {tone.icon}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[11px] font-semibold uppercase tracking-[0.25em] text-slate-400">{tone.label}</span>
                      {timestampText ? (
                        <span className="text-xs text-slate-400" title={tooltipText ?? undefined}>
                          {timestampText}
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-1 text-sm leading-6 text-slate-200">{message || entry}</p>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-3 text-slate-400">No execution log available.</div>
        )}
      </div>
    </div>
  );
}

export default ExecutionLog;
