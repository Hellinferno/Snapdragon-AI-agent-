const API_BASE = '/api';

export async function fetchDocuments() {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) {
    throw new Error(`Failed to fetch documents: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchDocumentDetail(id) {
  const res = await fetch(`${API_BASE}/documents/${id}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch document details: ${res.statusText}`);
  }
  return res.json();
}

export async function uploadDocument(file, title = null, authors = null) {
  const formData = new FormData();
  formData.append('file', file);
  if (title) formData.append('title', title);
  if (authors) formData.append('authors', authors);

  const res = await fetch(`${API_BASE}/documents`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed with status ${res.status}`);
  }
  return res.json();
}

export async function deleteDocument(id) {
  const res = await fetch(`${API_BASE}/documents/${id}`, {
    method: 'DELETE',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Delete failed with status ${res.status}`);
  }
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) {
    throw new Error('Backend health check failed');
  }
  return res.json();
}
