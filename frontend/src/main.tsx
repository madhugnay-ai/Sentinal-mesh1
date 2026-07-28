import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles.css';

function handleGmailOAuthCallback() {
  if (typeof window === 'undefined') {
    return;
  }

  const params = new URLSearchParams(window.location.search);
  const status = params.get('status');

  if (!window.opener || !status) {
    return;
  }

  if (status === 'success') {
    window.opener.postMessage({ type: 'gmail-oauth-success' }, window.location.origin);
    document.body.innerHTML = '<div style="font-family: sans-serif; padding: 2rem; color: #e2e8f0;">Gmail connected. You can close this window.</div>';
  } else {
    window.opener.postMessage({ type: 'gmail-oauth-error' }, window.location.origin);
    document.body.innerHTML = '<div style="font-family: sans-serif; padding: 2rem; color: #fda4af;">Gmail connection failed. You can close this window.</div>';
  }

  window.setTimeout(() => window.close(), 1200);
}

handleGmailOAuthCallback();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
