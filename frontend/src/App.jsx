import React, { useState, useEffect, useRef } from 'react';
import {
  BookOpen,
  Search,
  GraduationCap,
  Scale,
  UploadCloud,
  FileText,
  Trash2,
  X,
  Layers,
  CheckCircle2,
  Clock,
  AlertCircle,
  Cpu,
  RefreshCw,
} from 'lucide-react';
import {
  fetchDocuments,
  fetchDocumentDetail,
  uploadDocument,
  deleteDocument,
  fetchHealth,
} from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('library');
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [docDetailLoading, setDocDetailLoading] = useState(false);
  const [detailTab, setDetailTab] = useState('chunks'); // 'chunks' | 'pages'
  const [backendHealth, setBackendHealth] = useState(null);
  const [errorToast, setErrorToast] = useState(null);
  const [successToast, setSuccessToast] = useState(null);
  const fileInputRef = useRef(null);

  // Load documents and health on mount
  useEffect(() => {
    loadDocs();
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  async function checkHealth() {
    try {
      const health = await fetchHealth();
      setBackendHealth(health);
    } catch {
      setBackendHealth(null);
    }
  }

  async function loadDocs() {
    try {
      setLoading(true);
      const docs = await fetchDocuments();
      setDocuments(docs);
    } catch (err) {
      showError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function showError(msg) {
    setErrorToast(msg);
    setTimeout(() => setErrorToast(null), 5000);
  }

  function showSuccess(msg) {
    setSuccessToast(msg);
    setTimeout(() => setSuccessToast(null), 4000);
  }

  async function handleFileUpload(files) {
    if (!files || files.length === 0) return;
    const file = files[0];

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      showError('Only PDF files are supported.');
      return;
    }

    try {
      setUploading(true);
      const res = await uploadDocument(file);
      showSuccess(res.message || `Uploaded ${file.name}`);
      await loadDocs();
    } catch (err) {
      showError(err.message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  async function handleOpenDoc(doc) {
    try {
      setDocDetailLoading(true);
      const detail = await fetchDocumentDetail(doc.id);
      setSelectedDoc(detail);
    } catch (err) {
      showError(err.message);
    } finally {
      setDocDetailLoading(false);
    }
  }

  async function handleDeleteDoc(e, id) {
    e.stopPropagation();
    if (!window.confirm('Delete this document and all extracted pages & chunks?')) return;

    try {
      await deleteDocument(id);
      showSuccess('Document deleted successfully.');
      if (selectedDoc?.id === id) setSelectedDoc(null);
      await loadDocs();
    } catch (err) {
      showError(err.message);
    }
  }

  function formatBytes(bytes) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  return (
    <div className="app-container">
      {/* Toast notifications */}
      {errorToast && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '24px',
          backgroundColor: '#ef4444',
          color: '#fff',
          padding: '12px 20px',
          borderRadius: '8px',
          zIndex: 9999,
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '0.88rem'
        }}>
          <AlertCircle size={18} />
          {errorToast}
        </div>
      )}
      {successToast && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '24px',
          backgroundColor: '#10b981',
          color: '#fff',
          padding: '12px 20px',
          borderRadius: '8px',
          zIndex: 9999,
          boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '0.88rem'
        }}>
          <CheckCircle2 size={18} />
          {successToast}
        </div>
      )}

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand-header">
          <div className="brand-icon">
            <BookOpen size={20} />
          </div>
          <div>
            <div className="brand-title">ScholarEdge</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>On-Device AI Copilot</div>
          </div>
        </div>

        <nav className="nav-section">
          <button
            className={`nav-item ${activeTab === 'library' ? 'active' : ''}`}
            onClick={() => setActiveTab('library')}
          >
            <BookOpen size={18} />
            Library
            <span className="nav-badge">{documents.length}</span>
          </button>

          <button
            className={`nav-item ${activeTab === 'research' ? 'active' : ''}`}
            onClick={() => setActiveTab('research')}
          >
            <Search size={18} />
            Research
            <span className="nav-badge" style={{ color: 'var(--accent-amber)' }}>M2</span>
          </button>

          <button
            className={`nav-item ${activeTab === 'compare' ? 'active' : ''}`}
            onClick={() => setActiveTab('compare')}
          >
            <Scale size={18} />
            Compare
            <span className="nav-badge" style={{ color: 'var(--accent-amber)' }}>M3</span>
          </button>

          <button
            className={`nav-item ${activeTab === 'learn' ? 'active' : ''}`}
            onClick={() => setActiveTab('learn')}
          >
            <GraduationCap size={18} />
            Learn
            <span className="nav-badge" style={{ color: 'var(--accent-amber)' }}>M4</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="system-status">
            <span
              className="status-dot"
              style={{ backgroundColor: backendHealth ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}
            />
            <span>
              {backendHealth ? 'Local Engine Connected' : 'Engine Disconnected'}
            </span>
          </div>
          <div style={{ marginTop: '8px', fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Cpu size={14} />
            <span>Target: Snapdragon AI / 8GB RAM</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        <header className="top-bar">
          <div className="top-bar-title">
            {activeTab === 'library' && <>Document Library</>}
            {activeTab === 'research' && <>Grounded Research Mode</>}
            {activeTab === 'compare' && <>Cross-Paper Comparison</>}
            {activeTab === 'learn' && <>Interactive Learning & Quizzes</>}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button className="btn-icon" onClick={loadDocs} title="Refresh documents">
              <RefreshCw size={17} className={loading ? 'spin' : ''} />
            </button>
          </div>
        </header>

        <div className="view-content">
          {activeTab === 'library' && (
            <div>
              <div className="library-header">
                <div>
                  <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Documents & Knowledge Base</h2>
                  <p className="section-desc">
                    Upload PDFs for local page-aware extraction, chunking, and verifiable source references.
                  </p>
                </div>
              </div>

              {/* Upload Dropzone */}
              <div className="dropzone-container">
                <input
                  type="file"
                  accept="application/pdf"
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  onChange={(e) => handleFileUpload(e.target.files)}
                />
                <div
                  className={`dropzone ${uploading ? 'active' : ''}`}
                  onClick={() => !uploading && fileInputRef.current?.click()}
                  onDragOver={(e) => { e.preventDefault(); }}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (!uploading && e.dataTransfer.files) {
                      handleFileUpload(e.dataTransfer.files);
                    }
                  }}
                >
                  <div className="dropzone-icon">
                    <UploadCloud size={24} />
                  </div>
                  <div>
                    <div className="dropzone-title">
                      {uploading ? 'Processing & Extracting Document...' : 'Click or Drag & Drop Research Paper (PDF)'}
                    </div>
                    <div className="dropzone-sub">
                      Preserves page boundaries, extracts text, and indexes chunks locally. Up to 50MB.
                    </div>
                  </div>
                </div>
              </div>

              {/* Document List */}
              {loading && documents.length === 0 ? (
                <div className="empty-state">Loading document library...</div>
              ) : documents.length === 0 ? (
                <div className="empty-state">
                  <FileText size={48} style={{ opacity: 0.3, marginBottom: '12px' }} />
                  <p>No documents uploaded yet.</p>
                  <p style={{ fontSize: '0.85rem', marginTop: '6px' }}>
                    Upload your first research paper or study material above to begin.
                  </p>
                </div>
              ) : (
                <div className="doc-grid">
                  {documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="doc-card"
                      onClick={() => handleOpenDoc(doc)}
                    >
                      <div>
                        <div className="doc-card-header">
                          <div className="doc-icon-wrap">
                            <FileText size={20} />
                          </div>
                          <div className="doc-info">
                            <div className="doc-title" title={doc.title || doc.filename}>
                              {doc.title || doc.filename}
                            </div>
                            <div className="doc-filename">{doc.filename}</div>
                          </div>
                          <button
                            className="btn-icon btn-danger"
                            title="Delete document"
                            onClick={(e) => handleDeleteDoc(e, doc.id)}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>

                        <div>
                          {doc.status === 'INDEXED' && (
                            <span className="badge badge-indexed">
                              <CheckCircle2 size={12} /> Indexed
                            </span>
                          )}
                          {doc.status === 'PROCESSING' && (
                            <span className="badge badge-processing">
                              <Clock size={12} /> Processing
                            </span>
                          )}
                          {doc.status === 'FAILED' && (
                            <span className="badge badge-failed">
                              <AlertCircle size={12} /> Failed
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="doc-meta-row">
                        <div className="meta-item">
                          <Layers size={14} />
                          <span>{doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'}</span>
                        </div>
                        <div className="meta-item">
                          <span>{doc.chunk_count} chunks</span>
                        </div>
                        <div className="meta-item" style={{ marginLeft: 'auto' }}>
                          <span>{formatBytes(doc.file_size)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Research Placeholder */}
          {activeTab === 'research' && (
            <div className="empty-state">
              <Search size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
              <h3>Grounded Research & Multi-Paper Q&A</h3>
              <p style={{ marginTop: '8px', maxWidth: '480px', marginInline: 'auto' }}>
                Phase 1 Document Engine is ready. Phase 2 (M2) will introduce local embeddings, vector retrieval, and source-grounded answers.
              </p>
            </div>
          )}

          {/* Compare Placeholder */}
          {activeTab === 'compare' && (
            <div className="empty-state">
              <Scale size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
              <h3>Cross-Paper Comparative Analysis</h3>
              <p style={{ marginTop: '8px', maxWidth: '480px', marginInline: 'auto' }}>
                Multi-paper comparison across methodologies, datasets, and conclusions (M3).
              </p>
            </div>
          )}

          {/* Learn Placeholder */}
          {activeTab === 'learn' && (
            <div className="empty-state">
              <GraduationCap size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
              <h3>Interactive Learning & Study Mode</h3>
              <p style={{ marginTop: '8px', maxWidth: '480px', marginInline: 'auto' }}>
                Conceptual explanations, automated quiz generation, and active recall assistance (M4).
              </p>
            </div>
          )}
        </div>
      </main>

      {/* Document Detail Inspector Modal */}
      {selectedDoc && (
        <div className="modal-overlay" onClick={() => setSelectedDoc(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>{selectedDoc.title || selectedDoc.filename}</h3>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  ID: {selectedDoc.id} • {selectedDoc.page_count} Pages • {selectedDoc.chunks?.length || 0} Chunks
                </div>
              </div>
              <button className="btn-icon" onClick={() => setSelectedDoc(null)}>
                <X size={20} />
              </button>
            </div>

            <div className="modal-body">
              <div className="tab-list">
                <button
                  className={`tab-btn ${detailTab === 'chunks' ? 'active' : ''}`}
                  onClick={() => setDetailTab('chunks')}
                >
                  Extracted Chunks ({selectedDoc.chunks?.length || 0})
                </button>
                <button
                  className={`tab-btn ${detailTab === 'pages' ? 'active' : ''}`}
                  onClick={() => setDetailTab('pages')}
                >
                  Raw Pages ({selectedDoc.pages?.length || 0})
                </button>
              </div>

              {detailTab === 'chunks' && (
                <div>
                  {selectedDoc.chunks?.length === 0 ? (
                    <div className="empty-state">No chunks generated.</div>
                  ) : (
                    selectedDoc.chunks?.map((chunk) => (
                      <div key={chunk.id} className="chunk-item">
                        <div className="chunk-header">
                          <span>CHUNK #{chunk.chunk_index + 1} — PAGE {chunk.page_number || 'N/A'}</span>
                          {chunk.section && (
                            <span style={{ color: 'var(--accent-cyan)' }}>[{chunk.section}]</span>
                          )}
                        </div>
                        <div className="chunk-text">{chunk.text}</div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {detailTab === 'pages' && (
                <div>
                  {selectedDoc.pages?.length === 0 ? (
                    <div className="empty-state">No pages extracted.</div>
                  ) : (
                    selectedDoc.pages?.map((page) => (
                      <div key={page.id} className="chunk-item">
                        <div className="chunk-header">
                          <span>PAGE {page.page_number}</span>
                          <span>OCR: {page.ocr_used ? 'Yes' : 'No'}</span>
                        </div>
                        <div className="chunk-text">{page.text || '<Blank Page>'}</div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
