import React, { useEffect, useMemo, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  ArrowUpRight,
  BarChart3,
  Bell,
  BookOpen,
  Building2,
  CalendarDays,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Download,
  FileText,
  Filter,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Mic,
  MicOff,
  Menu,
  MoreHorizontal,
  Pause,
  Plus,
  Search,
  Send,
  Square,
  ShieldCheck,
  Trash2,
  UploadCloud,
  UserPlus,
  Users,
  X,
} from 'lucide-react'
import './index.css'

// ─── API layer ────────────────────────────────────────────────────────────────

const API_URL = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) || 'http://localhost:8000'

let _token = null

function setToken(t) { _token = t; if (t) localStorage.setItem('conai_token', t); else localStorage.removeItem('conai_token') }
function loadToken() { _token = localStorage.getItem('conai_token') }

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) }
  if (_token) headers['Authorization'] = `Bearer ${_token}`
  const res = await fetch(`${API_URL}${path}`, { ...opts, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'API error')
  }
  return res.json()
}

async function apiForm(path, formData, method = 'POST') {
  const headers = {}
  if (_token) headers['Authorization'] = `Bearer ${_token}`
  const res = await fetch(`${API_URL}${path}`, { method, headers, body: formData })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'API error')
  }
  return res.json()
}

// ─── Permissions helper ───────────────────────────────────────────────────────

const permissions = {
  ADMIN: { canManageUsers: true, canManagePolicies: true },
  EMPLOYEE: { canManageUsers: false, canManagePolicies: false },
}

function withPermissions(user) {
  if (!user) return null
  return { ...user, permissions: permissions[user.role] || permissions.EMPLOYEE }
}

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'chat', label: 'Employee Chat', icon: MessageSquare },
  { id: 'users', label: 'Users', icon: Users },
  { id: 'policies', label: 'Knowledge / Policies', icon: BookOpen },
]

// ─── App root ─────────────────────────────────────────────────────────────────

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [currentUser, setCurrentUser] = useState(null)
  const [authMode, setAuthMode] = useState('login')
  const [activePage, setActivePage] = useState('dashboard')
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [users, setUsers] = useState([])
  const [policies, setPolicies] = useState([])
  const [selectedPolicy, setSelectedPolicy] = useState(null)
  const [toast, setToast] = useState('')
  const [activePanel, setActivePanel] = useState(null)
  const [messageThreads, setMessageThreads] = useState([])
  const [notifications, setNotifications] = useState([])
  const [aiSessions, setAiSessions] = useState([])
  const [loading, setLoading] = useState(false)

  // Try to restore session from localStorage token on mount
  useEffect(() => {
    loadToken()
    if (!_token) return
    api('/api/auth/me')
      .then(user => {
        setCurrentUser(withPermissions(user))
        setIsAuthenticated(true)
      })
      .catch(() => setToken(null))
  }, [])

  useEffect(() => {
    if (!toast) return undefined
    const timer = window.setTimeout(() => setToast(''), 3000)
    return () => window.clearTimeout(timer)
  }, [toast])

  // Load data when authenticated
  useEffect(() => {
    if (!isAuthenticated) return
    Promise.all([
      api('/api/users').catch(() => []),
      api('/api/sources').catch(() => []),
      api('/api/threads').catch(() => []),
      api('/api/notifications').catch(() => []),
      api('/api/chat/sessions').catch(() => []),
    ]).then(([usersData, sourcesData, threadsData, notifsData, sessionsData]) => {
      setUsers(usersData)
      setPolicies(sourcesData)
      setMessageThreads(threadsData)
      setNotifications(notifsData)
      if (sessionsData.length > 0) {
        setAiSessions(sessionsData)
      } else {
        // Create a default session for first-time users
        api('/api/chat/sessions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: 'ConAI AI Chat' }) })
          .then(session => setAiSessions([session]))
          .catch(() => {})
      }
    })
  }, [isAuthenticated])

  const handleAuth = async (event) => {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const identifier = String(formData.get('identifier') || '')
    const password = String(formData.get('password') || '')
    const name = String(formData.get('name') || '')
    const employeeId = String(formData.get('employeeId') || '')

    setLoading(true)
    try {
      let result
      if (authMode === 'signup') {
        result = await api('/api/auth/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, identifier, employeeId, password }),
        })
      } else {
        result = await api('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ identifier, password }),
        })
      }
      setToken(result.access_token)
      setCurrentUser(withPermissions(result.user))
      setIsAuthenticated(true)
      setToast(`${result.user.role === 'ADMIN' ? 'Admin' : 'Employee'} access granted.`)
    } catch (err) {
      setToast(err.message || 'Authentication failed.')
    } finally {
      setLoading(false)
    }
  }

  const navigate = (page) => {
    if (page === 'users' && !currentUser?.permissions.canManageUsers) {
      setToast('Users is restricted to administrators.')
      return
    }
    setActivePage(page)
    setMobileNavOpen(false)
  }

  const handleLogout = () => {
    api('/api/auth/logout', { method: 'POST' }).catch(() => {})
    setToken(null)
    setActivePanel(null)
    setSelectedPolicy(null)
    setMobileNavOpen(false)
    setIsAuthenticated(false)
    setCurrentUser(null)
    setUsers([])
    setPolicies([])
    setAiSessions([])
    setMessageThreads([])
    setNotifications([])
    setToast('')
  }

  if (!isAuthenticated) {
    return <AuthScreen mode={authMode} setMode={setAuthMode} onSubmit={handleAuth} loading={loading} />
  }

  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} navigate={navigate} open={mobileNavOpen} close={() => setMobileNavOpen(false)} onAction={setActivePanel} currentUser={currentUser} />
      <main className="main-content">
        <header className="topbar">
          <button className="icon-button mobile-menu" onClick={() => setMobileNavOpen(true)} aria-label="Open navigation"><Menu size={20} /></button>
          <div className="breadcrumbs"><span>Workspace</span><span className="crumb-separator">/</span><strong>{navItems.find((item) => item.id === activePage)?.label}</strong></div>
          <div className="topbar-actions">
            <button className="icon-button" aria-label="Help" onClick={() => setActivePanel('help')}><CircleHelp size={19} /></button>
            <button className="icon-button notification-button" aria-label="Notifications" onClick={() => setActivePanel('notifications')}><Bell size={19} />{notifications.length > 0 && <i />}</button>
            <button className="profile-chip" onClick={() => setActivePanel('profile')}><div className="avatar avatar-small avatar-rose">{currentUser?.name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase()}</div><span>{currentUser?.name}</span><ChevronDown size={15} /></button>
          </div>
        </header>
        <div className="page-wrap">
          {activePage === 'dashboard' && <Dashboard users={users} policies={policies} navigate={navigate} showToast={setToast} currentUser={currentUser} threads={messageThreads} setThreads={setMessageThreads} notify={setNotifications} />}
          {activePage === 'chat' && <ChatPage sessions={aiSessions} setSessions={setAiSessions} currentUser={currentUser} showToast={setToast} />}
          {activePage === 'users' && <UsersPage users={users} setUsers={setUsers} showToast={setToast} />}
          {activePage === 'policies' && <PoliciesPage policies={policies} setPolicies={setPolicies} onView={setSelectedPolicy} showToast={setToast} canManage={currentUser?.permissions.canManagePolicies} currentUser={currentUser} />}
        </div>
      </main>
      {selectedPolicy && <PolicyViewer policy={selectedPolicy} onClose={() => setSelectedPolicy(null)} />}
      {activePanel && <InfoPanel type={activePanel} onClose={() => setActivePanel(null)} onLogout={handleLogout} currentUser={currentUser} notifications={notifications} setNotifications={setNotifications} />}
      {toast && <div className="toast"><Check size={17} />{toast}</div>}
    </div>
  )
}

