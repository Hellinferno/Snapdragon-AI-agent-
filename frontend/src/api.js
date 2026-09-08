const API_BASE = '/api';

export function normalizeVisionUpload(response) {
  const [width, height] = response.dimensions;
  return {
    id: response.image_id,
    filename: response.filename,
    width,
    height,
    aspectRatio: width / height,
    mimeType: response.mime_type,
    previewUrl: response.preview_url,
  };
}

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

export async function fetchRuntimeStatus() {
  const res = await fetch(`${API_BASE}/runtime/status`);
  if (!res.ok) {
    throw new Error('Failed to fetch runtime telemetry');
  }
  return res.json();
}


export async function searchDocuments(query, documentIds = null, topK = 5) {
  const res = await fetch(`${API_BASE}/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, document_ids: documentIds, top_k: topK }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Search failed with status ${res.status}`);
  }
  return res.json();
}

export async function sendChatQuestion(question, documentIds = null, topK = 5) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, document_ids: documentIds, top_k: topK }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Chat failed with status ${res.status}`);
  }
  return res.json();
}

export async function compareDocuments(documentIds, dimensions = null) {
  const res = await fetch(`${API_BASE}/research/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_ids: documentIds, dimensions }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Comparison failed with status ${res.status}`);
  }
  return res.json();
}

export async function explainConcept(concept, documentIds = null, level = 'beginner') {
  const res = await fetch(`${API_BASE}/learning/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ concept, document_ids: documentIds, level }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Explanation request failed: ${res.statusText}`);
  }
  return res.json();
}

export async function generateQuiz(documentIds = null, questionCount = 4, difficulty = 'medium') {
  const res = await fetch(`${API_BASE}/learning/quiz`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_ids: documentIds, question_count: questionCount, difficulty }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Quiz generation failed: ${res.statusText}`);
  }
  return res.json();
}

export async function generateFlashcards() {
  const res = await fetch(`${API_BASE}/learning/flashcards`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Flashcards generation failed: ${res.statusText}`);
  }
  return res.json();
}

export async function uploadVisionImage(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/vision/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Image upload failed: ${res.statusText}`);
  }
  const data = await res.json();
  return normalizeVisionUpload(data);
}

export async function analyzeFigure(imageId) {
  const res = await fetch(`${API_BASE}/vision/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_id: imageId }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Figure analysis failed: ${res.statusText}`);
  }
  return res.json();
}

export async function chatWithFigure(imageId, question) {
  const res = await fetch(`${API_BASE}/vision/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_id: imageId, question }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Visual chat failed: ${res.statusText}`);
  }
  return res.json();
}

export function getVisionImageUrl(imageId) {
  return `${API_BASE}/vision/${imageId}/file`;
}

export async function seedDemoDataset() {
  const res = await fetch(`${API_BASE}/documents/seed_demo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Demo seeding failed: ${res.statusText}`);
  }
  return res.json();
}

