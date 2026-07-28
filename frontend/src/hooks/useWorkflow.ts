import { useMemo, useState } from 'react';
import { type Connection, addEdge, useEdgesState, useNodesState } from 'reactflow';
import { executeWorkflow, listWorkflows, saveWorkflow } from '../services/api';
import { loadWorkflowFromStorage, saveWorkflowToStorage, exportWorkflowJson } from '../services/workflowStorage';
import type { WorkflowEdge, WorkflowExecutionResult, WorkflowNode, WorkflowNodeData, WorkflowNodeField, WorkflowNodeValue, WorkflowPayload } from '../types/workflow';

const initialNodes: WorkflowNode[] = [
  {
    id: 'requirement-validation-1',
    type: 'workflowNode',
    position: { x: 80, y: 80 },
    data: {
      label: 'Requirement Validation',
      nodeType: 'Requirement Validation',
      description: 'Validate incoming requirements before proceeding.',
      config: 'Rule: must include business owner',
      kind: 'requirement-validation',
    },
  },
  {
    id: 'approval-1',
    type: 'workflowNode',
    position: { x: 360, y: 220 },
    data: {
      label: 'Approval',
      nodeType: 'Approval',
      description: 'Review and authorize the request.',
      config: 'Approver: Finance Lead',
      kind: 'approval',
    },
  },
];

const initialEdges: WorkflowEdge[] = [{ id: 'e1', source: 'requirement-validation-1', target: 'approval-1' }];

type AnimationStep = {
  nodeId: string;
  status: 'success' | 'failed';
};

type ExecutionAnimationState = {
  steps: AnimationStep[];
  currentNodeId: string | null;
  completedNodeIds: string[];
  failedNodeIds: string[];
  activeEdgeIds: string[];
  isPlaying: boolean;
};

function normalize(text: string) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function getNodeMatchers(node: WorkflowNode) {
  return [node.data.kind, node.data.label, node.data.nodeType]
    .filter(Boolean)
    .map((value) => normalize(value as string))
    .filter(Boolean);
}

function matchExecutionStep(entry: string, nodes: WorkflowNode[]) {
  const normalizedEntry = normalize(entry);
  if (!normalizedEntry) {
    return null;
  }

  let bestMatch: { nodeId: string; score: number; index: number } | undefined;

  nodes.forEach((node) => {
    const keywords = getNodeMatchers(node);
    if (!keywords.length) {
      return;
    }

    const score = keywords.reduce((total, keyword) => (normalizedEntry.includes(keyword) ? total + 1 : total), 0);
    if (!score) {
      return;
    }

    const keywordIndex = keywords.reduce((smallestIndex, keyword) => {
      const index = normalizedEntry.indexOf(keyword);
      return index >= 0 && (smallestIndex === -1 || index < smallestIndex) ? index : smallestIndex;
    }, -1);

    if (!bestMatch || score > bestMatch.score || (score === bestMatch.score && keywordIndex !== -1 && (bestMatch.index === -1 || keywordIndex < bestMatch.index))) {
      bestMatch = { nodeId: node.id, score, index: keywordIndex };
    }
  });

  return bestMatch?.nodeId ?? null;
}

function getExecutionStatus(entry: string) {
  const normalized = normalize(entry);
  if (/failed|rejected|not generated|error/.test(normalized)) {
    return 'failed' as const;
  }
  if (/passed|completed|approved|generated|healthy/.test(normalized)) {
    return 'success' as const;
  }
  return 'success' as const;
}

