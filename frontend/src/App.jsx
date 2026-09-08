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
  Send,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  Filter,
  CheckSquare,
  Square,
  ArrowRight,
} from 'lucide-react';
import {
  fetchDocuments,
  fetchDocumentDetail,
  uploadDocument,
  deleteDocument,
  fetchHealth,
  sendChatQuestion,
  searchDocuments,
  compareDocuments,
} from './api';

const ALL_DIMENSIONS = [
  'Core Objective',
  'Methodology & Architecture',
  'Key Findings & Metrics',
  'Limitations & Future Work',
];

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

  // Research mode state
  const [selectedScope, setSelectedScope] = useState('ALL');
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState([
    {
      id: 'welcome-1',
      sender: 'assistant',
      text: 'Welcome to ScholarEdge Research Copilot. I answer questions grounded strictly in your indexed documents, with explicit citations to source documents and page numbers.',
      sources: [],
      hasSufficientEvidence: true,
    },
  ]);
  const [researchSubTab, setResearchSubTab] = useState('chat'); // 'chat' | 'search'
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);

  // Compare mode state (M3)
  const [selectedCompareDocs, setSelectedCompareDocs] = useState([]);
  const [selectedDimensions, setSelectedDimensions] = useState(ALL_DIMENSIONS);
  const [comparisonResult, setComparisonResult] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);

  const chatBottomRef = useRef(null);

  useEffect(() => {
    loadDocs();
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (activeTab === 'research') {
      chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, activeTab]);

  // Pre-select first 2 documents for comparison if available and none selected
  useEffect(() => {
    if (documents.length >= 2 && selectedCompareDocs.length === 0) {
      setSelectedCompareDocs([documents[0].id, documents[1].id]);
    }
  }, [documents]);

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
      setSelectedCompareDocs((prev) => prev.filter((dId) => dId !== id));
      await loadDocs();
    } catch (err) {
      showError(err.message);
    }
  }

  async function handleSendChat(customText = null) {
    const textToSend = customText || chatInput;
    if (!textToSend.trim() || chatLoading) return;

    const userMsgId = 'user-' + Date.now();
    const newUserMsg = {
      id: userMsgId,
      sender: 'user',
      text: textToSend,
    };

    setChatMessages((prev) => [...prev, newUserMsg]);
    if (!customText) setChatInput('');
    setChatLoading(true);

    try {
      const scopeIds = selectedScope === 'ALL' ? null : [selectedScope];
      const res = await sendChatQuestion(textToSend, scopeIds, 5);

      const assistantMsg = {
        id: 'assistant-' + Date.now(),
        sender: 'assistant',
        text: res.answer,
        sources: res.sources || [],
        hasSufficientEvidence: res.has_sufficient_evidence,
      };

      setChatMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      showError(err.message);
      setChatMessages((prev) => [
        ...prev,
        {
          id: 'error-' + Date.now(),
          sender: 'assistant',
          text: `Error processing query: ${err.message}`,
          sources: [],
          hasSufficientEvidence: false,
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  async function handleSearch(query) {
    if (!query.trim() || searchLoading) return;
    try {
      setSearchLoading(true);
      const scopeIds = selectedScope === 'ALL' ? null : [selectedScope];
      const res = await searchDocuments(query, scopeIds, 8);
      setSearchResults(res.results || []);
    } catch (err) {
      showError(err.message);
    } finally {
      setSearchLoading(false);
    }
  }

  function handleToggleCompareDoc(docId) {
    setSelectedCompareDocs((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  }

  function handleToggleDimension(dim) {
    setSelectedDimensions((prev) =>
      prev.includes(dim)
        ? prev.length > 1
          ? prev.filter((d) => d !== dim)
          : prev
        : [...prev, dim]
    );
  }

  async function handleRunComparison() {
    if (selectedCompareDocs.length < 2) {
      showError('Please select at least two research papers to compare.');
      return;
    }
    try {
      setCompareLoading(true);
      const res = await compareDocuments(selectedCompareDocs, selectedDimensions);
      setComparisonResult(res);
      showSuccess(`Successfully compared ${res.comparisons.length} documents.`);
    } catch (err) {
      showError(err.message);
    } finally {
      setCompareLoading(false);
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
            Research (RAG)
            <span className="nav-badge" style={{ color: 'var(--accent-emerald)', borderColor: 'var(--accent-emerald)' }}>Active</span>
          </button>

          <button
            className={`nav-item ${activeTab === 'compare' ? 'active' : ''}`}
            onClick={() => setActiveTab('compare')}
          >
            <Scale size={18} />
            Compare
            <span className="nav-badge" style={{ color: 'var(--accent-emerald)', borderColor: 'var(--accent-emerald)' }}>Active</span>
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
            {activeTab === 'research' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <span>Grounded Research Studio</span>
                <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-tertiary)', padding: '3px', borderRadius: '8px' }}>
                  <button
                    className={`tab-btn ${researchSubTab === 'chat' ? 'active' : ''}`}
                    style={{ padding: '4px 12px', fontSize: '0.8rem' }}
                    onClick={() => setResearchSubTab('chat')}
                  >
                    Grounded Chat
                  </button>
                  <button
                    className={`tab-btn ${researchSubTab === 'search' ? 'active' : ''}`}
                    style={{ padding: '4px 12px', fontSize: '0.8rem' }}
                    onClick={() => setResearchSubTab('search')}
                  >
                    Semantic Retrieval
                  </button>
                </div>
              </div>
            )}
            {activeTab === 'compare' && <>Cross-Paper Comparison Studio (M3)</>}
            {activeTab === 'learn' && <>Interactive Learning & Quizzes</>}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button className="btn-icon" onClick={loadDocs} title="Refresh documents">
              <RefreshCw size={17} className={loading ? 'spin' : ''} />
            </button>
          </div>
        </header>

        <div className="view-content">
          {/* LIBRARY TAB */}
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

          {/* RESEARCH (RAG) TAB */}
          {activeTab === 'research' && (
            <div className="research-container">
              {/* Header with Scope Filter */}
              <div className="research-header">
                <div className="scope-bar">
                  <Filter size={16} />
                  <span>Research Scope:</span>
                  <select
                    className="scope-select"
                    value={selectedScope}
                    onChange={(e) => setSelectedScope(e.target.value)}
                  >
                    <option value="ALL">All Documents in Library ({documents.length})</option>
                    {documents.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.title || d.filename}
                      </option>
                    ))}
                  </select>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: 'var(--accent-emerald)' }}>
                  <ShieldCheck size={16} />
                  <span>Source Grounding Active (Refusal on unverified facts)</span>
                </div>
              </div>

              {/* Subtab 1: Grounded Chat */}
              {researchSubTab === 'chat' && (
                <>
                  <div className="chat-scroll">
                    {chatMessages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`chat-message ${msg.sender === 'user' ? 'user' : 'assistant'}`}
                      >
                        {msg.sender === 'user' ? (
                          <div className="user-bubble">{msg.text}</div>
                        ) : (
                          <div className="assistant-card">
                            <div className="assistant-header">
                              <Sparkles size={16} />
                              <span>ScholarEdge Evidence Synthesis</span>
                            </div>
                            <div className="assistant-text">{msg.text}</div>

                            {!msg.hasSufficientEvidence && msg.id !== 'welcome-1' && (
                              <div className="insufficient-alert">
                                <AlertCircle size={20} style={{ flexShrink: 0 }} />
                                <div>
                                  <strong>Insufficient Evidence Detected:</strong>
                                  <div>
                                    The indexed documents do not contain authoritative evidence on this topic. ScholarEdge refuses to fabricate ungrounded claims.
                                  </div>
                                </div>
                              </div>
                            )}

                            {msg.sources && msg.sources.length > 0 && (
                              <div className="sources-panel">
                                <div className="sources-label">
                                  <BookOpen size={14} />
                                  <span>Retrieved Evidence ({msg.sources.length} sources)</span>
                                </div>
                                <div className="source-cards-grid">
                                  {msg.sources.map((src, idx) => (
                                    <div
                                      key={src.chunk_id || idx}
                                      className="source-card"
                                      onClick={() => {
                                        const docMatch = documents.find((d) => d.id === src.document_id);
                                        if (docMatch) handleOpenDoc(docMatch);
                                      }}
                                      title="Click to view in document inspector"
                                    >
                                      <div className="source-card-top">
                                        <span>PAGE {src.page_number} {src.section ? `• ${src.section}` : ''}</span>
                                        <span className="source-score">sim: {src.relevance_score}</span>
                                      </div>
                                      <div className="source-card-title">{src.document_title}</div>
                                      <div className="source-card-snippet">"{src.excerpt}"</div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                    {chatLoading && (
                      <div className="chat-message assistant">
                        <div className="assistant-card" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <RefreshCw size={18} className="spin" style={{ color: 'var(--accent-cyan)' }} />
                          <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                            Retrieving vectors and synthesizing grounded response...
                          </span>
                        </div>
                      </div>
                    )}
                    <div ref={chatBottomRef} />
                  </div>

                  {/* Prompt Suggestion Chips */}
                  <div className="prompt-chips">
                    <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)', alignSelf: 'center' }}>Quick queries:</span>
                    <button
                      className="chip-btn"
                      onClick={() => handleSendChat('What are the latency benefits of on-device NPU inference?')}
                    >
                      Latency benefits on NPU?
                    </button>
                    <button
                      className="chip-btn"
                      onClick={() => handleSendChat('How is citation traceability verified in RAG?')}
                    >
                      Citation traceability?
                    </button>
                    <button
                      className="chip-btn"
                      onClick={() => handleSendChat('What were the student test results for quiz generation?')}
                    >
                      Quiz retention results?
                    </button>
                    <button
                      className="chip-btn"
                      onClick={() => handleSendChat('What is the weather like on Mars today?')}
                    >
                      Test refusal (Mars weather)
                    </button>
                  </div>

                  {/* Chat Input Bar */}
                  <div className="chat-input-bar">
                    <input
                      type="text"
                      className="chat-input-field"
                      placeholder="Ask a question across your research library..."
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSendChat()}
                      disabled={chatLoading}
                    />
                    <button
                      className="send-btn"
                      onClick={() => handleSendChat()}
                      disabled={chatLoading || !chatInput.trim()}
                      title="Send question"
                    >
                      <Send size={18} />
                    </button>
                  </div>
                </>
              )}

              {/* Subtab 2: Semantic Retrieval Inspector */}
              {researchSubTab === 'search' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div className="chat-input-bar">
                    <input
                      type="text"
                      className="chat-input-field"
                      placeholder="Enter search query to inspect raw vector similarity..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSearch(searchQuery)}
                    />
                    <button
                      className="send-btn"
                      onClick={() => handleSearch(searchQuery)}
                      disabled={searchLoading || !searchQuery.trim()}
                    >
                      <Search size={18} />
                    </button>
                  </div>

                  {searchLoading && <div className="empty-state">Searching vector store...</div>}

                  {!searchLoading && searchResults.length === 0 && searchQuery && (
                    <div className="empty-state">No chunks matched the similarity threshold.</div>
                  )}

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {searchResults.map((res, idx) => (
                      <div key={res.chunk_id || idx} className="chunk-item">
                        <div className="chunk-header">
                          <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>
                            HIT #{idx + 1} — {res.document_title} (PAGE {res.page_number})
                          </span>
                          <span className="source-score">cosine similarity: {res.relevance_score}</span>
                        </div>
                        {res.section && (
                          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                            Section: [{res.section}]
                          </div>
                        )}
                        <div className="chunk-text">{res.excerpt}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* COMPARE TAB (M3) */}
          {activeTab === 'compare' && (
            <div className="compare-container">
              {/* Setup / Configuration Panel */}
              <div className="compare-setup-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Select Research Papers to Compare</h3>
                    <p className="section-desc">
                      Choose at least two indexed papers for side-by-side dimensional contrast and synthesis.
                    </p>
                  </div>
                  <button
                    className="compare-btn-primary"
                    disabled={selectedCompareDocs.length < 2 || compareLoading}
                    onClick={handleRunComparison}
                  >
                    <Scale size={18} />
                    {compareLoading ? 'Synthesizing...' : `Compare Selected (${selectedCompareDocs.length})`}
                  </button>
                </div>

                {/* Paper Selection Grid */}
                {documents.length < 2 ? (
                  <div className="empty-state" style={{ padding: '30px 0' }}>
                    <p>At least two papers must be indexed in your library to compare.</p>
                    <button
                      className="chip-btn"
                      style={{ marginTop: '12px', padding: '6px 14px' }}
                      onClick={() => setActiveTab('library')}
                    >
                      Go to Library to upload more papers
                    </button>
                  </div>
                ) : (
                  <div className="paper-checklist-grid">
                    {documents.map((doc) => {
                      const isSelected = selectedCompareDocs.includes(doc.id);
                      return (
                        <div
                          key={doc.id}
                          className={`paper-check-card ${isSelected ? 'selected' : ''}`}
                          onClick={() => handleToggleCompareDoc(doc.id)}
                        >
                          <div style={{ color: isSelected ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
                            {isSelected ? <CheckSquare size={18} /> : <Square size={18} />}
                          </div>
                          <div style={{ overflow: 'hidden' }}>
                            <div className="doc-title" style={{ fontSize: '0.86rem' }}>
                              {doc.title || doc.filename}
                            </div>
                            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                              {doc.page_count} pages • {doc.chunk_count} chunks
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Dimensions Selector */}
                <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid rgba(255, 255, 255, 0.05)' }}>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '8px', fontWeight: 600 }}>
                    Active Comparison Dimensions:
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {ALL_DIMENSIONS.map((dim) => {
                      const isActive = selectedDimensions.includes(dim);
                      return (
                        <button
                          key={dim}
                          className={`chip-btn ${isActive ? 'active' : ''}`}
                          style={{
                            background: isActive ? 'rgba(56, 189, 248, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                            borderColor: isActive ? 'var(--accent-cyan)' : 'var(--border-subtle)',
                            color: isActive ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                          }}
                          onClick={() => handleToggleDimension(dim)}
                        >
                          {dim}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Comparison Results */}
              {comparisonResult && (
                <>
                  {/* Synthesis Callout Card */}
                  <div className="synthesis-card">
                    <div className="synthesis-header">
                      <Sparkles size={20} />
                      <span>Comparative Synthesis & Trade-off Analysis</span>
                    </div>
                    <div className="synthesis-body">{comparisonResult.synthesis}</div>
                  </div>

                  {/* Side-by-Side Matrix Table */}
                  <div className="matrix-container">
                    <table className="matrix-table">
                      <thead>
                        <tr>
                          <th className="matrix-th matrix-dim-col">Dimension</th>
                          {comparisonResult.comparisons.map((c) => (
                            <th key={c.document_id} className="matrix-th">
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <FileText size={16} style={{ color: 'var(--accent-cyan)' }} />
                                <span>{c.document_title}</span>
                              </div>
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {comparisonResult.dimensions.map((dim) => (
                          <tr key={dim}>
                            <td className="matrix-td matrix-dim-col">{dim}</td>
                            {comparisonResult.comparisons.map((c) => {
                              const cellValue = c.dimension_values[dim] || 'N/A';
                              return (
                                <td key={c.document_id + dim} className="matrix-td">
                                  <div>{cellValue}</div>
                                  <div
                                    className="citation-pill"
                                    onClick={() => {
                                      const fullDoc = documents.find((d) => d.id === c.document_id);
                                      if (fullDoc) handleOpenDoc(fullDoc);
                                    }}
                                    title="Open document inspector"
                                  >
                                    Inspect Source Excerpt →
                                  </div>
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          )}

          {/* LEARN TAB (M4) */}
          {activeTab === 'learn' && (
            <div className="empty-state">
              <GraduationCap size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
              <h3>Interactive Learning & Study Mode</h3>
              <p style={{ marginTop: '8px', maxWidth: '480px', marginInline: 'auto' }}>
                Conceptual explanations, automated quiz generation, and active recall assistance (Coming in Phase 4 / M4).
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
