type TemplateExecutionDialogProps = {
  isOpen: boolean;
  onClose: () => void;
  unsupportedNodeTypes: string[];
};

function TemplateExecutionDialog({ isOpen, onClose, unsupportedNodeTypes }: TemplateExecutionDialogProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/80 px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/95 p-6 shadow-2xl">
        <h3 className="text-lg font-semibold text-white">Execution unavailable</h3>
        <p className="mt-3 text-sm leading-6 text-slate-300">
          Execution is unavailable until every node in the workflow has a backend implementation.
        </p>
        {unsupportedNodeTypes.length > 0 ? (
          <div className="mt-4 rounded-xl border border-slate-700 bg-slate-950/70 p-3">
            <p className="text-sm font-medium text-slate-200">The following node types are not yet implemented:</p>
            <ul className="mt-2 space-y-1 text-sm text-slate-300">
              {unsupportedNodeTypes.map((nodeType) => (
                <li key={nodeType} className="flex items-center gap-2">
                  <span className="text-cyan-400">•</span>
                  <span>{nodeType}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <button
          onClick={onClose}
          className="mt-5 rounded-xl bg-cyan-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-cyan-400"
        >
          Got it
        </button>
      </div>
    </div>
  );
}

export default TemplateExecutionDialog;
