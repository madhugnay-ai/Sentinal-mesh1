import type { WorkflowTemplate } from '../templates/workflowTemplates';

type TemplateGalleryModalProps = {
  isOpen: boolean;
  onClose: () => void;
  onSelectTemplate: (template: WorkflowTemplate) => void;
  templates: WorkflowTemplate[];
};

function TemplateGalleryModal({ isOpen, onClose, onSelectTemplate, templates }: TemplateGalleryModalProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/85 px-3 py-6 backdrop-blur-sm">
      <div className="w-full max-w-5xl rounded-3xl border border-slate-800 bg-slate-900/95 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4 sm:px-6">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-cyan-400">Templates</p>
            <h2 className="mt-1 text-xl font-semibold text-white">Choose a workflow template</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-full border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-300 transition hover:border-slate-500 hover:bg-slate-700"
          >
            Close
          </button>
        </div>

        <div className="grid gap-4 p-4 sm:grid-cols-2 lg:grid-cols-3 sm:p-6">
          {templates.map((template) => (
            <div
              key={template.id}
              className="group rounded-2xl border border-slate-800 bg-slate-950/70 p-4 transition duration-200 hover:-translate-y-1 hover:border-cyan-500/50 hover:shadow-[0_0_24px_rgba(34,211,238,0.15)]"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="text-3xl">{template.icon}</div>
                {template.comingSoon ? (
                  <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-[10px] uppercase tracking-[0.24em] text-amber-300">
                    Coming Soon
                  </span>
                ) : null}
              </div>

              <h3 className="mt-4 text-lg font-semibold text-white">{template.name}</h3>
              <p className="mt-2 min-h-[48px] text-sm leading-6 text-slate-400">{template.description}</p>

              <button
                onClick={() => onSelectTemplate(template)}
                className="mt-5 w-full rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-500/20"
              >
                Use Template
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default TemplateGalleryModal;
