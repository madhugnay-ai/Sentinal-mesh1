import { getNodeExecutionState, getVisualExecutionState } from './executionState.ts';

function expectEqual(actual: unknown, expected: unknown, message: string) {
  if (actual !== expected) {
    throw new Error(`${message}: expected ${String(expected)}, received ${String(actual)}`);
  }
}

const nodes = [
  { id: 'email-1', data: { label: 'Email Trigger', kind: 'email-trigger' } },
  { id: 'llm-critical', data: { label: 'Critical Handler', kind: 'llm' } },
  { id: 'llm-support', data: { label: 'Support Handler', kind: 'llm' } },
];

const result = {
  execution_log: ['Router selected support'],
  executed_node_ids: ['email-1', 'llm-support'],
  failed_node_ids: [],
  skipped_node_ids: ['llm-critical'],
  current_node_id: 'llm-support',
};

const state = getNodeExecutionState(nodes, result as unknown as Parameters<typeof getNodeExecutionState>[1]);

expectEqual(state.completedNodeIds.includes('llm-support'), true, 'selected branch should be completed');
expectEqual(state.completedNodeIds.includes('llm-critical'), false, 'non-selected branch should not be completed');
expectEqual(state.skippedNodeIds.includes('llm-critical'), true, 'non-selected branch should be marked skipped');
expectEqual(state.currentNodeId, 'llm-support', 'active node should be the selected branch');

const finalState = getVisualExecutionState('llm-support', {
  currentNodeId: 'llm-support',
  completedNodeIds: ['llm-support'],
  failedNodeIds: [],
  skippedNodeIds: ['llm-critical'],
  isPlaying: false,
});

expectEqual(finalState, 'success', 'final executed branch should resolve to completed after replay finishes');

console.log('executionState test passed');