export function useWorkflow() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [name, setName] = useState('Procurement Workflow');
  const [status, setStatus] = useState('Ready');
  const [workflowId, setWorkflowId] = useState<string | null>(null);
  const [executionResult, setExecutionResult] = useState<WorkflowExecutionResult | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [executionAnimation, setExecutionAnimation] = useState<ExecutionAnimationState | null>(null);

  const workflowSummary = useMemo(() => ({
    nodes: nodes.length,
    edges: edges.length,
    lastUpdated: new Date().toLocaleTimeString(),
  }), [nodes.length, edges.length]);

  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? null;

  const animatedNodes = useMemo(() => {
    return nodes.map((node) => {
      const state: WorkflowNodeData['executionState'] = executionAnimation?.currentNodeId === node.id
        ? 'current'
        : executionAnimation?.failedNodeIds.includes(node.id)
          ? 'failed'
          : executionAnimation?.completedNodeIds.includes(node.id)
            ? 'success'
            : 'waiting';

      return {
        ...node,
        data: {
          ...node.data,
          executionState: state,
        },
      };
    });
  }, [nodes, executionAnimation]);

  const animatedEdges = useMemo(() => {
    return edges.map((edge) => ({
      ...edge,
      animated: executionAnimation?.activeEdgeIds.includes(edge.id) ?? false,
      style: executionAnimation?.activeEdgeIds.includes(edge.id)
        ? { stroke: '#38bdf8', strokeWidth: 3 }
        : { stroke: '#475569', strokeWidth: 2 },
    }));
  }, [edges, executionAnimation]);

  const onConnect = (params: Connection) => {
    setEdges((currentEdges) => addEdge(params, currentEdges));
  };

  const addNode = (kind: string) => {
    const id = `${kind}-${Date.now()}`;
    const label = kind
      .split('-')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');

    const nodeData: WorkflowNodeData = {
      label,
      nodeType: label,
      description: kind === 'email-trigger' ? 'Collect inbound emails from Gmail.' : kind === 'llm' ? 'Generate text with an LLM provider.' : 'New workflow step.',
      config: kind === 'email-trigger' ? 'Email account, folder, and filter settings' : kind === 'llm' ? 'LLM runtime configuration' : 'Default configuration',
      kind,
      ...(kind === 'email-trigger'
        ? {
            emailAccount: 'you@example.com',
            folder: 'INBOX',
            unreadOnly: true,
            subjectFilter: '',
          }
        : {}),
      ...(kind === 'llm'
        ? {
            provider: 'OpenAI',
            model: 'gpt-4.1-mini',
            prompt: 'Summarize the incoming content.',
            temperature: 0.2,
            maxTokens: 256,
          }
        : {}),
      ...(kind === 'send-email'
        ? {
            recipientEmail: 'recipient@example.com',
            subject: 'SentinelMesh notification',
            body: 'This is a fallback email body.',
            useLlmOutput: true,
          }
        : {}),
    };

    const newNode: WorkflowNode = {
      id,
      type: 'workflowNode',
      position: { x: 120 + nodes.length * 40, y: 80 + nodes.length * 40 },
      data: nodeData,
    };

    setNodes((currentNodes) => [...currentNodes, newNode]);
    setStatus(`Added ${label}`);
  };

  const updateNode = (id: string, field: WorkflowNodeField, value: WorkflowNodeValue) => {
    setNodes((currentNodes) =>
      currentNodes.map((node) => (node.id === id ? { ...node, data: { ...node.data, [field]: value } } : node)),
    );
  };

  const deleteSelectedNode = () => {
    if (!selectedNodeId) {
      return;
    }

    setNodes((currentNodes) => currentNodes.filter((node) => node.id !== selectedNodeId));
    setEdges((currentEdges) => currentEdges.filter((edge) => edge.source !== selectedNodeId && edge.target !== selectedNodeId));
    setSelectedNodeId(null);
    setStatus('Removed selected node');
  };

  const handleSaveWorkflow = async () => {
    const payload: WorkflowPayload = {
      name,
      description: `Workflow built in SentinelMesh Studio: ${name}`,
      nodes: nodes.map(({ id, type, position, data }) => ({ id, type, position, data })),
      edges,
    };

    try {
      const savedWorkflow = await saveWorkflow(payload);
      setWorkflowId(savedWorkflow.workflow_id);
      saveWorkflowToStorage(nodes, edges);
      setStatus(`Workflow saved to backend: ${savedWorkflow.workflow_id}`);
      setErrorMessage(null);
      return savedWorkflow.workflow_id;
    } catch (error) {
      setStatus('Save failed');
      const message = error instanceof Error ? error.message : 'Unable to save workflow.';
      setErrorMessage(message);
      throw new Error(message);
    }
  };

  const handleLoadWorkflow = async () => {
    try {
      const stored = loadWorkflowFromStorage();
      if (!stored) {
        const workflows = await listWorkflows();
        if (!workflows.length) {
          setStatus('No saved workflow found');
          return;
        }

        const latest = workflows[workflows.length - 1];
        setWorkflowId(latest.workflow_id);
        setName(latest.name);
        setNodes(latest.nodes as WorkflowNode[]);
        setEdges(latest.edges);
        setSelectedNodeId(null);
        setStatus('Workflow loaded from backend');
        setErrorMessage(null);
        return;
      }

      setNodes(stored.nodes);
      setEdges(stored.edges);
      setSelectedNodeId(null);
      setStatus('Workflow loaded locally');
      setErrorMessage(null);
    } catch (error) {
      setStatus('Load failed');
      setErrorMessage(error instanceof Error ? error.message : 'Unable to load workflow.');
    }
  };

  const exportJson = () => {
    exportWorkflowJson(name, nodes, edges);
    setStatus('JSON exported');
  };

  const replayExecutionAnimation = (logEntries: string[] | undefined = executionResult?.execution_log) => {
    const steps = (logEntries ?? []).reduce<AnimationStep[]>((collected, entry) => {
      const nodeId = matchExecutionStep(entry, nodes);
      if (!nodeId) {
        return collected;
      }

      collected.push({ nodeId, status: getExecutionStatus(entry) });
      return collected;
    }, []);

    if (!steps.length) {
      setExecutionAnimation(null);
      return;
    }

    setExecutionAnimation({
      steps,
      currentNodeId: null,
      completedNodeIds: [],
      failedNodeIds: [],
      activeEdgeIds: [],
      isPlaying: true,
    });

    let index = 0;
    const runStep = () => {
      if (index >= steps.length) {
        setExecutionAnimation((current) => (current ? { ...current, currentNodeId: null, isPlaying: false } : null));
        return;
      }

      const step = steps[index];
      const previousStep = steps[index - 1];
      const completedNodeIds = steps.slice(0, index).map((item) => item.nodeId);
      const failedNodeIds = steps.slice(0, index).filter((item) => item.status === 'failed').map((item) => item.nodeId);
      const activeEdgeIds = previousStep && edges.find((edge) => edge.source === previousStep.nodeId && edge.target === step.nodeId)
        ? [edges.find((edge) => edge.source === previousStep.nodeId && edge.target === step.nodeId)!.id]
        : [];

      setExecutionAnimation({
        steps,
        currentNodeId: step.nodeId,
        completedNodeIds,
        failedNodeIds,
        activeEdgeIds,
        isPlaying: true,
      });

      index += 1;
      window.setTimeout(runStep, 900);
    };

    runStep();
  };

  const executeWorkflowFromBackend = async () => {
    let currentWorkflowId = workflowId;

    if (!currentWorkflowId) {
      try {
        currentWorkflowId = await handleSaveWorkflow();
      } catch {
        setStatus('Execution unavailable');
        return;
      }
    }

    setIsExecuting(true);
    setErrorMessage(null);

    try {
      const result = await executeWorkflow(currentWorkflowId);
      console.log(result);
      setExecutionResult(result);
      setExecutionAnimation(null);
      replayExecutionAnimation(result.execution_log);
      setStatus('Workflow executed');
    } catch (error) {
      setExecutionResult(null);
      setStatus('Execution failed');
      const message = error instanceof Error ? error.message : 'Workflow execution failed.';
      setErrorMessage(message);
      console.error(message);
    } finally {
      setIsExecuting(false);
    }
  };

  const clearCanvas = () => {
    setNodes([]);
    setEdges([]);
    setSelectedNodeId(null);
    setStatus('Canvas cleared');
  };

  return {
    nodes,
    edges,
    animatedNodes,
    animatedEdges,
    selectedNode,
    selectedNodeId,
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
    saveWorkflow: handleSaveWorkflow,
    loadWorkflow: handleLoadWorkflow,
    exportJson,
    clearCanvas,
    setNodes,
    setEdges,
    executeWorkflow: executeWorkflowFromBackend,
    replayExecutionAnimation,
    workflowId,
    executionResult,
    isExecuting,
    errorMessage,
  };
}
