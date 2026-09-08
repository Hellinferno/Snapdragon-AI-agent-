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
  HelpCircle,
  Award,
  RotateCw,
  ChevronRight,
  ChevronLeft,
  Image as ImageIcon,
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
  explainConcept,
  generateQuiz,
  generateFlashcards,
  uploadVisionImage,
  analyzeFigure,
  chatWithFigure,
  getVisionImageUrl,
  seedDemoDataset,
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
  const [seedingDemo, setSeedingDemo] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [docDetailLoading, setDocDetailLoading] = useState(false);
  const [detailTab, setDetailTab] = useState('chunks'); // 'chunks' | 'pages'
  const [backendHealth, setBackendHealth] = useState(null);
  const [errorToast, setErrorToast] = useState(null);
  const [successToast, setSuccessToast] = useState(null);
  const fileInputRef = useRef(null);

  // Research mode state (M2)
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

  // Learn mode state (M4)
  const [learnSubTab, setLearnSubTab] = useState('explain'); // 'explain' | 'quiz' | 'flashcards'
  const [explainConceptText, setExplainConceptText] = useState('Quantized Transformer Inference');
  const [explainLevel, setExplainLevel] = useState('beginner');
  const [explanationResult, setExplanationResult] = useState(null);
  const [explainLoading, setExplainLoading] = useState(false);

  const [quizData, setQuizData] = useState(null);
  const [userAnswers, setUserAnswers] = useState({});
  const [quizLoading, setQuizLoading] = useState(false);

  const [flashcardDeck, setFlashcardDeck] = useState([]);
  const [currentFcIdx, setCurrentFcIdx] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [flashcardsLoading, setFlashcardsLoading] = useState(false);

  // Vision mode state (M5)
  const [visionImage, setVisionImage] = useState(null);
  const [visionAnalysis, setVisionAnalysis] = useState(null);
  const [visionUploading, setVisionUploading] = useState(false);
  const [visionAnalyzing, setVisionAnalyzing] = useState(false);
  const [visionChatLoading, setVisionChatLoading] = useState(false);
  const [visionChatInput, setVisionChatInput] = useState('');
  const [visionChatMessages, setVisionChatMessages] = useState([]);
  const visionFileInputRef = useRef(null);
  const visionChatBottomRef = useRef(null);

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

  useEffect(() => {
    if (activeTab === 'vision') {
      visionChatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [visionChatMessages, activeTab]);

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

  async function handleSeedDemo() {
    try {
      setSeedingDemo(true);
      const res = await seedDemoDataset();
      showSuccess(res.message);
      await loadDocs();
    } catch (err) {
      showError(err.message);
    } finally {
      setSeedingDemo(false);
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

  async function handleExplain() {
    if (!explainConceptText.trim() || explainLoading) return;
    try {
      setExplainLoading(true);
      const scopeIds = selectedScope === 'ALL' ? null : [selectedScope];
      const res = await explainConcept(explainConceptText, scopeIds, explainLevel);
      setExplanationResult(res);
    } catch (err) {
      showError(err.message);
    } finally {
      setExplainLoading(false);
    }
  }

  async function handleGenerateQuiz() {
    try {
      setQuizLoading(true);
      setUserAnswers({});
      const scopeIds = selectedScope === 'ALL' ? null : [selectedScope];
      const res = await generateQuiz(scopeIds, 4, 'medium');
      setQuizData(res);
      showSuccess('Quiz generated with source citations.');
    } catch (err) {
      showError(err.message);
    } finally {
      setQuizLoading(false);
    }
  }

  async function handleLoadFlashcards() {
    try {
      setFlashcardsLoading(true);
      setIsFlipped(false);
      setCurrentFcIdx(0);
      const res = await generateFlashcards();
      setFlashcardDeck(res.flashcards || []);
      showSuccess('Loaded study flashcard deck.');
    } catch (err) {
      showError(err.message);
    } finally {
      setFlashcardsLoading(false);
    }
  }

  async function handleVisionUpload(file) {
    if (!file) return;
    try {
      setVisionUploading(true);
      const uploaded = await uploadVisionImage(file);
      setVisionImage(uploaded);
      showSuccess(`Figure '${uploaded.filename}' uploaded (${uploaded.width}x${uploaded.height}). Analyzing...`);

      setVisionAnalyzing(true);
      const analysis = await analyzeFigure(uploaded.id);
      setVisionAnalysis(analysis);
      setVisionChatMessages([
        {
          id: 'vision-welcome',
          sender: 'assistant',
          text: `Figure "${analysis.title}" analyzed as ${analysis.figure_type.toUpperCase()} with ${(analysis.confidence_score * 100).toFixed(0)}% confidence. You can now ask questions about trends, methodology, or observations.`,
        },
      ]);
    } catch (err) {
      showError(err.message);
    } finally {
      setVisionUploading(false);
      setVisionAnalyzing(false);
    }
  }

  async function handleVisionChat(customText = null) {
    const text = customText || visionChatInput;
    if (!text.trim() || !visionImage || visionChatLoading) return;

    const userMsg = { id: 'u-' + Date.now(), sender: 'user', text };
    setVisionChatMessages((prev) => [...prev, userMsg]);
    if (!customText) setVisionChatInput('');
    setVisionChatLoading(true);

    try {
      const res = await chatWithFigure(visionImage.id, text);
      const assistantMsg = {
        id: 'a-' + Date.now(),
        sender: 'assistant',
        text: res.answer,
      };
      setVisionChatMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      showError(err.message);
      setVisionChatMessages((prev) => [
        ...prev,
        { id: 'err-' + Date.now(), sender: 'assistant', text: `Error: ${err.message}` },
      ]);
    } finally {
      setVisionChatLoading(false);
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

        <nav className="nav-section" role="tablist" aria-label="Studio Navigation Tabs">
          <button
            role="tab"
            aria-selected={activeTab === 'library'}
            aria-label={`Document Library, ${documents.length} documents`}
            className={`nav-item ${activeTab === 'library' ? 'active' : ''}`}
            onClick={() => setActiveTab('library')}
          >
            <BookOpen size={18} />
            Library
            <span className="nav-badge">{documents.length}</span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'research'}
            aria-label="Research RAG Studio"
            className={`nav-item ${activeTab === 'research' ? 'active' : ''}`}
            onClick={() => setActiveTab('research')}
          >
            <Search size={18} />
            Research (RAG)
            <span className="nav-badge" style={{ color: 'var(--accent-emerald)', borderColor: 'var(--accent-emerald)' }}>Active</span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'compare'}
            aria-label="Cross-Paper Comparison Studio"
            className={`nav-item ${activeTab === 'compare' ? 'active' : ''}`}
            onClick={() => setActiveTab('compare')}
          >
            <Scale size={18} />
            Compare
            <span className="nav-badge" style={{ color: 'var(--accent-emerald)', borderColor: 'var(--accent-emerald)' }}>Active</span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'learn'}
            aria-label="Learning and Quiz Studio"
            className={`nav-item ${activeTab === 'learn' ? 'active' : ''}`}
            onClick={() => setActiveTab('learn')}
          >
            <GraduationCap size={18} />
            Learn
            <span className="nav-badge" style={{ color: 'var(--accent-emerald)', borderColor: 'var(--accent-emerald)' }}>Active</span>
          </button>

          <button
            role="tab"
            aria-selected={activeTab === 'vision'}
            aria-label="Vision Figure and Diagram Studio"
            className={`nav-item ${activeTab === 'vision' ? 'active' : ''}`}
            onClick={() => setActiveTab('vision')}
          >
            <ImageIcon size={18} />
            Vision (Figures)
            <span className="nav-badge" style={{ color: 'var(--accent-cyan)', borderColor: 'var(--accent-cyan)' }}>Active</span>
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
            {activeTab === 'learn' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <span>Learning & Formative Assessment Studio (M4)</span>
                <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-tertiary)', padding: '3px', borderRadius: '8px' }}>
                  <button
                    className={`tab-btn ${learnSubTab === 'explain' ? 'active' : ''}`}
                    style={{ padding: '4px 12px', fontSize: '0.8rem' }}
                    onClick={() => setLearnSubTab('explain')}
                  >
                    Concept Explainer
                  </button>
                  <button
                    className={`tab-btn ${learnSubTab === 'quiz' ? 'active' : ''}`}
                    style={{ padding: '4px 12px', fontSize: '0.8rem' }}
                    onClick={() => {
                      setLearnSubTab('quiz');
                      if (!quizData) handleGenerateQuiz();
                    }}
                  >
                    Interactive Quiz
                  </button>
                  <button
                    className={`tab-btn ${learnSubTab === 'flashcards' ? 'active' : ''}`}
                    style={{ padding: '4px 12px', fontSize: '0.8rem' }}
                    onClick={() => {
                      setLearnSubTab('flashcards');
                      if (flashcardDeck.length === 0) handleLoadFlashcards();
                    }}
                  >
                    Flashcards Deck
                  </button>
                </div>
              </div>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button className="btn-icon" onClick={loadDocs} title="Refresh documents" aria-label="Refresh documents">
              <RefreshCw size={17} className={loading ? 'spin' : ''} />
            </button>
          </div>
        </header>

        <div className="view-content">
          {/* LIBRARY TAB */}
          {activeTab === 'library' && (
            <div>
              <div className="library-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
                <div>
                  <h2 style={{ fontSize: '1.4rem', fontWeight: 700 }}>Documents & Knowledge Base</h2>
                  <p className="section-desc">
                    Upload PDFs for local page-aware extraction, chunking, and verifiable source references.
                  </p>
                </div>
                <button
                  className="primary-btn"
                  disabled={seedingDemo || uploading}
                  onClick={handleSeedDemo}
                  style={{
                    background: 'linear-gradient(135deg, var(--accent-emerald), #059669)',
                    borderColor: 'transparent',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '0.85rem',
                  }}
                  title="Seed 3 sample academic research papers and 1 architecture diagram"
                >
                  {seedingDemo ? (
                    <>
                      <RefreshCw size={15} className="spin" /> Seeding Demo Data...
                    </>
                  ) : (
                    <>
                      <Sparkles size={15} /> Load Demo Papers (1-Click)
                    </>
                  )}
                </button>
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
                  <p style={{ fontWeight: 600, fontSize: '1.05rem' }}>No documents in your library yet.</p>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginTop: '6px', maxWidth: '440px' }}>
                    Upload your own PDF research papers, or click below to populate the workspace with pre-formatted academic papers.
                  </p>
                  <div style={{ display: 'flex', gap: '12px', marginTop: '16px', flexWrap: 'wrap', justifyContent: 'center' }}>
                    <button
                      className="primary-btn"
                      disabled={seedingDemo}
                      onClick={handleSeedDemo}
                      style={{
                        background: 'linear-gradient(135deg, var(--accent-emerald), #059669)',
                        borderColor: 'transparent',
                      }}
                    >
                      {seedingDemo ? (
                        <>
                          <RefreshCw size={15} className="spin" /> Seeding Dataset...
                        </>
                      ) : (
                        <>
                          <Sparkles size={15} /> Load 3 Academic Demo Papers
                        </>
                      )}
                    </button>
                    <button
                      className="chip-btn"
                      onClick={() => fileInputRef.current?.click()}
                    >
                      <UploadCloud size={15} /> Browse PDF
                    </button>
                  </div>
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
            <div className="learn-container">
              {/* SUBTAB 1: CONCEPT EXPLAINER */}
              {learnSubTab === 'explain' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div className="learn-setup-card">
                    <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Source-Grounded Concept Explainer</h3>
                    <p className="section-desc">
                      Demystify complex technical mechanisms using your indexed papers. Select your target depth.
                    </p>

                    <div className="depth-selector">
                      <button
                        className={`depth-btn ${explainLevel === 'beginner' ? 'active' : ''}`}
                        onClick={() => setExplainLevel('beginner')}
                      >
                        <div className="depth-title">Beginner</div>
                        <div className="depth-desc">Intuitive analogies & simple conceptual frameworks</div>
                      </button>
                      <button
                        className={`depth-btn ${explainLevel === 'intermediate' ? 'active' : ''}`}
                        onClick={() => setExplainLevel('intermediate')}
                      >
                        <div className="depth-title">Intermediate</div>
                        <div className="depth-desc">Core architectures, equations, and engineering flow</div>
                      </button>
                      <button
                        className={`depth-btn ${explainLevel === 'deep_dive' ? 'active' : ''}`}
                        onClick={() => setExplainLevel('deep_dive')}
                      >
                        <div className="depth-title">Deep Dive</div>
                        <div className="depth-desc">Optimization nuances, hardware constraints, metrics</div>
                      </button>
                    </div>

                    <div className="chat-input-bar" style={{ marginTop: '14px' }}>
                      <input
                        type="text"
                        className="chat-input-field"
                        placeholder="Enter concept (e.g. INT4 Quantization, Vector Retrieval)..."
                        value={explainConceptText}
                        onChange={(e) => setExplainConceptText(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleExplain()}
                      />
                      <button
                        className="send-btn"
                        onClick={handleExplain}
                        disabled={explainLoading || !explainConceptText.trim()}
                      >
                        <Sparkles size={18} />
                      </button>
                    </div>
                  </div>

                  {explainLoading && <div className="empty-state">Synthesizing grounded explanation...</div>}

                  {explanationResult && (
                    <div className="assistant-card">
                      <div className="assistant-header">
                        <Award size={16} />
                        <span>Pedagogical Breakdown ({explanationResult.level.toUpperCase()})</span>
                      </div>
                      <div className="assistant-text">{explanationResult.explanation}</div>

                      {explanationResult.key_takeaways.length > 0 && (
                        <div className="takeaways-box">
                          <div className="takeaways-title">
                            <CheckCircle2 size={15} />
                            <span>Key Takeaways</span>
                          </div>
                          <ul style={{ paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                            {explanationResult.key_takeaways.map((takeaway, i) => (
                              <li key={i} style={{ fontSize: '0.86rem', color: '#e2e8f0' }}>{takeaway}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {explanationResult.sources.length > 0 && (
                        <div className="sources-panel">
                          <div className="sources-label">
                            <BookOpen size={14} />
                            <span>Supporting Evidence</span>
                          </div>
                          <div className="source-cards-grid">
                            {explanationResult.sources.map((src, i) => (
                              <div
                                key={i}
                                className="source-card"
                                onClick={() => {
                                  const docMatch = documents.find((d) => d.id === src.document_id);
                                  if (docMatch) handleOpenDoc(docMatch);
                                }}
                              >
                                <div className="source-card-top">
                                  <span>PAGE {src.page_number}</span>
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
              )}

              {/* SUBTAB 2: INTERACTIVE QUIZ */}
              {learnSubTab === 'quiz' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div className="learn-setup-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Interactive Formative Assessment</h3>
                      <p className="section-desc">
                        Active recall questions automatically generated from your library's peer-reviewed papers.
                      </p>
                    </div>
                    <button
                      className="compare-btn-primary"
                      onClick={handleGenerateQuiz}
                      disabled={quizLoading}
                    >
                      <RotateCw size={17} className={quizLoading ? 'spin' : ''} />
                      {quizLoading ? 'Generating...' : 'Regenerate Quiz'}
                    </button>
                  </div>

                  {quizData && quizData.questions && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      {quizData.questions.map((q, qIdx) => {
                        const selectedAns = userAnswers[qIdx];
                        const isAnswered = selectedAns !== undefined;

                        return (
                          <div key={q.id} className="quiz-question-box">
                            <div className="quiz-header-row">
                              <span>QUESTION #{qIdx + 1} OF {quizData.questions.length}</span>
                              <span className="badge badge-indexed">{quizData.difficulty.toUpperCase()}</span>
                            </div>
                            <div className="quiz-question-text">{q.question}</div>

                            <div className="quiz-options-list">
                              {q.options.map((opt, optIdx) => {
                                let btnClass = 'quiz-option-btn';
                                if (isAnswered) {
                                  if (optIdx === q.correct_answer_index) {
                                    btnClass += ' correct';
                                  } else if (selectedAns === optIdx) {
                                    btnClass += ' incorrect';
                                  }
                                }

                                return (
                                  <button
                                    key={optIdx}
                                    className={btnClass}
                                    disabled={isAnswered}
                                    onClick={() => setUserAnswers((prev) => ({ ...prev, [qIdx]: optIdx }))}
                                  >
                                    <span style={{ fontWeight: 700, minWidth: '20px' }}>
                                      {String.fromCharCode(65 + optIdx)}.
                                    </span>
                                    <span>{opt}</span>
                                  </button>
                                );
                              })}
                            </div>

                            {isAnswered && (
                              <div className="quiz-explanation-box">
                                <div style={{ fontWeight: 700, marginBottom: '4px', color: selectedAns === q.correct_answer_index ? 'var(--accent-emerald)' : 'var(--accent-rose)' }}>
                                  {selectedAns === q.correct_answer_index ? '✓ Correct Answer' : '✗ Incorrect'}
                                </div>
                                <div>{q.explanation}</div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* SUBTAB 3: FLASHCARDS */}
              {learnSubTab === 'flashcards' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div className="learn-setup-card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Active Recall Flashcard Deck</h3>
                      <p className="section-desc">
                        Spaced repetition cards generated from indexed findings. Click card to flip.
                      </p>
                    </div>
                    <button
                      className="compare-btn-primary"
                      onClick={handleLoadFlashcards}
                      disabled={flashcardsLoading}
                    >
                      <RotateCw size={17} className={flashcardsLoading ? 'spin' : ''} />
                      {flashcardsLoading ? 'Loading...' : 'Refresh Deck'}
                    </button>
                  </div>

                  {flashcardDeck.length > 0 && (
                    <div>
                      <div
                        className="flashcard-card"
                        onClick={() => setIsFlipped((prev) => !prev)}
                      >
                        <div className="flashcard-tag">
                          {isFlipped ? 'Answer (Verified Finding)' : 'Prompt (Active Recall)'}
                        </div>
                        <div className="flashcard-content">
                          {isFlipped
                            ? flashcardDeck[currentFcIdx].back_answer
                            : flashcardDeck[currentFcIdx].front_prompt}
                        </div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          {isFlipped ? `Source: ${flashcardDeck[currentFcIdx].source_hint}` : 'Click card to flip ↺'}
                        </div>
                      </div>

                      {/* Flashcard Navigation */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '16px' }}>
                        <button
                          className="chip-btn"
                          disabled={currentFcIdx === 0}
                          onClick={() => {
                            setIsFlipped(false);
                            setCurrentFcIdx((i) => Math.max(0, i - 1));
                          }}
                        >
                          <ChevronLeft size={16} /> Previous Card
                        </button>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                          Card {currentFcIdx + 1} of {flashcardDeck.length}
                        </span>
                        <button
                          className="chip-btn"
                          disabled={currentFcIdx >= flashcardDeck.length - 1}
                          onClick={() => {
                            setIsFlipped(false);
                            setCurrentFcIdx((i) => Math.min(flashcardDeck.length - 1, i + 1));
                          }}
                        >
                          Next Card <ChevronRight size={16} />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ================================================================= */}
          {/* TAB 5: VISION MODE (M5)                                            */}
          {/* ================================================================= */}
          {activeTab === 'vision' && (
            <div className="vision-container">
              {/* Header & Upload Bar */}
              <div className="vision-upload-bar">
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <div
                    style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: '8px',
                      background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-blue))',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#fff',
                    }}
                  >
                    <ImageIcon size={20} />
                  </div>
                  <div>
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 600 }}>Figure & Diagram Visual Studio</h3>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Local multimodal analysis of research charts, architectures, ROC curves, and tables with zero external API calls.
                    </p>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <input
                    type="file"
                    ref={visionFileInputRef}
                    style={{ display: 'none' }}
                    accept="image/png,image/jpeg,image/webp"
                    onChange={(e) => {
                      if (e.target.files?.[0]) {
                        handleVisionUpload(e.target.files[0]);
                        e.target.value = '';
                      }
                    }}
                  />
                  <button
                    className="primary-btn"
                    disabled={visionUploading || visionAnalyzing}
                    onClick={() => visionFileInputRef.current?.click()}
                  >
                    {visionUploading ? (
                      <>
                        <RefreshCw size={16} className="spin" /> Uploading...
                      </>
                    ) : visionAnalyzing ? (
                      <>
                        <RefreshCw size={16} className="spin" /> Analyzing...
                      </>
                    ) : (
                      <>
                        <UploadCloud size={16} /> Upload Research Figure
                      </>
                    )}
                  </button>
                </div>
              </div>

              {!visionImage ? (
                <div
                  className="upload-dropzone"
                  style={{ minHeight: '320px', cursor: 'pointer' }}
                  onClick={() => visionFileInputRef.current?.click()}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer.files?.[0]) {
                      handleVisionUpload(e.dataTransfer.files[0]);
                    }
                  }}
                >
                  <div className="dropzone-icon">
                    <ImageIcon size={48} />
                  </div>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: 600, marginBottom: '8px' }}>
                    Upload a Paper Figure, Architecture, or Plot
                  </h3>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '440px', marginBottom: '16px' }}>
                    Drag & drop PNG, JPEG, or WebP screenshots of architecture diagrams, benchmark charts, or tables for automated decomposition.
                  </p>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <span className="nav-badge">PNG</span>
                    <span className="nav-badge">JPEG</span>
                    <span className="nav-badge">WebP</span>
                    <span className="nav-badge">Local-First</span>
                  </div>
                </div>
              ) : (
                <div className="vision-workspace">
                  {/* Left Column: Image Preview & Visual Decomposition */}
                  <div className="figure-preview-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="nav-badge" style={{ color: 'var(--accent-cyan)', borderColor: 'var(--accent-cyan)' }}>
                          {visionAnalysis?.figure_type || 'FIGURE'}
                        </span>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                          {visionImage.filename}
                        </span>
                      </div>
                      <button
                        className="chip-btn"
                        onClick={() => {
                          setVisionImage(null);
                          setVisionAnalysis(null);
                          setVisionChatMessages([]);
                        }}
                      >
                        <X size={14} /> Clear
                      </button>
                    </div>

                    <div className="figure-image-container">
                      <img
                        src={getVisionImageUrl(visionImage.id)}
                        alt={visionAnalysis?.title || visionImage.filename}
                      />
                    </div>

                    {/* Telemetry Info */}
                    <div className="figure-telemetry-grid">
                      <div className="telemetry-item">
                        <div className="telemetry-label">Resolution</div>
                        <div className="telemetry-value">{visionImage.width} × {visionImage.height}</div>
                      </div>
                      <div className="telemetry-item">
                        <div className="telemetry-label">Aspect Ratio</div>
                        <div className="telemetry-value">{visionImage.aspect_ratio.toFixed(2)} : 1</div>
                      </div>
                      <div className="telemetry-item">
                        <div className="telemetry-label">Format / Mode</div>
                        <div className="telemetry-value">{visionImage.format} ({visionImage.mode})</div>
                      </div>
                      <div className="telemetry-item">
                        <div className="telemetry-label">Confidence</div>
                        <div className="telemetry-value" style={{ color: 'var(--accent-emerald)' }}>
                          {((visionAnalysis?.confidence_score || 0.85) * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>

                    {/* Insights & Decomposition */}
                    <div className="figure-insights-card">
                      <h4 style={{ fontSize: '0.92rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <Sparkles size={16} style={{ color: 'var(--accent-cyan)' }} />
                        {visionAnalysis?.title || 'Visual Analysis'}
                      </h4>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {visionAnalysis?.key_observations?.map((obs, idx) => (
                          <div key={idx} className="observation-row">
                            <span className="observation-bullet">✦</span>
                            <span>{obs}</span>
                          </div>
                        ))}
                      </div>

                      {visionAnalysis?.axes_or_labels?.length > 0 && (
                        <div style={{ marginTop: '10px' }}>
                          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            Extracted Axes, Labels & Headers
                          </div>
                          <div className="labels-tag-cloud">
                            {visionAnalysis.axes_or_labels.map((lbl, idx) => (
                              <span key={idx} className="label-tag">
                                {lbl}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right Column: Visual QA Chat */}
                  <div className="vision-chat-card">
                    <div className="vision-chat-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <GraduationCap size={18} style={{ color: 'var(--accent-cyan)' }} />
                        <span style={{ fontWeight: 600, fontSize: '0.92rem' }}>Figure Visual Q&A</span>
                      </div>
                      <span className="nav-badge" style={{ color: 'var(--accent-emerald)', borderColor: 'var(--accent-emerald)' }}>
                        Provider: DevelopmentVision
                      </span>
                    </div>

                    {/* Quick Prompts */}
                    <div className="vision-quick-prompts">
                      <button
                        className="quick-prompt-btn"
                        onClick={() => handleVisionChat('What is the primary trend or structural relationship shown?')}
                      >
                        Trend Analysis
                      </button>
                      <button
                        className="quick-prompt-btn"
                        onClick={() => handleVisionChat('Explain the detected axes, headers, and coordinate methodology.')}
                      >
                        Axes & Methodology
                      </button>
                      <button
                        className="quick-prompt-btn"
                        onClick={() => handleVisionChat('What are the key numerical findings or component metrics?')}
                      >
                        Numerical Findings
                      </button>
                      <button
                        className="quick-prompt-btn"
                        onClick={() => handleVisionChat('Summarize the architectural flow or diagram pipeline.')}
                      >
                        Architecture Flow
                      </button>
                    </div>

                    {/* Messages */}
                    <div className="vision-chat-messages">
                      {visionChatMessages.map((msg) => (
                        <div key={msg.id} className={`vision-msg ${msg.sender}`}>
                          {msg.text}
                        </div>
                      ))}
                      {visionChatLoading && (
                        <div className="vision-msg assistant" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <RefreshCw size={14} className="spin" />
                          Analyzing visual attributes...
                        </div>
                      )}
                      <div ref={visionChatBottomRef} />
                    </div>

                    {/* Input Bar */}
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        handleVisionChat();
                      }}
                      style={{ display: 'flex', gap: '10px' }}
                    >
                      <input
                        type="text"
                        className="chat-input"
                        placeholder="Ask a question about this figure..."
                        value={visionChatInput}
                        onChange={(e) => setVisionChatInput(e.target.value)}
                        disabled={visionChatLoading}
                      />
                      <button
                        type="submit"
                        className="primary-btn"
                        disabled={visionChatLoading || !visionChatInput.trim()}
                        style={{ padding: '0 18px' }}
                      >
                        <Send size={16} />
                      </button>
                    </form>
                  </div>
                </div>
              )}
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
              <button className="btn-icon" onClick={() => setSelectedDoc(null)} aria-label="Close document inspector">
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