function AuthScreen({ mode, setMode, onSubmit, loading }) {
  const signup = mode === 'signup'
  const [forgotMessage, setForgotMessage] = useState('')
  const [legalMessage, setLegalMessage] = useState('')
  return (
    <div className="auth-page">
      <div className="auth-visual">
        <div className="auth-brand"><BrandMark light /><span>ConAI</span></div>
        <div className="visual-copy">
          <p className="eyebrow light-eyebrow">Enterprise intelligence, made simple</p>
          <h1>Make knowledge<br /><em>work for everyone.</em></h1>
          <p>One trusted place for your team's knowledge, policies, and everyday answers.</p>
        </div>
        <div className="visual-footer"><span className="live-dot" /> Trusted by modern teams to move with clarity.</div>
      </div>
      <div className="auth-panel">
        <div className="auth-mobile-brand"><BrandMark /><span>ConAI</span></div>
        <div className="auth-form-wrap">
          <div className="auth-heading"><p className="eyebrow">Welcome to ConAI</p><h2>{signup ? 'Create your workspace' : 'Good to see you again'}</h2><p>{signup ? 'Set up your team account in a few seconds.' : 'Sign in to your enterprise knowledge hub.'}</p></div>
          <div className="auth-tabs"><button className={!signup ? 'active' : ''} onClick={() => setMode('login')}>Log in</button><button className={signup ? 'active' : ''} onClick={() => setMode('signup')}>Sign up</button></div>
          <form onSubmit={onSubmit} className="auth-form">
            {signup && <Field name="name" label="Full name" placeholder="Your full name" icon={<Users size={17} />} />}
            <Field name="identifier" label={signup ? 'Work email' : 'Email / Employee ID'} placeholder={signup ? 'you@company.com' : 'you@company.com or EMP-1048'} icon={<Building2 size={17} />} type={signup ? 'email' : 'text'} />
            {signup && <Field name="employeeId" label="Employee ID" placeholder="EMP-0000" icon={<ShieldCheck size={17} />} />}
            <Field name="password" label="Password" placeholder="Enter your password" icon={<ShieldCheck size={17} />} type="password" />
            {!signup && <div className="form-meta"><label className="check-label"><input type="checkbox" /> <span>Remember me</span></label><button type="button" className="text-button" onClick={() => setForgotMessage('Password reset instructions would be sent to your work email.')}>Forgot password?</button></div>}
            <button className="primary-button auth-submit" type="submit" disabled={loading}>{loading ? 'Please wait…' : signup ? 'Create account' : 'Continue'}<ArrowUpRight size={17} /></button>
          </form>
          {forgotMessage && <p className="inline-notice">{forgotMessage}</p>}
          <p className="auth-note">By continuing, you agree to ConAI's <button type="button" className="legal-button" onClick={() => setLegalMessage('ConAI terms of service apply.')}>Terms of Service</button> and <button type="button" className="legal-button" onClick={() => setLegalMessage('Your data is protected by ConAI privacy policy.')}>Privacy Policy</button>.</p>
          {legalMessage && <p className="inline-notice">{legalMessage}</p>}
        </div>
        <div className="auth-bottom"><span>© 2024 ConAI Inc.</span><span>Enterprise Knowledge & AI Assistant</span></div>
      </div>
    </div>
  )
}

