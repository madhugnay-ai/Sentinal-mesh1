import axios from 'axios';
import type { WorkflowPayload, WorkflowExecutionResult, WorkflowRecord } from '../types/workflow';

export type GmailConnectionStatus = {
  connected: boolean;
  configured: boolean;
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 10000,
});

function getErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'An unexpected error occurred.';
}

export async function saveWorkflow(payload: WorkflowPayload): Promise<WorkflowRecord> {
  try {
    const response = await api.post<WorkflowRecord>('/workflows', payload);
    return response.data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function loadWorkflow(workflowId: string): Promise<WorkflowRecord> {
  try {
    const response = await api.get<WorkflowRecord>(`/workflows/${workflowId}`);
    return response.data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function listWorkflows(): Promise<WorkflowRecord[]> {
  try {
    const response = await api.get<WorkflowRecord[]>('/workflows');
    return response.data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function deleteWorkflow(workflowId: string): Promise<void> {
  try {
    await api.delete(`/workflows/${workflowId}`);
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function executeWorkflow(workflowId: string): Promise<WorkflowExecutionResult> {
  try {
    const response = await api.post<WorkflowExecutionResult>(`/workflows/${workflowId}/execute`, undefined, {
      timeout: 30000,
    });
    return response.data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function getGmailConnectionStatus(): Promise<GmailConnectionStatus> {
  try {
    const response = await api.get<GmailConnectionStatus>('/gmail/oauth/status');
    return response.data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function connectGmail(): Promise<{ auth_url: string }> {
  try {
    const response = await api.get<{ auth_url: string }>('/gmail/oauth/authorize');
    return response.data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export async function disconnectGmail(): Promise<GmailConnectionStatus> {
  try {
    const response = await api.delete<GmailConnectionStatus>('/gmail/oauth/disconnect');
    return response.data;
  } catch (error) {
    throw new Error(getErrorMessage(error));
  }
}

export { getErrorMessage };
