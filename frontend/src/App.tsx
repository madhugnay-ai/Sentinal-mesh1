import { useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react';
import ExecutionPanel from './components/ExecutionPanel';
import PropertiesPanel from './components/PropertiesPanel';
import Sidebar from './components/Sidebar';
import Toolbar from './components/Toolbar';
import TemplateExecutionDialog from './components/TemplateExecutionDialog';
import TemplateGalleryModal from './components/TemplateGalleryModal';
import WorkflowCanvas from './components/WorkflowCanvas';
import { useWorkflow } from './hooks/useWorkflow';
import { workflowTemplates } from './templates/workflowTemplates';
import { getExecutionEligibility } from './nodeCapabilities';

const STORAGE_KEY = 'sentinelmesh-panel-widths';
const DEFAULT_PANEL_WIDTHS = {
  sidebarWidth: 260,
  canvasWidth: 760,
  inspectorWidth: 360,
};

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function getStoredPanelWidths() {
  if (typeof window === 'undefined') {
    return DEFAULT_PANEL_WIDTHS;
  }

  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (!saved) {
      return DEFAULT_PANEL_WIDTHS;
    }

    const parsed = JSON.parse(saved) as Partial<typeof DEFAULT_PANEL_WIDTHS>;
    return {
      sidebarWidth: parsed.sidebarWidth ?? DEFAULT_PANEL_WIDTHS.sidebarWidth,
      canvasWidth: parsed.canvasWidth ?? DEFAULT_PANEL_WIDTHS.canvasWidth,
      inspectorWidth: parsed.inspectorWidth ?? DEFAULT_PANEL_WIDTHS.inspectorWidth,
    };
  } catch {
    return DEFAULT_PANEL_WIDTHS;
  }
}

