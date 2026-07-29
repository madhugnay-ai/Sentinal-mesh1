import type { WorkflowExecutionResult } from '../types/workflow';

export type ExecutionDisplayState = 'waiting' | 'current' | 'success' | 'failed';

export type ExecutionStateNode = {
  id: string;
  data: {
    label?: string;
    nodeType?: string;
    kind?: string;
  };
};

export type NodeExecutionState = {
  currentNodeId: string | null;
  completedNodeIds: string[];
  failedNodeIds: string[];
  skippedNodeIds: string[];
};

function normalize(text: string) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

function getNodeMatchers(node: ExecutionStateNode) {
  return [node.data.kind, node.data.label, node.data.nodeType]
    .filter(Boolean)
    .map((value) => normalize(value as string))
    .filter(Boolean);
}

function matchExecutionStep(entry: string, nodes: ExecutionStateNode[]) {
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

function resolveNodeIdFromStage(nodes: ExecutionStateNode[], stage: string) {
  const normalizedStage = normalize(stage);
  if (!normalizedStage) {
    return null;
  }

  return nodes.find((node) => {
    const matchers = getNodeMatchers(node);
    return matchers.some((matcher) => normalize(matcher) === normalizedStage);
  })?.id ?? null;
}

export type ExecutionAnimationSnapshot = {
  currentNodeId: string | null;
  completedNodeIds: string[];
  failedNodeIds: string[];
  skippedNodeIds: string[];
  isPlaying?: boolean;
};

export function getNodeExecutionState(nodes: ExecutionStateNode[], result?: WorkflowExecutionResult | null) {
  const completedNodeIds = [...new Set((result?.executed_node_ids ?? []).filter(Boolean))];
  const failedNodeIds = [...new Set((result?.failed_node_ids ?? []).filter(Boolean))];
  const skippedNodeIds = [...new Set((result?.skipped_node_ids ?? []).filter(Boolean))];

  if (!completedNodeIds.length && !failedNodeIds.length && !skippedNodeIds.length) {
    const fallbackSteps = (result?.execution_log ?? []).reduce<Array<{ nodeId: string; status: 'success' | 'failed' }>>((collected, entry) => {
      const nodeId = matchExecutionStep(entry, nodes);
      if (!nodeId) {
        return collected;
      }

      collected.push({ nodeId, status: getExecutionStatus(entry) });
      return collected;
    }, []);

    return {
      currentNodeId: result?.current_node_id ?? null,
      completedNodeIds: fallbackSteps.filter((step) => step.status === 'success').map((step) => step.nodeId),
      failedNodeIds: fallbackSteps.filter((step) => step.status === 'failed').map((step) => step.nodeId),
      skippedNodeIds: [],
    } satisfies NodeExecutionState;
  }

  const stageCompletedIds = (result?.completed_stages ?? [])
    .map((stage) => resolveNodeIdFromStage(nodes, stage))
    .filter((value): value is string => Boolean(value));

  const stageFailedIds = (result?.failed_stages ?? [])
    .map((stage) => resolveNodeIdFromStage(nodes, stage))
    .filter((value): value is string => Boolean(value));

  const stageSkippedIds = (result?.skipped_stages ?? [])
    .map((stage) => resolveNodeIdFromStage(nodes, stage))
    .filter((value): value is string => Boolean(value));

  const mergedCompletedNodeIds = [...new Set([...completedNodeIds, ...stageCompletedIds])];
  const mergedFailedNodeIds = [...new Set([...failedNodeIds, ...stageFailedIds])];
  const mergedSkippedNodeIds = [...new Set([...skippedNodeIds, ...stageSkippedIds])];

  return {
    currentNodeId: result?.current_node_id ?? null,
    completedNodeIds: mergedCompletedNodeIds,
    failedNodeIds: mergedFailedNodeIds,
    skippedNodeIds: mergedSkippedNodeIds,
  } satisfies NodeExecutionState;
}

export function getVisualExecutionState(nodeId: string, state: ExecutionAnimationSnapshot): ExecutionDisplayState {
  if (state.isPlaying && state.currentNodeId === nodeId) {
    return 'current';
  }
  if (state.failedNodeIds.includes(nodeId)) {
    return 'failed';
  }
  if (state.completedNodeIds.includes(nodeId)) {
    return 'success';
  }
  if (state.skippedNodeIds.includes(nodeId)) {
    return 'waiting';
  }
  return 'waiting';
}
