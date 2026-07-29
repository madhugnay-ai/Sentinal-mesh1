import { useEffect, useState } from 'react';
import { connectGmail, disconnectGmail, getGmailConnectionStatus } from '../services/api';
import type { WorkflowNodeData, WorkflowNodeField, WorkflowNodeValue } from '../types/workflow';

type PropertiesPanelProps = {
  selectedNode: {
    id: string;
    data: WorkflowNodeData;
  } | null;
  onUpdateNode: (id: string, field: WorkflowNodeField, value: WorkflowNodeValue) => void;
};

function PropertiesPanel({ selectedNode, onUpdateNode }: PropertiesPanelProps) {
  const [gmailStatus, setGmailStatus] = useState<'idle' | 'loading' | 'connected' | 'disconnected' | 'error'>('idle');
  const [gmailMessage, setGmailMessage] = useState('');

  useEffect(() => {
    if (!selectedNode || selectedNode.data.kind !== 'email-trigger') {
      return;
    }

    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === 'gmail-oauth-success') {
        setGmailStatus('connected');
        setGmailMessage('Gmail Connected');
      }
      if (event.data?.type === 'gmail-oauth-error') {
        setGmailStatus('error');
        setGmailMessage('Gmail connection failed.');
      }
    };

    window.addEventListener('message', handleMessage);

    let active = true;
    setGmailStatus('loading');
    getGmailConnectionStatus()
      .then((status) => {
        if (!active) {
          return;
        }
        setGmailStatus(status.connected ? 'connected' : 'disconnected');
        setGmailMessage(status.connected ? 'Gmail Connected' : 'No Gmail connection');
      })
      .catch(() => {
        if (!active) {
          return;
        }
        setGmailStatus('error');
        setGmailMessage('Unable to check Gmail connection');
      });

    return () => {
      active = false;
      window.removeEventListener('message', handleMessage);
    };
  }, [selectedNode?.id, selectedNode?.data.kind]);

  if (!selectedNode) {
    return (
      <aside className="w-full rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-xl">
        <h3 className="text-lg font-medium">Properties</h3>
        <p className="mt-2 text-sm text-slate-400">Select a node to edit its label, type, and configuration.</p>
      </aside>
    );
  }

  return (
    <aside className="w-full rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-xl">
      <h3 className="text-lg font-medium">Properties</h3>
      <div className="mt-4 space-y-3 text-sm text-slate-300">
        <label className="block">
          <span className="mb-1 block text-slate-400">Node Name</span>
          <input
            value={selectedNode.data.label}
            onChange={(event) => onUpdateNode(selectedNode.id, 'label', event.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
          />
        </label>

        <label className="block">
          <span className="mb-1 block text-slate-400">Node Type</span>
          <input
            value={selectedNode.data.nodeType}
            onChange={(event) => onUpdateNode(selectedNode.id, 'nodeType', event.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
          />
        </label>

        <label className="block">
          <span className="mb-1 block text-slate-400">Description</span>
          <textarea
            value={selectedNode.data.description}
            onChange={(event) => onUpdateNode(selectedNode.id, 'description', event.target.value)}
            className="min-h-24 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
          />
        </label>

        {selectedNode.data.kind === 'email-trigger' ? (
          <>
            <label className="block">
              <span className="mb-1 block text-slate-400">Email Account</span>
              <input
                value={selectedNode.data.emailAccount ?? ''}
                onChange={(event) => onUpdateNode(selectedNode.id, 'emailAccount', event.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-slate-400">Folder</span>
              <input
                value={selectedNode.data.folder ?? 'INBOX'}
                onChange={(event) => onUpdateNode(selectedNode.id, 'folder', event.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-slate-400">Subject Filter</span>
              <input
                value={selectedNode.data.subjectFilter ?? ''}
                onChange={(event) => onUpdateNode(selectedNode.id, 'subjectFilter', event.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
              />
            </label>

            <label className="flex items-center justify-between rounded-lg border border-slate-700 bg-slate-950 px-3 py-2">
              <span className="text-slate-400">Unread only</span>
              <input
                type="checkbox"
                checked={Boolean(selectedNode.data.unreadOnly)}
                onChange={(event) => onUpdateNode(selectedNode.id, 'unreadOnly', event.target.checked)}
                className="h-4 w-4 rounded border-slate-600 bg-slate-900"
              />
            </label>

            <div className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Gmail Connection</span>
                <span className="text-xs text-slate-500">{gmailStatus === 'connected' ? 'Connected' : gmailStatus === 'loading' ? 'Checking...' : gmailStatus === 'error' ? 'Error' : 'Not connected'}</span>
              </div>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setGmailStatus('loading');
                    setGmailMessage('Opening Google consent screen...');
                    connectGmail()
                      .then(({ auth_url }) => {
                        window.open(auth_url, '_blank', 'width=600,height=700');
                        setGmailStatus('loading');
                        setGmailMessage('Complete the Google consent screen to connect Gmail.');
                      })
                      .catch(() => {
                        setGmailStatus('error');
                        setGmailMessage('Unable to start Gmail connection.');
                      });
                  }}
                  className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200"
                >
                  Connect Gmail
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setGmailStatus('loading');
                    disconnectGmail()
                      .then(() => {
                        setGmailStatus('disconnected');
                        setGmailMessage('Disconnected from Gmail.');
                      })
                      .catch(() => {
                        setGmailStatus('error');
                        setGmailMessage('Unable to disconnect Gmail.');
                      });
                  }}
                  className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200"
                >
                  Disconnect
                </button>
              </div>
              {gmailMessage ? <p className="mt-2 text-xs text-slate-500">{gmailMessage}</p> : null}
            </div>
          </>
        ) : null}

        {selectedNode.data.kind === 'llm' ? (
          <>
            <label className="block">
              <span className="mb-1 block text-slate-400">Provider</span>
              <select
                value={selectedNode.data.provider || 'OpenAI'}
                onChange={(event) => onUpdateNode(selectedNode.id, 'provider', event.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
              >
                <option value="OpenAI">OpenAI</option>
                <option value="Gemini">Gemini</option>
                <option value="Groq">Groq</option>
              </select>
            </label>

            <label className="block">
              <span className="mb-1 block text-slate-400">Model</span>
              <input
                value={selectedNode.data.model || ''}
                onChange={(event) => onUpdateNode(selectedNode.id, 'model', event.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-slate-400">Prompt</span>
              <textarea
                value={selectedNode.data.prompt || ''}
                onChange={(event) => onUpdateNode(selectedNode.id, 'prompt', event.target.value)}
                className="min-h-24 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-slate-400">Temperature</span>
              <input
                type="number"
                step="0.1"
                value={selectedNode.data.temperature ?? 0}
                onChange={(event) => onUpdateNode(selectedNode.id, 'temperature', Number(event.target.value))}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-slate-400">Max Tokens</span>
              <input
                type="number"
                value={selectedNode.data.maxTokens ?? 256}
                onChange={(event) => onUpdateNode(selectedNode.id, 'maxTokens', Number(event.target.value))}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
              />
            </label>
          </>
        ) : null}

        {selectedNode.data.kind === 'send-email' ? (
          <>
            <label className="block">
              <span className="mb-1 block text-slate-400">Recipient</span>
              <input
                value={selectedNode.data.recipientEmail ?? ''}
                onChange={(event) => onUpdateNode(selectedNode.id, 'recipientEmail', event.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-slate-400">Subject</span>
              <input
                value={selectedNode.data.subject ?? ''}
                onChange={(event) => onUpdateNode(selectedNode.id, 'subject', event.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
              />
            </label>

            <label className="block">
              <span className="mb-1 block text-slate-400">Optional Body</span>
              <textarea
                value={selectedNode.data.body ?? ''}
                onChange={(event) => onUpdateNode(selectedNode.id, 'body', event.target.value)}
                className="min-h-24 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
              />
            </label>

            <label className="flex items-center justify-between rounded-lg border border-slate-700 bg-slate-950 px-3 py-2">
              <span className="text-slate-400">Use LLM Output</span>
              <input
                type="checkbox"
                checked={Boolean(selectedNode.data.useLlmOutput)}
                onChange={(event) => onUpdateNode(selectedNode.id, 'useLlmOutput', event.target.checked)}
                className="h-4 w-4 rounded border-slate-600 bg-slate-900"
              />
            </label>
          </>        ) : selectedNode.data.kind === 'condition' ? (
          <>
            <label className="block">
              <span className="mb-1 block text-slate-400">Field</span>
              <input
                value={selectedNode.data.field ?? ''}
                onChange={(event) => onUpdateNode(selectedNode.id, 'field', event.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-slate-400">Operator</span>
              <select
                value={selectedNode.data.operator ?? 'equals'}
                onChange={(event) => onUpdateNode(selectedNode.id, 'operator', event.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
              >
                <option value="equals">equals</option>
                <option value="not_equals">not_equals</option>
                <option value="contains">contains</option>
                <option value="not_contains">not_contains</option>
                <option value="greater_than">greater_than</option>
                <option value="less_than">less_than</option>
                <option value="greater_than_or_equal">greater_than_or_equal</option>
                <option value="less_than_or_equal">less_than_or_equal</option>
                <option value="exists">exists</option>
                <option value="not_exists">not_exists</option>
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-slate-400">Value</span>
              <input
                value={selectedNode.data.value ?? ''}
                onChange={(event) => onUpdateNode(selectedNode.id, 'value', event.target.value)}
                disabled={selectedNode.data.operator === 'exists' || selectedNode.data.operator === 'not_exists'}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none disabled:cursor-not-allowed disabled:opacity-50"
              />
            </label>
          </>        ) : null}

        <label className="block">
          <span className="mb-1 block text-slate-400">Configuration</span>
          <textarea
            value={selectedNode.data.config}
            onChange={(event) => onUpdateNode(selectedNode.id, 'config', event.target.value)}
            className="min-h-24 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none"
          />
        </label>
      </div>
    </aside>
  );
}

export default PropertiesPanel;