function App() {
  const {
    animatedNodes,
    animatedEdges,
    selectedNode,
    name,
    status,
    workflowSummary,
    onNodesChange,
    onEdgesChange,
    setSelectedNodeId,
    setName,
    setStatus,
    onConnect,
    addNode,
    updateNode,
    deleteSelectedNode,
    saveWorkflow,
    loadWorkflow,
    exportJson,
    clearCanvas,
    setEdges,
    setNodes,
    executeWorkflow,
    replayExecutionAnimation,
    executionResult,
    isExecuting,
    errorMessage,
  } = useWorkflow();

  const layoutRef = useRef<HTMLDivElement | null>(null);
  const dragOrigin = useRef<{ x: number; sidebarWidth: number; canvasWidth: number; inspectorWidth: number } | null>(null);
  const [panelWidths, setPanelWidths] = useState(getStoredPanelWidths);
  const [activeSplitter, setActiveSplitter] = useState<'left' | 'right' | null>(null);
  const [isMobile, setIsMobile] = useState(() => (typeof window !== 'undefined' ? window.innerWidth < 1024 : false));
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false);
  const [isExecutionDialogOpen, setIsExecutionDialogOpen] = useState(false);
  const [unsupportedNodeTypes, setUnsupportedNodeTypes] = useState<string[]>([]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const handleResize = () => {
      setIsMobile(window.innerWidth < 1024);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(panelWidths));
  }, [panelWidths]);

  useEffect(() => {
    if (!activeSplitter) {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      return;
    }

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    const handleMouseMove = (event: MouseEvent) => {
      const origin = dragOrigin.current;
      if (!origin || !layoutRef.current) {
        return;
      }

      const containerWidth = layoutRef.current.getBoundingClientRect().width;
      const delta = event.clientX - origin.x;
      const splitterWidth = 8;
      const gapWidth = 16;
      const availableWidth = containerWidth - splitterWidth * 2 - gapWidth * 2;
      const minSidebar = 220;
      const minCanvas = 500;
      const minInspector = 320;

      if (activeSplitter === 'left') {
        const maxSidebar = availableWidth - minCanvas - origin.inspectorWidth;
        const nextSidebarWidth = clamp(origin.sidebarWidth + delta, minSidebar, maxSidebar);
        const nextCanvasWidth = availableWidth - nextSidebarWidth - origin.inspectorWidth;
        setPanelWidths((current) => ({
          ...current,
          sidebarWidth: nextSidebarWidth,
          canvasWidth: clamp(nextCanvasWidth, minCanvas, availableWidth - minSidebar - origin.inspectorWidth),
        }));
      }

      if (activeSplitter === 'right') {
        const maxCanvas = availableWidth - origin.sidebarWidth - minInspector;
        const nextCanvasWidth = clamp(origin.canvasWidth + delta, minCanvas, maxCanvas);
        const nextInspectorWidth = availableWidth - origin.sidebarWidth - nextCanvasWidth;
        setPanelWidths((current) => ({
          ...current,
          canvasWidth: nextCanvasWidth,
          inspectorWidth: clamp(nextInspectorWidth, minInspector, availableWidth - origin.sidebarWidth - minCanvas),
        }));
      }
    };

    const handleMouseUp = () => {
      setActiveSplitter(null);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [activeSplitter]);

  const handleSplitterMouseDown = (splitter: 'left' | 'right') => (event: ReactMouseEvent<HTMLDivElement>) => {
    if (isMobile) {
      return;
    }

    dragOrigin.current = {
      x: event.clientX,
      sidebarWidth: panelWidths.sidebarWidth,
      canvasWidth: panelWidths.canvasWidth,
      inspectorWidth: panelWidths.inspectorWidth,
    };
    setActiveSplitter(splitter);
    event.preventDefault();
  };

  const handleSelectTemplate = (template: (typeof workflowTemplates)[number]) => {
    setName(template.initialName ?? template.name);
    setNodes(template.nodes);
    setEdges(template.edges);
    setSelectedNodeId(null);
    setStatus(`Loaded template: ${template.name}`);
    setIsTemplateModalOpen(false);
  };

  const executionEligibility = getExecutionEligibility(animatedNodes);

  const handleExecuteWorkflow = () => {
    const { canExecute, unsupportedNodeTypes: unavailableNodes } = getExecutionEligibility(animatedNodes);
    setUnsupportedNodeTypes(unavailableNodes);

    if (!canExecute) {
      setIsExecutionDialogOpen(true);
      return;
    }

    executeWorkflow();
  };

  return (
    <div className="min-h-screen bg-slate-950 p-3 text-slate-100 sm:p-4 lg:p-6">
      <div className="mx-auto flex w-full flex-1 flex-col gap-4">
        <header className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-2xl sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-cyan-400">SentinelMesh Studio</p>
              <h1 className="mt-2 text-3xl font-semibold">Workflow Builder</h1>
            </div>
            <Toolbar onSave={saveWorkflow} onLoad={loadWorkflow} onExport={exportJson} onClear={clearCanvas} onExecute={handleExecuteWorkflow} onOpenTemplates={() => setIsTemplateModalOpen(true)} />
          </div>
        </header>

        <div ref={layoutRef} className="flex min-h-0 flex-1 flex-col gap-4 lg:flex-row">
          <div className="shrink-0" style={{ width: isMobile ? '100%' : `${panelWidths.sidebarWidth}px` }}>
            <Sidebar onAddNode={addNode} />
          </div>

          {!isMobile ? (
            <div
              className="hidden w-2 shrink-0 cursor-col-resize rounded-full bg-slate-800/80 transition hover:bg-cyan-500/40 lg:block"
              onMouseDown={handleSplitterMouseDown('left')}
            />
          ) : null}

          <div
            className="min-h-0 rounded-2xl border border-slate-800 bg-slate-900/70 p-3 shadow-xl sm:p-4"
            style={{ width: isMobile ? '100%' : `${panelWidths.canvasWidth}px`, minWidth: isMobile ? undefined : '500px', flexShrink: 0 }}
          >
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-medium">Canvas</h2>
              <div className="flex items-center gap-3">
                <label className="text-sm text-slate-400">
                  Workflow name
                  <input
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="ml-2 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
                  />
                </label>
                <span className={`rounded-full px-3 py-1 text-sm ${executionEligibility.canExecute ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'}`}>
                  {executionEligibility.canExecute ? 'Backend Supported' : 'Blocked by Node Support'}
                </span>
                <button
                  onClick={() => replayExecutionAnimation(executionResult?.execution_log)}
                  disabled={!executionResult?.execution_log?.length}
                  className="rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-3 py-2 text-sm font-medium text-cyan-200 transition hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Replay
                </button>
                <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-sm text-emerald-300">{status}</span>
              </div>
            </div>
            <div className="h-[calc(100vh-13rem)] min-h-[620px] overflow-hidden rounded-xl border border-slate-800">
              <WorkflowCanvas
                nodes={animatedNodes}
                edges={animatedEdges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onNodeClick={(_, node) => setSelectedNodeId(node.id)}
                onPaneClick={() => setSelectedNodeId(null)}
                onNodesDelete={(deleted) => {
                  const ids = new Set(deleted.map((node) => node.id));
                  setEdges((currentEdges) => currentEdges.filter((edge) => !ids.has(edge.source) && !ids.has(edge.target)));
                }}
              />
            </div>
          </div>

          {!isMobile ? (
            <div
              className="hidden w-2 shrink-0 cursor-col-resize rounded-full bg-slate-800/80 transition hover:bg-cyan-500/40 lg:block"
              onMouseDown={handleSplitterMouseDown('right')}
            />
          ) : null}

          <div className="w-full shrink-0 lg:w-auto" style={{ width: isMobile ? '100%' : `${panelWidths.inspectorWidth}px`, minWidth: isMobile ? undefined : '320px' }}>
            <div className="flex h-full flex-col overflow-y-auto rounded-2xl border border-slate-800 bg-slate-900/70 shadow-xl">
              <div className="space-y-4 p-4">
                <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 shadow-xl">
                  <h3 className="text-lg font-medium">Workflow details</h3>
                  <div className="mt-4 space-y-3 text-sm text-slate-300">
                    <div className="flex items-center justify-between rounded-lg bg-slate-900/80 px-3 py-2">
                      <span>Nodes</span>
                      <strong>{workflowSummary.nodes}</strong>
                    </div>
                    <div className="flex items-center justify-between rounded-lg bg-slate-900/80 px-3 py-2">
                      <span>Edges</span>
                      <strong>{workflowSummary.edges}</strong>
                    </div>
                    <div className="flex items-center justify-between rounded-lg bg-slate-900/80 px-3 py-2">
                      <span>Updated</span>
                      <strong>{workflowSummary.lastUpdated}</strong>
                    </div>
                  </div>
                  <button
                    onClick={deleteSelectedNode}
                    className="mt-4 w-full rounded-xl border border-rose-700 bg-rose-600/20 px-3 py-2 text-sm text-rose-200 transition hover:bg-rose-600/40"
                  >
                    Delete Selected Node
                  </button>
                </div>
                <PropertiesPanel selectedNode={selectedNode} onUpdateNode={updateNode} />
              </div>
              <div className="border-t border-slate-800">
                <ExecutionPanel result={executionResult} isExecuting={isExecuting} errorMessage={errorMessage} />
              </div>
            </div>
          </div>
        </div>
      </div>
      <TemplateGalleryModal
        isOpen={isTemplateModalOpen}
        onClose={() => setIsTemplateModalOpen(false)}
        onSelectTemplate={handleSelectTemplate}
        templates={workflowTemplates}
      />
      <TemplateExecutionDialog
        isOpen={isExecutionDialogOpen}
        onClose={() => setIsExecutionDialogOpen(false)}
        unsupportedNodeTypes={unsupportedNodeTypes}
      />
    </div>
  );
}

export default App;
