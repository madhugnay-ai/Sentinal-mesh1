import { Background, Controls, MiniMap, type NodeMouseHandler, type OnNodesDelete, type ReactFlowProps, ReactFlow } from 'reactflow';
import 'reactflow/dist/style.css';
import WorkflowNode from './WorkflowNode';
import type { WorkflowEdge, WorkflowNode as WorkflowNodeType } from '../types/workflow';

type WorkflowCanvasProps = {
  nodes: WorkflowNodeType[];
  edges: WorkflowEdge[];
  onNodesChange: ReactFlowProps['onNodesChange'];
  onEdgesChange: ReactFlowProps['onEdgesChange'];
  onConnect: ReactFlowProps['onConnect'];
  onNodeClick: NodeMouseHandler;
  onPaneClick: ReactFlowProps['onPaneClick'];
  onNodesDelete: OnNodesDelete;
};

const nodeTypes = {
  workflowNode: WorkflowNode,
};

function WorkflowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onNodeClick,
  onPaneClick,
  onNodesDelete,
}: WorkflowCanvasProps) {
  return (
    <div className="h-full w-full rounded-xl border border-slate-800">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onNodesDelete={onNodesDelete}
        deleteKeyCode="Delete"
        fitView
        attributionPosition="bottom-left"
        style={{ width: '100%', height: '100%' }}
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}

export default WorkflowCanvas;