function Field({ name, label, placeholder, icon, type = 'text' }) {
  return <label className="field"><span>{label}</span><div className="input-wrap">{icon}<input name={name} type={type} placeholder={placeholder} required /></div></label>
}

function BrandMark({ light = false }) {
  return <span className={`brand-mark ${light ? 'brand-mark-light' : ''}`}><span /><span /><span /></span>
}

function Sidebar({ activePage, navigate, open, close, onAction, currentUser }) {
  const visibleItems = navItems.filter((item) => item.id !== 'users' || currentUser?.permissions.canManageUsers)
  const initials = currentUser?.name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase()
  return <><div className={`sidebar-overlay ${open ? 'visible' : ''}`} onClick={close} /><aside className={`sidebar ${open ? 'open' : ''}`}>
    <div className="sidebar-brand"><BrandMark /><span>ConAI</span><button className="icon-button close-nav" onClick={close}><X size={20} /></button></div>
    <button className="workspace-select" onClick={() => onAction('workspace')}><div className="workspace-icon">C</div><div><strong>ConAI Workspace</strong><span>Enterprise account</span></div><ChevronDown size={15} /></button>
    <nav className="side-nav"><span className="nav-label">Workspace</span>{visibleItems.map(({ id, label, icon: Icon }) => <button key={id} className={activePage === id ? 'selected' : ''} onClick={() => navigate(id)}><Icon size={18} /><span>{label}</span></button>)}</nav>
    <div className="sidebar-bottom"><div className="upgrade-note"><div className="upgrade-icon"><BarChart3 size={17} /></div><strong>{currentUser?.role === 'ADMIN' ? 'Knowledge at a glance' : 'Employee access'}</strong><p>{currentUser?.role === 'ADMIN' ? 'Your workspace is up to date.' : 'Read-only workspace access.'}</p></div><button className="side-logout" onClick={() => onAction('logout')}><LogOut size={18} /> Log out</button><button className="sidebar-user" onClick={() => onAction('profile')}><div className="avatar avatar-rose">{initials}</div><div><strong>{currentUser?.name}</strong><span>{currentUser?.role}</span></div><MoreHorizontal size={18} /></button></div>
  </aside></>
}

