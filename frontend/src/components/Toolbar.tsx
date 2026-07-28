type ToolbarProps = {
  onSave: () => void;
  onLoad: () => void;
  onExport: () => void;
  onClear: () => void;
  onExecute: () => void;
  onOpenTemplates: () => void;
};

function Toolbar({ onSave, onLoad, onExport, onClear, onExecute, onOpenTemplates }: ToolbarProps) {
  return (
    <div className="flex flex-wrap gap-2">
      <button onClick={onSave} className="rounded-xl bg-cyan-500 px-4 py-2 font-medium text-slate-950 transition hover:bg-cyan-400">Save Workflow</button>
      <button onClick={onLoad} className="rounded-xl bg-slate-800 px-4 py-2 font-medium text-slate-100 transition hover:bg-slate-700">Load Workflow</button>
      <button onClick={onOpenTemplates} className="rounded-xl border border-cyan-500/40 bg-cyan-500/10 px-4 py-2 font-medium text-cyan-200 transition hover:bg-cyan-500/20">Templates</button>
      <button onClick={onExecute} className="rounded-xl bg-violet-600 px-4 py-2 font-medium text-white transition hover:bg-violet-500">Execute Workflow</button>
      <button onClick={onExport} className="rounded-xl bg-emerald-600 px-4 py-2 font-medium text-white transition hover:bg-emerald-500">Export JSON</button>
      <button onClick={onClear} className="rounded-xl bg-rose-600 px-4 py-2 font-medium text-white transition hover:bg-rose-500">Clear Canvas</button>
    </div>
  );
}

export default Toolbar;
