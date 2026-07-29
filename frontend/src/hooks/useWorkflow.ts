import { useEffect, useMemo, useRef, useState } from 'react';
import { type Connection, addEdge, useEdgesState, useNodesState } from 'reactflow';
import { executeWorkflow, listWorkflows, saveWorkflow } from '../services/api';
import { loadWorkflowFromStorage, saveWorkflowToStorage, exportWorkflowJson, normalizeWorkflowEdges } from '../services/workflowStorage';
import { getNodeExecutionState, getVisualExecutionState } from './executionState';
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

type ExecutionAnimationState = {
  currentNodeId: string | null;
  completedNodeIds: string[];
  failedNodeIds: string[];
  activeEdgeIds: string[];
  isPlaying: boolean;
  skippedNodeIds: string[];
};

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
  const replayTimeoutRef = useRef<number | null>(null);

  const workflowSummary = useMemo(() => ({
    nodes: nodes.length,
    edges: edges.length,
    lastUpdated: new Date().toLocaleTimeString(),
  }), [nodes.length, edges.length]);

  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? null;

  const animatedNodes = useMemo(() => {
    return nodes.map((node) => {
      const state: WorkflowNodeData['executionState'] = getVisualExecutionState(node.id, {
        currentNodeId: executionAnimation?.currentNodeId ?? null,
        completedNodeIds: executionAnimation?.completedNodeIds ?? [],
        failedNodeIds: executionAnimation?.failedNodeIds ?? [],
        skippedNodeIds: executionAnimation?.skippedNodeIds ?? [],
        isPlaying: executionAnimation?.isPlaying ?? false,
      });

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
    const sourceNode = nodes.find((node) => node.id === params.source);
    const sourceKind = sourceNode?.data?.kind;
    const normalizedKind = sourceKind ? sourceKind.toLowerCase() : '';

    const nextParams: Connection = { ...params };

    if (normalizedKind === 'classifier' && params.sourceHandle) {
      nextParams.sourceHandle = params.sourceHandle;
    } else if (normalizedKind === 'classifier' && !params.sourceHandle) {
      const fallbackHandle = sourceNode?.data?.categories?.find((category) => category?.trim())?.trim();
      if (fallbackHandle) {
        nextParams.sourceHandle = fallbackHandle;
      }
    }

    setEdges((currentEdges) => addEdge(nextParams, currentEdges));
  };

  const addNode = (kind: string) => {
    const id = `${kind}-${Date.now()}`;
    const label = kind
      .split('-')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');

    const description = kind === 'email-trigger'
      ? 'Collect inbound emails from Gmail.'
      : kind === 'llm'
        ? 'Generate text with an LLM provider.'
        : kind === 'condition'
          ? 'Evaluate a condition and branch on true/false.'
          : kind === 'router'
            ? 'Select one outgoing route based on a field evaluation.'
            : 'New workflow step.';

    const config = kind === 'email-trigger'
      ? 'Email account, folder, and filter settings'
      : kind === 'llm'
        ? 'LLM runtime configuration'
        : kind === 'condition'
          ? 'Field, operator, and value determine the branch.'
          : kind === 'router'
            ? 'Routes are evaluated in order; first match wins.'
            : 'Default configuration';

    const nodeData: WorkflowNodeData = {
      label,
      nodeType: label,
      description,
      config,
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
      ...(kind === 'classifier'
        ? {
            provider: 'Groq',
            model: 'llama-3.1-8b-instant',
            inputField: 'email_subject_and_body',
            categories: ['critical', 'support', 'general'],
            instructions: 'Classify the incoming content into exactly one configured category.',
            temperature: 0,
            maxTokens: 128,
          }
        : {}),
      ...(kind === 'extractor'
        ? {
            provider: 'Groq',
            model: 'llama-3.1-8b-instant',
            inputField: 'email_subject_and_body',
            extractionFields: ['service', 'status', 'location', 'urgency'],
            instructions: 'Extract the requested fields into a structured JSON object.',
            temperature: 0,
            maxTokens: 256,
          }
        : {}),
      ...(kind === 'condition'
        ? {
            field: 'email_subject',
            operator: 'contains',
            value: 'URGENT',
          }
        : kind === 'router'
        ? {
            field: 'workflow_status',
            defaultRoute: 'default',
            routes: [
              { route: 'critical', operator: 'equals', value: 'CRITICAL' },
              { route: 'normal', operator: 'equals', value: 'NORMAL' },
            ],
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
    const normalizedEdges = normalizeWorkflowEdges(nodes, edges);
    const payload: WorkflowPayload = {
      name,
      description: `Workflow built in SentinelMesh Studio: ${name}`,
      nodes: nodes.map(({ id, type, position, data }) => ({ id, type, position, data })),
      edges: normalizedEdges,
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

  const replayExecutionAnimation = (result: WorkflowExecutionResult | string[] | null = executionResult) => {
    if (replayTimeoutRef.current !== null) {
      window.clearTimeout(replayTimeoutRef.current);
      replayTimeoutRef.current = null;
    }

    const nodeState = getNodeExecutionState(nodes, Array.isArray(result) ? ({ execution_log: result } as WorkflowExecutionResult) : result);

    setExecutionAnimation({
      currentNodeId: nodeState.currentNodeId,
      completedNodeIds: [],
      failedNodeIds: [],
      activeEdgeIds: [],
      isPlaying: true,
      skippedNodeIds: nodeState.skippedNodeIds,
    });

    replayTimeoutRef.current = window.setTimeout(() => {
      replayTimeoutRef.current = null;
      setExecutionAnimation({
        currentNodeId: null,
        completedNodeIds: nodeState.completedNodeIds,
        failedNodeIds: nodeState.failedNodeIds,
        activeEdgeIds: [],
        isPlaying: false,
        skippedNodeIds: nodeState.skippedNodeIds,
      });
    }, 500);
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
      replayExecutionAnimation(result);
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

  useEffect(() => {
    return () => {
      if (replayTimeoutRef.current !== null) {
        window.clearTimeout(replayTimeoutRef.current);
        replayTimeoutRef.current = null;
      }
    };
  }, []);

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