function PageHeader({ eyebrow, title, description, action }) {
  return <div className="page-header"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div>{action}</div>
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

function Dashboard({ users, policies, navigate, showToast, currentUser, threads, setThreads, notify }) {
  const canManage = currentUser?.permissions.canManagePolicies
  const [stats, setStats] = useState(null)

  useEffect(() => {
    api('/api/dashboard/stats').then(setStats).catch(() => {})
  }, [policies])

  const cards = stats
    ? [
        { label: 'Total policies', value: stats.totalSources, change: `${stats.activeUsers} active`, note: 'users', icon: FileText, tone: 'violet' },
        { label: 'Recently uploaded', value: stats.recentlyUploaded, change: 'Latest', note: stats.recentlyUploadedName, icon: UploadCloud, tone: 'amber' },
      ]
    : [
        { label: 'Total policies', value: policies.length, change: '+2', note: 'this month', icon: FileText, tone: 'violet' },
        { label: 'Recently uploaded', value: '—', change: 'Latest', note: 'Loading…', icon: UploadCloud, tone: 'amber' },
      ]

  return <>
    <PageHeader eyebrow={currentUser?.role === 'ADMIN' ? 'Admin overview' : 'Employee overview'} title={`Good morning, ${currentUser?.name.split(' ')[0]}`} description={canManage ? 'Manage employee questions and keep company knowledge current.' : 'Ask the admin team questions and review the latest company policies.'} />
    <section className="stats-grid">{cards.map(({ label, value, change, note, icon: Icon, tone }) => <div className="stat-card" key={label}><div className={`stat-icon ${tone}`}><Icon size={19} /></div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-change"><span>{change}</span>{note}</div></div>)}</section>
    <DashboardCommsChat threads={threads} setThreads={setThreads} currentUser={currentUser} showToast={showToast} notify={notify} />
  </>
}

function Activity({ icon, title, detail, time, tone }) { return <div className="activity-row"><div className={`activity-icon ${tone}`}>{icon}</div><div className="activity-text"><strong>{title}</strong><span>{detail}</span></div><time>{time}</time></div> }

// ─── AI Chat ─────────────────────────────────────────────────────────────────

function ChatPage({ sessions, setSessions, currentUser, showToast }) {
  const [activeSessionId, setActiveSessionId] = useState(sessions[0]?.id || null)
  const [draft, setDraft] = useState('')
  const [recordingState, setRecordingState] = useState('idle')
  const [chatMode, setChatMode] = useState('voice')
  const [sending, setSending] = useState(false)
  const activeSession = sessions.find((session) => session.id === activeSessionId) || sessions[0]

  useEffect(() => { if (sessions.length > 0 && !activeSessionId) setActiveSessionId(sessions[0].id) }, [sessions])

  const createChat = async () => {
    try {
      const session = await api('/api/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New conversation' }),
      })
      setSessions((current) => [session, ...current])
      setActiveSessionId(session.id)
      setDraft('')
    } catch (err) {
      showToast(err.message)
    }
  }

  const sendMessage = async (event) => {
    event.preventDefault()
    const text = draft.trim()
    if (!text || !activeSession || sending) return
    setSending(true)
    setDraft('')
    try {
      const updated = await api(`/api/chat/sessions/${activeSession.id}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      setSessions((current) => current.map((s) => s.id === updated.id ? updated : s))
    } catch (err) {
      showToast(err.message)
    } finally {
      setSending(false)
    }
  }

  const startRecording = () => { setRecordingState('recording'); showToast('Recording started. Voice input coming soon.') }
  const pauseRecording = () => { setRecordingState('paused'); showToast('Recording paused.') }
  const stopRecording = () => { setRecordingState('idle'); showToast('Recording stopped. No transcript was created.') }

  return <div className="chat-page ai-chat-page">
    <aside className="chat-sidebar surface"><div className="chat-sidebar-heading"><div><p className="eyebrow">Knowledge assistant</p><h1>ConAI AI Chat</h1></div><MessageSquare size={20} /></div><button className="primary-button new-chat-button" onClick={createChat}><Plus size={17} /> New Chat</button><p className="chat-section-label">Recent chats</p><div className="chat-history-list">{sessions.map((session) => <button key={session.id} className={`chat-history-item ${session.id === activeSession?.id ? 'selected' : ''}`} onClick={() => setActiveSessionId(session.id)}><MessageSquare size={16} /><span>{session.title}</span></button>)}</div><div className="chat-sidebar-footer"><div className="avatar avatar-blue">AI</div><div><strong>ConAI AI Agent</strong><span>Knowledge and policies</span></div></div></aside>
    <section className="chat-workspace surface"><header className="chat-header"><div><p className="eyebrow">Private AI workspace</p><h2>{activeSession?.title || 'New conversation'}</h2></div><div className="chat-header-actions"><div className="chat-mode-toggle"><button className={chatMode === 'voice' ? 'active' : ''} onClick={() => setChatMode('voice')} type="button"><Mic size={14} /> Voice chat</button><button className={chatMode === 'text' ? 'active' : ''} onClick={() => { setChatMode('text'); setRecordingState('idle') }} type="button"><MessageSquare size={14} /> Text chat</button></div><span className="chat-status"><i /> AI agent ready</span></div></header><div className="chat-messages">{activeSession?.messages.map((message) => <div key={message.id} className={`chat-message-row ${message.from === 'user' ? 'user' : 'assistant'}`}><div className={`chat-message-avatar ${message.from === 'user' ? 'user' : 'assistant'}`}>{message.from === 'user' ? 'ME' : 'AI'}</div><div className="chat-message"><span className="chat-message-author">{message.from === 'user' ? 'You' : 'ConAI AI Agent'}</span><p style={{whiteSpace:'pre-wrap'}}>{message.text}</p></div></div>)}</div>{chatMode === 'voice' ? <div className={`voice-console ${recordingState}`}><p className="voice-console-label">Voice chat</p><button type="button" className="voice-record-button" onClick={recordingState === 'idle' ? startRecording : recordingState === 'paused' ? startRecording : pauseRecording} aria-label="Voice recording">{recordingState === 'recording' ? <Pause size={30} /> : <Mic size={34} />}</button><strong>{recordingState === 'idle' ? 'Tap to start recording' : recordingState === 'recording' ? 'Recording...' : 'Recording paused'}</strong><span>Voice input coming soon</span>{recordingState !== 'idle' && <button type="button" className="stop-record-button" onClick={stopRecording}><Square size={14} /> Stop recording</button>}</div> : <form className="chat-composer text-only-composer" onSubmit={sendMessage}><input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask about knowledge, policies, or workplace questions" disabled={sending} /><button type="submit" className="send-button" aria-label="Send message" disabled={!draft.trim() || sending}><Send size={17} /></button></form>}</section>
  </div>
}

// ─── Dashboard comms chat ─────────────────────────────────────────────────────

function DashboardCommsChat({ threads, setThreads, currentUser, showToast, notify }) {
  const availableThreads = currentUser?.role === 'ADMIN' ? threads : threads.filter((thread) => thread.employeeId === currentUser?.employeeId)
  const [activeThreadId, setActiveThreadId] = useState(availableThreads[0]?.id || null)
  const [draft, setDraft] = useState('')
  const [recording, setRecording] = useState(false)
  const [chatMode, setChatMode] = useState('voice')
  const [sending, setSending] = useState(false)
  const activeThread = availableThreads.find((thread) => thread.id === activeThreadId) || availableThreads[0]

  useEffect(() => { if (availableThreads.length > 0 && !activeThreadId) setActiveThreadId(availableThreads[0].id) }, [threads])

  const createChat = async () => {
    try {
      const thread = await api('/api/threads', { method: 'POST' })
      setThreads((current) => {
        const exists = current.find(t => t.id === thread.id)
        return exists ? current : [thread, ...current]
      })
      setActiveThreadId(thread.id)
      setDraft('')
    } catch (err) { showToast(err.message) }
  }

  const sendMessage = async (event) => {
    event.preventDefault()
    const text = draft.trim()
    if (!text || !activeThread || sending) return
    setSending(true)
    setDraft('')
    try {
      const updated = await api(`/api/threads/${activeThread.id}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      setThreads((current) => current.map((t) => t.id === updated.id ? updated : t))
      // Refresh notifications
      api('/api/notifications').then(notify).catch(() => {})
    } catch (err) { showToast(err.message) } finally { setSending(false) }
  }

  const toggleRecording = () => {
    setRecording((current) => !current)
    if (!recording) showToast('Listening... voice input coming soon.')
    else showToast('Voice recording stopped.')
  }

  return <div className="chat-page embedded-chat">
    <aside className="chat-sidebar surface">
      <div className="chat-sidebar-heading"><div><p className="eyebrow">{currentUser.role === 'ADMIN' ? 'Employee inbox' : 'Admin support'}</p><h1>ConAI Chat</h1></div><MessageSquare size={20} /></div>
      {currentUser.role === 'EMPLOYEE' && <button className="primary-button new-chat-button" onClick={createChat}><Plus size={17} /> New Chat</button>}
      <p className="chat-section-label">{currentUser.role === 'ADMIN' ? 'Employee conversations' : 'Recent chats'}</p>
      <div className="chat-history-list">{availableThreads.map((thread) => <button key={thread.id} className={`chat-history-item ${thread.id === activeThread?.id ? 'selected' : ''}`} onClick={() => setActiveThreadId(thread.id)}><MessageSquare size={16} /><span>{currentUser.role === 'ADMIN' ? thread.employeeName : `Conversation ${thread.id}`}</span></button>)}</div>
      <div className="chat-sidebar-footer"><div className="avatar avatar-blue">{currentUser?.name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase()}</div><div><strong>{currentUser?.name}</strong><span>{currentUser?.role === 'ADMIN' ? 'Administrator' : 'Employee'}</span></div></div>
    </aside>
    <section className="chat-workspace surface">
      <header className="chat-header"><div><p className="eyebrow">{currentUser.role === 'ADMIN' ? 'Respond to employee' : 'Admin support'}</p><h2>{activeThread ? (currentUser.role === 'ADMIN' ? activeThread.employeeName : 'Admin team') : 'No conversation selected'}</h2></div><div className="chat-header-actions"><div className="chat-mode-toggle"><button className={chatMode === 'voice' ? 'active' : ''} onClick={() => { setChatMode('voice'); setRecording(true) }} type="button"><Mic size={14} /> Voice chat</button><button className={chatMode === 'text' ? 'active' : ''} onClick={() => { setChatMode('text'); setRecording(false) }} type="button"><MessageSquare size={14} /> Text chat</button></div><span className="chat-status"><i /> Messages live</span></div></header>
      <div className="chat-messages">{activeThread?.messages.map((message) => <div key={message.id} className={`chat-message-row ${message.from === 'employee' ? 'user' : 'assistant'}`}><div className={`chat-message-avatar ${message.from === 'employee' ? 'user' : 'assistant'}`}>{message.from === 'employee' ? activeThread.employeeName.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase() : 'A'}</div><div className="chat-message"><span className="chat-message-author">{message.senderName || (message.from === 'assistant' ? 'ConAI Assistant' : 'Admin')}</span><p>{message.text}</p></div></div>)}</div>
      <form className={`chat-composer ${recording ? 'recording' : ''}`} onSubmit={sendMessage}><button type="button" className="record-button" onClick={toggleRecording} aria-label={recording ? 'Stop recording' : 'Start voice input'}>{recording ? <MicOff size={18} /> : <Mic size={18} />}</button><input value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={recording ? 'Listening... click microphone to stop' : currentUser.role === 'ADMIN' ? 'Reply to this employee' : 'Message the admin team'} disabled={!activeThread || sending} /><button type="submit" className="send-button" aria-label="Send message" disabled={!draft.trim() || !activeThread || sending}><Send size={17} /></button></form>
      {recording && <div className="recording-note"><span className="recording-pulse" /> Voice input coming soon. Click the microphone to stop.</div>}
    </section>
  </div>
}

// ─── Users page ───────────────────────────────────────────────────────────────

function UsersPage({ users, setUsers, showToast }) {
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('All roles')
  const [selectedUser, setSelectedUser] = useState(null)
  const [showInvite, setShowInvite] = useState(false)
  const filtered = users.filter((user) => (role === 'All roles' || user.role === role) && `${user.name} ${user.email} ${user.employeeId} ${user.department}`.toLowerCase().includes(search.toLowerCase()))

  const handleExport = () => {
    window.open(`${API_URL}/api/users/export`, '_blank')
  }

  return <>
    <PageHeader eyebrow="Directory" title="Users" description="Manage your organization's people and access levels." action={<button className="primary-button" onClick={() => setShowInvite(true)}><UserPlus size={16} /> Invite user</button>} />
    <div className="surface table-surface"><div className="table-toolbar"><div className="search-box"><Search size={17} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search users..." /></div><div className="toolbar-right"><div className="select-wrap"><Filter size={16} /><select value={role} onChange={(event) => setRole(event.target.value)}><option>All roles</option><option>ADMIN</option><option>EMPLOYEE</option></select><ChevronDown size={15} /></div><button className="outline-button export-button" onClick={handleExport}><Download size={16} /> Export</button></div></div><div className="table-scroll"><table><thead><tr><th>Name</th><th>Employee ID</th><th>Email</th><th>Role</th><th>Department</th><th>Salary</th><th>Status</th><th>Joined date</th><th /></tr></thead><tbody>{filtered.map((user) => <tr key={user.employeeId}><td><div className="person-cell"><div className={`avatar avatar-${user.color}`}>{user.initials}</div><strong>{user.name}</strong></div></td><td className="muted-cell">{user.employeeId}</td><td className="muted-cell">{user.email}</td><td><span className={`role-pill ${user.role.toLowerCase()}`}>{user.role}</span></td><td className="muted-cell">{user.department}</td><td className="muted-cell">{user.salary}</td><td><span className={`status-pill ${user.status.toLowerCase()}`}><i />{user.status}</span></td><td className="muted-cell">{user.joined}</td><td><button className="row-action" onClick={() => setSelectedUser(user)} aria-label={`View ${user.name}`}><ArrowUpRight size={16} /></button></td></tr>)}</tbody></table></div><div className="table-footer"><span>Showing <strong>{filtered.length}</strong> of <strong>{users.length}</strong> users</span></div></div>
    {showInvite && <InviteModal onClose={() => setShowInvite(false)} onInvite={async (form) => {
      try {
        const created = await api('/api/users', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...form, password: 'Welcome@1234' }),
        })
        setUsers((current) => [created, ...current])
        setShowInvite(false)
        showToast(`${created.name} added. Temporary password: Welcome@1234`)
      } catch (err) { showToast(err.message) }
    }} />}
    {selectedUser && <UserModal user={selectedUser} onClose={() => setSelectedUser(null)} onSave={async (updatedUser) => {
      try {
        const saved = await api(`/api/users/${updatedUser.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: updatedUser.name, email: updatedUser.email, department: updatedUser.department, salary: updatedUser.salary, role: updatedUser.role, status: updatedUser.status }),
        })
        setUsers((current) => current.map((u) => u.id === saved.id ? saved : u))
        setSelectedUser(saved)
        showToast(`${saved.name} was updated successfully.`)
      } catch (err) { showToast(err.message) }
    }} />}
  </>
}

function InviteModal({ onClose, onInvite }) {
  const [form, setForm] = useState({ name: '', email: '', employeeId: '', department: '', role: 'EMPLOYEE' })
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))
  const submit = (event) => { event.preventDefault(); onInvite(form) }
  return <div className="modal-backdrop" onMouseDown={onClose}><form className="user-modal invite-modal" onSubmit={submit} onMouseDown={(event) => event.stopPropagation()}><button type="button" className="modal-close" onClick={onClose}><X size={18} /></button><div className="modal-profile"><div className="avatar avatar-large avatar-blue"><UserPlus size={23} /></div><div><h2>Invite a user</h2><p>Add a team member to your ConAI workspace.</p></div></div><div className="invite-fields"><label className="field"><span>Full name</span><input className="plain-input" required value={form.name} onChange={(event) => update('name', event.target.value)} placeholder="e.g. Taylor Morgan" /></label><label className="field"><span>Work email</span><input className="plain-input" required type="email" value={form.email} onChange={(event) => update('email', event.target.value)} placeholder="taylor@company.com" /></label><label className="field"><span>Employee ID</span><input className="plain-input" required value={form.employeeId} onChange={(event) => update('employeeId', event.target.value)} placeholder="EMP-0000" /></label><label className="field"><span>Department</span><input className="plain-input" required value={form.department} onChange={(event) => update('department', event.target.value)} placeholder="e.g. Engineering" /></label><label className="field"><span>Role</span><select className="plain-input" value={form.role} onChange={(event) => update('role', event.target.value)}><option>EMPLOYEE</option><option>ADMIN</option></select></label></div><button className="primary-button full-button" type="submit"><UserPlus size={16} /> Add user</button></form></div>
}

function UserModal({ user, onClose, onSave }) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState(user)
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))
  const submit = (event) => { event.preventDefault(); onSave({ ...form, initials: form.name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase() }); setEditing(false) }
  return <div className="modal-backdrop" onMouseDown={onClose}><div className="user-modal" onMouseDown={(event) => event.stopPropagation()}><button className="modal-close" onClick={onClose}><X size={18} /></button>{editing ? <form onSubmit={submit}><div className="modal-profile"><div className={`avatar avatar-large avatar-${form.color}`}>{form.initials}</div><div><h2>Edit user</h2><p>Update directory information and access.</p></div></div><div className="edit-user-grid"><EditField label="Name" value={form.name} onChange={(value) => update('name', value)} /><label className="field"><span>Employee ID</span><input className="plain-input" value={form.employeeId} disabled /></label><EditField label="Email" type="email" value={form.email} onChange={(value) => update('email', value)} /><EditField label="Department" value={form.department} onChange={(value) => update('department', value)} /><EditField label="Salary" value={form.salary} onChange={(value) => update('salary', value)} /><label className="field"><span>Role</span><select className="plain-input" value={form.role} onChange={(event) => update('role', event.target.value)}><option>ADMIN</option><option>EMPLOYEE</option></select></label><label className="field"><span>Status</span><select className="plain-input" value={form.status} onChange={(event) => update('status', event.target.value)}><option>Active</option><option>Inactive</option></select></label></div><div className="info-actions"><button type="button" className="outline-button" onClick={() => setEditing(false)}>Cancel</button><button type="submit" className="primary-button"><Check size={16} /> Save changes</button></div></form> : <><div className="modal-profile"><div className={`avatar avatar-large avatar-${user.color}`}>{user.initials}</div><div><h2>{user.name}</h2><p>{user.employeeId} · {user.department}</p></div></div><div className="detail-grid"><Detail label="Work email" value={user.email} /><Detail label="Role" value={user.role} /><Detail label="Status" value={user.status} /><Detail label="Joined date" value={user.joined} /><Detail label="Department" value={user.department} /><Detail label="Annual salary" value={user.salary} /></div><div className="info-actions"><button className="outline-button" onClick={onClose}>Close details</button><button className="primary-button" onClick={() => setEditing(true)}>Edit user</button></div></>}</div></div>
}
function EditField({ label, value, onChange, type = 'text' }) { return <label className="field"><span>{label}</span><input className="plain-input" required type={type} value={value} onChange={(event) => onChange(event.target.value)} /></label> }
function Detail({ label, value }) { return <div className="detail-item"><span>{label}</span><strong>{value}</strong></div> }

// ─── Policies page ────────────────────────────────────────────────────────────

function PoliciesPage({ policies, setPolicies, onView, showToast, canManage = false, currentUser }) {
  const [dragActive, setDragActive] = useState(false)
  const [file, setFile] = useState(null)
  const [policyName, setPolicyName] = useState('')
  const [description, setDescription] = useState('')
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef(null)

  const handleFile = (selected) => {
    const next = selected?.[0]
    if (next && ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'text/plain'].includes(next.type)) {
      setFile(next)
    } else if (next) {
      showToast('Please choose a PDF, DOCX, XLSX, or TXT file.')
    }
  }

  const upload = async (event) => {
    event.preventDefault()
    if (!policyName || !file) { showToast('Add a document name and file before uploading.'); return }
    setUploading(true)
    try {
      const form = new FormData()
      form.append('name', policyName.trim())
      form.append('description', description || 'No description provided.')
      form.append('status', 'draft')
      form.append('file', file)
      const created = await apiForm('/api/sources', form)
      setPolicies([created, ...policies])
      setPolicyName(''); setDescription(''); setFile(null)
      showToast('Document uploaded and indexing started.')
    } catch (err) { showToast(err.message) } finally { setUploading(false) }
  }

  const remove = async (id) => {
    try {
      await api(`/api/sources/${id}`, { method: 'DELETE' })
      setPolicies(policies.filter((policy) => policy.id !== id))
      showToast('Document removed from the workspace.')
    } catch (err) { showToast(err.message) }
  }

  const publish = async (policy) => {
    try {
      const form = new FormData()
      form.append('status', 'published')
      const updated = await apiForm(`/api/sources/${policy.id}`, form, 'PATCH')
      setPolicies(policies.map(p => p.id === updated.id ? updated : p))
      showToast(`${updated.name} published.`)
    } catch (err) { showToast(err.message) }
  }

  const visiblePolicies = policies.filter((policy) => canManage || policy.status === 'Published')

  return <>
    <PageHeader eyebrow="Knowledge hub" title="Knowledge / Policies" description="Keep your organization's most important knowledge clear, current, and accessible." action={<div className="header-status"><span className="status-pill active"><i /> Workspace synced</span></div>} />
    <div className={`policy-layout ${canManage ? '' : 'read-only-policy-layout'}`}>{canManage && <section className="surface upload-surface"><div className="surface-heading"><div><h2>Upload a document</h2><p>Add a PDF, DOCX, XLSX, or TXT to your knowledge hub.</p></div><div className="upload-badge"><ShieldCheck size={17} /> Secure</div></div><form onSubmit={upload}><label className="field"><span>Document name</span><input className="plain-input" value={policyName} onChange={(event) => setPolicyName(event.target.value)} placeholder="e.g. Information Security Policy" /></label><label className="field"><span>Description <small>Optional</small></span><textarea className="plain-input textarea" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="A short description of this document" rows="3" /></label><div className={`drop-zone ${dragActive ? 'drag-active' : ''} ${file ? 'has-file' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragActive(true) }} onDragLeave={() => setDragActive(false)} onDrop={(event) => { event.preventDefault(); setDragActive(false); handleFile(event.dataTransfer.files) }} onClick={() => inputRef.current?.click()}>{file ? <><div className="drop-icon file-selected"><FileText size={23} /></div><div><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB · Ready to upload</span></div><button type="button" className="remove-file" onClick={(event) => { event.stopPropagation(); setFile(null) }}><X size={16} /></button></> : <><div className="drop-icon"><UploadCloud size={23} /></div><div><strong>Drop your file here, or <u>browse</u></strong><span>PDF, DOCX, XLSX, TXT · Max 50 MB</span></div></>}<input ref={inputRef} type="file" accept=".pdf,.docx,.xlsx,.txt" hidden onChange={(event) => handleFile(event.target.files)} /></div><button className="primary-button upload-button" type="submit" disabled={uploading}><UploadCloud size={17} /> {uploading ? 'Uploading…' : 'Upload document'}</button></form></section>}<section className="policy-list-section"><div className="section-title-row"><div><h2>{canManage ? 'All documents' : 'Available policies'} <span>{visiblePolicies.length}</span></h2><p>{canManage ? 'Manage and review your organization\'s policies.' : 'Read the policies available to your role.'}</p></div><button className="icon-button" onClick={() => api('/api/sources').then(setPolicies).catch(() => showToast('Refresh failed.'))} aria-label="Refresh policies"><MoreHorizontal size={19} /></button></div><div className="policy-list">{visiblePolicies.map((policy) => <PolicyCard key={policy.id} policy={policy} onView={onView} onDelete={canManage ? () => remove(policy.id) : undefined} onPublish={canManage && policy.status === 'Draft' ? () => publish(policy) : undefined} canManage={canManage} />)}</div></section></div>
  </>
}

function PolicyCard({ policy, onView, onDelete, onPublish, canManage = false }) {
  return <article className="policy-card"><div className="pdf-icon"><FileText size={21} /><span>{policy.sourceType?.toUpperCase() || 'PDF'}</span></div><div className="policy-card-main"><div className="policy-card-heading"><div><h3>{policy.name}</h3><p>{policy.description}</p></div><button className="card-menu" onClick={() => onView(policy)} aria-label={`Open ${policy.name}`}><MoreHorizontal size={18} /></button></div><div className="policy-meta"><span><CalendarDays size={14} /> {policy.date}</span><span><Users size={14} /> {policy.uploadedBy}</span><span className="version-tag">{policy.version}</span><span className={`status-pill ${policy.status === 'Draft' ? 'draft' : 'active'}`}><i />{policy.status}</span>{policy.ingestionStatus && <span className={`status-pill ${policy.ingestionStatus === 'indexed' ? 'active' : policy.ingestionStatus === 'failed' ? 'draft' : ''}`}><i />{policy.ingestionStatus}</span>}</div><div className="policy-actions"><button onClick={() => onView(policy)}><FileText size={15} /> View document</button>{onPublish && <button onClick={onPublish}><Check size={15} /> Publish</button>}{canManage && <button className="delete-action" onClick={onDelete}><Trash2 size={15} /> Delete</button>}</div></div></article>
}

function PolicyViewer({ policy, onClose }) {
  const fileUrl = policy.file ? `${API_URL}${policy.file}` : null
  return <div className="modal-backdrop viewer-backdrop" onMouseDown={onClose}><div className="viewer-modal" onMouseDown={(event) => event.stopPropagation()}><header className="viewer-header"><div className="viewer-title"><div className="pdf-icon small"><FileText size={18} /><span>{policy.sourceType?.toUpperCase() || 'PDF'}</span></div><div><strong>{policy.name}</strong><span>{policy.version} · {policy.size}</span></div></div><div className="viewer-actions">{fileUrl && <a className="icon-button" href={fileUrl} download={policy.name}><Download size={18} /></a>}<button className="icon-button" onClick={onClose}><X size={19} /></button></div></header><div className="viewer-body">{fileUrl ? <iframe title={policy.name} src={fileUrl} /> : <div className="mock-pdf"><div className="mock-pdf-page"><div className="mock-pdf-kicker">CONAI / KNOWLEDGE HUB</div><h1>{policy.name}</h1><div className="mock-line long" /><div className="mock-line" /><div className="mock-line medium" /><div className="mock-block" /><div className="mock-line long" /><div className="mock-line medium" /><div className="mock-footer">Version {policy.version} · Published {policy.date}</div></div><div className="viewer-note"><FileText size={17} /> Preview mode — file not yet available</div></div>}</div></div></div>
}

// ─── Info panel ───────────────────────────────────────────────────────────────

function InfoPanel({ type, onClose, onLogout, currentUser, notifications = [], setNotifications }) {
  const markAllRead = async () => {
    for (const n of notifications) {
      await api(`/api/notifications/${n.id}/read`, { method: 'POST' }).catch(() => {})
    }
    setNotifications([])
  }

  const content = {
    help: { title: 'ConAI help center', text: 'Use the sidebar to move between your dashboard, users, and knowledge policies. Upload documents on the Knowledge / Policies page.' },
    notifications: { title: 'Notifications', text: notifications.length ? notifications.map((n) => n.text).join(' · ') : 'You are all caught up. New messages will appear here.' },
    workspace: { title: 'Workspace settings', text: 'ConAI Workspace is your active enterprise account.' },
    profile: { title: currentUser?.name || 'ConAI user', text: `${currentUser?.role || 'Employee'} account · Access is controlled by your assigned role.` },
    logout: { title: 'Log out of ConAI?', text: 'Your session will end and you will return to the login screen.' },
  }[type]

  return <div className="modal-backdrop" onMouseDown={onClose}><div className="user-modal info-panel" onMouseDown={(event) => event.stopPropagation()}><button className="modal-close" onClick={onClose}><X size={18} /></button><div className="modal-profile"><div className="avatar avatar-large avatar-blue"><CircleHelp size={23} /></div><div><h2>{content?.title}</h2><p>{content?.text}</p></div></div>{type === 'logout' ? <div className="info-actions"><button className="outline-button" onClick={onClose}>Cancel</button><button className="primary-button" onClick={onLogout}><LogOut size={16} /> Log out</button></div> : type === 'notifications' && notifications.length > 0 ? <div className="info-actions"><button className="outline-button full-button" onClick={markAllRead}>Mark all read</button></div> : <button className="outline-button full-button" onClick={onClose}>Done</button>}</div></div>
}

function AppRoot() { return <App /> }
const rootElement = document.getElementById('root')
const root = globalThis.__conaiRoot || (globalThis.__conaiRoot = createRoot(rootElement))
root.render(<AppRoot />)
