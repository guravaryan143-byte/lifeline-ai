import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'motion/react';
import { Activity, ArrowRight, Check, CircleAlert, Clock3, FilePlus2, Filter, HeartPulse, LayoutDashboard, LifeBuoy, LoaderCircle, LogIn, LogOut, Menu, Plus, RefreshCw, Search, ShieldCheck, Siren, X } from 'lucide-react';
import {
  TOKEN_KEY,
  api,
  assignIncident,
  categoryLabels,
  changeIncidentStatus,
  classifyIncident,
  createIncident,
  createNote,
  downloadAttachment,
  endpoints,
  fetchAttachments,
  fetchCurrentUser,
  fetchDuplicates,
  fetchHistory,
  fetchIncident,
  fetchIncidents,
  fetchNotes,
  incidentStatuses,
  login as loginRequest,
  readableError,
  register as registerRequest,
  statusLabels,
  updateIncident,
  uploadAttachment,
} from './api';
import type {
  Category,
  Classification,
  DashboardSummary,
  DashboardTrend,
  DuplicateCandidate,
  Incident,
  IncidentAttachment,
  IncidentNote,
  IncidentStatus,
  DashboardLocation,
  StatusHistoryEntry,
  User,
} from './api';

interface AuthContextValue {
  user: User | null;
  ready: boolean;
  signIn: (username: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const signOut = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY);
    setUser(null);
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => setUser(null);
    window.addEventListener('lifeline:unauthorized', handleUnauthorized);
    const token = sessionStorage.getItem(TOKEN_KEY);
    if (!token) {
      setReady(true);
    } else {
      fetchCurrentUser()
        .then(setUser)
        .catch(() => {
          sessionStorage.removeItem(TOKEN_KEY);
          setUser(null);
        })
        .finally(() => setReady(true));
    }
    return () => window.removeEventListener('lifeline:unauthorized', handleUnauthorized);
  }, []);

  const signIn = useCallback(async (username: string, password: string) => {
    const token = await loginRequest(username, password);
    sessionStorage.setItem(TOKEN_KEY, token);
    try {
      setUser(await fetchCurrentUser());
    } catch (error) {
      signOut();
      throw error;
    }
  }, [signOut]);

  const signUp = useCallback(async (email: string, password: string) => {
    await registerRequest(email, password);
    await signIn(email, password);
  }, [signIn]);

  const value = useMemo(
    () => ({ user, ready, signIn, signUp, signOut }),
    [user, ready, signIn, signUp, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be rendered inside AuthProvider.');
  return value;
}

function Brand({ light = false }: { light?: boolean }) {
  return (
    <Link className={`brand ${light ? 'brand-light' : ''}`} to="/">
      <span className="brand-mark"><HeartPulse size={19} /></span>
      <span>lifeline<span className="brand-ai">.ai</span></span>
    </Link>
  );
}

function PublicHome() {
  const reducedMotion = useReducedMotion();
  return (
    <div className="landing">
      <nav className="public-nav wrap">
        <Brand light />
        <div className="public-links"><a href="#platform">Platform</a><a href="#workflow">How it works</a></div>
        <Link className="button button-dark button-small" to="/app">Open workspace <ArrowRight size={15} /></Link>
      </nav>
      <main>
        <section className="hero wrap">
          <div className="hero-copy">
            <div className="eyebrow"><span className="pulse-dot" /> INCIDENT COORDINATION</div>
            <h1>Every second<br />matters<span className="serif-dot">.</span><br /><em>Every response counts.</em></h1>
            <p className="hero-sub">A clearer view of every incident. One connected workspace for teams coordinating the response.</p>
            <div className="hero-actions"><Link to="/app" className="button button-dark">Enter operations <ArrowRight size={16} /></Link><a href="#platform" className="text-link">Explore the platform</a></div>
            <div className="hero-foot"><span><ShieldCheck size={16} /> AI-assisted, human-led</span></div>
          </div>
          <motion.div className="hero-art" animate={reducedMotion ? undefined : { y: [0, -5, 0] }} transition={{ duration: 6, repeat: Infinity }}>
            <div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit orbit-three" />
            <div className="art-core"><div className="core-ring"><HeartPulse size={46} strokeWidth={1.25} /></div><span>RESPONSE<br />NETWORK</span></div>
            <div className="float-card float-card-top"><span className="mini-icon blue"><Activity size={15} /></span><div><b>Incident intelligence</b><small>Signals into context</small></div></div>
            <div className="float-card float-card-left"><span className="mini-icon red"><Siren size={15} /></span><div><b>Priority visibility</b><small>See what needs attention</small></div></div>
            <div className="float-card float-card-bottom"><span className="mini-icon green"><Check size={15} /></span><div><b>One shared picture</b><small>From report to resolution</small></div></div>
            <div className="art-glow" />
          </motion.div>
        </section>
        <section id="platform" className="feature-section">
          <div className="wrap">
            <div className="section-kicker">THE PLATFORM</div>
            <div className="feature-heading"><h2>Less uncertainty.<br /><em>More informed action.</em></h2><p>Review incident details, status, and human-reviewed classification from your connected API.</p></div>
            <div className="feature-grid">
              <article className="feature-card"><div className="feature-icon"><Activity size={20} /></div><span className="feature-num">01 / VISIBILITY</span><h3>Incidents, in context.</h3><p>Review real incident records and status in one organized workspace.</p></article>
              <article className="feature-card"><div className="feature-icon feature-icon-violet"><HeartPulse size={20} /></div><span className="feature-num">02 / INTELLIGENCE</span><h3>AI, with a clear role.</h3><p>Classification results are displayed with their review flags and limitations.</p></article>
              <article className="feature-card"><div className="feature-icon feature-icon-red"><Clock3 size={20} /></div><span className="feature-num">03 / CONTINUITY</span><h3>From report to resolution.</h3><p>Follow incident status, notes, attachments, and supported history.</p></article>
            </div>
          </div>
        </section>
        <section id="workflow" className="workflow-section wrap"><div className="workflow-left"><div className="section-kicker">A CLEARER WORKFLOW</div><h2>Good decisions start<br />with a <em>shared picture.</em></h2></div><div className="workflow-steps"><div><span>01</span><section><h3>Capture the incident</h3><p>Record incident details for the coordination team.</p></section></div><div><span>02</span><section><h3>Understand the situation</h3><p>Review the actual classification and status returned by the API.</p></section></div><div><span>03</span><section><h3>Coordinate and follow through</h3><p>Keep notes and status history with the incident record.</p></section></div></div></section>
      </main>
      <footer className="wrap public-footer"><Brand light /><span>LifeLine AI · Incident coordination</span><span>Not an emergency service.</span></footer>
    </div>
  );
}

function Shell({ children, title }: { children: ReactNode; title: string }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-brand"><Brand /></div>
        <div className="workspace-label">WORKSPACE <span className="workspace-status"><i /> {user?.role}</span></div>
        <nav className="side-nav">
          <NavLink to="/app" end><LayoutDashboard size={17} /> Overview</NavLink>
          <NavLink to="/app/incidents"><Siren size={17} /> Incidents</NavLink>
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-help"><span className="help-icon"><LifeBuoy size={17} /></span><div><b>API connection</b><small>FastAPI backend configured</small></div></div>
          <div className="user-row"><div className="user-avatar">{user?.email.slice(0, 2).toUpperCase()}</div><div className="user-meta"><b>{user?.email}</b><small>{user?.role}</small></div><button className="icon-button" aria-label="Sign out" onClick={() => { signOut(); navigate('/app/login'); }}><LogOut size={16} /></button></div>
        </div>
      </aside>
      {mobileOpen && <button aria-label="Close menu" className="mobile-scrim" onClick={() => setMobileOpen(false)} />}
      <main className="app-main">
        <header className="app-topbar"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileOpen((open) => !open)}><Menu size={19} /></button><div className="breadcrumbs"><span>LifeLine AI</span><span className="crumb-slash">/</span><b>{title}</b></div><div className="top-actions"><span className="secure-chip"><ShieldCheck size={14} /> Signed in</span><div className="top-avatar">{user?.email.slice(0, 2).toUpperCase()}</div></div></header>
        <div className="page-content"><div className="page-heading"><div><div className="section-kicker">INCIDENT OPERATIONS / LIVE WORKSPACE</div><h1>{title}</h1><p>Signed in as {user?.email}</p></div></div>{children}<footer className="app-footer"><span>LifeLine AI <i>·</i> Incident coordination</span><span>Not an emergency service</span></footer></div>
      </main>
    </div>
  );
}

function Protected({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) return <div className="loading-state"><LoaderCircle className="spin" size={22} /> Checking session…</div>;
  if (!user) return <Navigate to="/app/login" replace state={{ from: location.pathname }} />;
  return children;
}

function Loading({ label = 'Loading from API…' }: { label?: string }) {
  return <div className="loading-state"><LoaderCircle className="spin" size={22} /><span>{label}</span></div>;
}

function ConnectionBanner({ error, onRetry }: { error: string; onRetry: () => void }) {
  return <div className="connection-banner" role="alert"><span className="connection-symbol"><CircleAlert size={19} /></span><div><b>Request needs attention</b><p>{error}</p></div><button className="button button-outline button-small" onClick={onRetry}><RefreshCw size={14} /> Retry</button></div>;
}

function Empty({ title, detail }: { title: string; detail: string }) {
  return <div className="empty-state"><span><FilePlus2 size={22} /></span><b>{title}</b><p>{detail}</p></div>;
}

function StatusPill({ value }: { value: string }) {
  const normalized = value.toLowerCase();
  const tone = /urgent|high|reported|progress/.test(normalized) ? 'red' : /resolved|closed/.test(normalized) ? 'green' : /review|assigned/.test(normalized) ? 'amber' : 'neutral';
  return <span className={`status-pill ${tone}`}><i />{value}</span>;
}

function Overview() {
  const { user } = useAuth();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [categories, setCategories] = useState<Record<string, number>>({});
  const [statuses, setStatuses] = useState<Record<string, number>>({});
  const [locations, setLocations] = useState<DashboardLocation[]>([]);
  const [trends, setTrends] = useState<DashboardTrend[]>([]);
  const [health, setHealth] = useState<'checking' | 'ok' | 'error'>('checking');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);
  const canViewDashboard = user?.role === 'coordinator' || user?.role === 'administrator';

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    const load = async () => {
      try {
        const healthRequest = api.get(endpoints.health);
        if (canViewDashboard) {
          const [healthResponse, list, metrics, categoryCounts, statusCounts, locationData, trendData] = await Promise.all([
            healthRequest,
            fetchIncidents({ page: 1, page_size: 6 }),
            api.get<DashboardSummary>(endpoints.dashboardSummary),
            api.get<Record<string, number>>(endpoints.dashboardCategories),
            api.get<Record<string, number>>(endpoints.dashboardStatuses),
            api.get<DashboardLocation[]>(endpoints.dashboardLocations),
            api.get<DashboardTrend[]>(endpoints.dashboardTrends),
          ]);
          if (!active) return;
          setHealth(healthResponse.data.status === 'ok' ? 'ok' : 'error');
          setIncidents(list);
          setSummary(metrics.data);
          setCategories(categoryCounts.data);
          setStatuses(statusCounts.data);
          setLocations(locationData.data);
          setTrends(trendData.data);
        } else {
          const [healthResponse, list] = await Promise.all([
            healthRequest,
            fetchIncidents({ page: 1, page_size: 6 }),
          ]);
          if (!active) return;
          setHealth(healthResponse.data.status === 'ok' ? 'ok' : 'error');
          setIncidents(list);
          setSummary(null);
          setCategories({});
          setStatuses({});
          setLocations([]);
          setTrends([]);
        }
      } catch (requestError) {
        if (active) {
          setHealth('error');
          setError(readableError(requestError));
        }
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, [canViewDashboard, reload]);

  const reporterOpen = incidents.filter((item) => !['resolved', 'closed'].includes(item.status)).length;
  return (
    <Shell title="Overview">
      <div className="api-strip"><span className="api-strip-icon"><Activity size={16} /></span><div><b>Backend health</b><small>{health === 'ok' ? 'Database-backed API health check succeeded' : health === 'checking' ? 'Checking API…' : 'API health check failed'}</small></div><span className={`api-tag ${health === 'ok' ? 'api-tag-ok' : 'api-tag-warn'}`}><i />{health}</span></div>
      {error && <ConnectionBanner error={error} onRetry={() => setReload((value) => value + 1)} />}
      <div className="stats-grid">
        <StatCard label={canViewDashboard ? 'Total incidents' : 'Your recent incidents'} value={loading ? '…' : summary?.total ?? incidents.length} note={canViewDashboard ? 'Live dashboard metric' : 'Records on this page'} icon={<Siren size={18} />} tone="blue" />
        <StatCard label={canViewDashboard ? 'Open' : 'Open in this page'} value={loading ? '…' : summary?.open ?? reporterOpen} note="Not resolved or closed" icon={<CircleAlert size={18} />} tone="red" />
        <StatCard label={canViewDashboard ? 'Resolved' : 'Role'} value={loading ? '…' : summary?.resolved ?? (user?.role ?? '—')} note={canViewDashboard ? 'Live dashboard metric' : 'Access is enforced by the API'} icon={<Check size={18} />} tone="violet" />
        <StatCard label={canViewDashboard ? 'Human review' : 'API status'} value={loading ? '…' : summary?.requiring_human_review ?? (health === 'ok' ? 'Connected' : 'Unavailable')} note={canViewDashboard ? 'AI review flag set' : 'SELECT-backed health endpoint'} icon={<ShieldCheck size={18} />} tone="amber" />
      </div>
      <div className="dashboard-grid">
        <section className="panel incidents-panel"><div className="panel-heading"><div><span className="panel-kicker">INCIDENT FEED</span><h2>Recent incidents</h2></div><Link className="panel-link" to="/app/incidents">View all <ArrowRight size={14} /></Link></div>
          {loading ? <Loading /> : incidents.length === 0 ? <Empty title="No incidents to display" detail={error || 'The API returned no incident records.'} /> : <div className="incident-feed">{incidents.map((item) => <Link className="feed-row" to={`/app/incidents/${item.id}`} key={item.id}><span className="feed-symbol"><Siren size={16} /></span><span className="feed-main"><b>{item.title}</b><small>{categoryLabels[item.category]} · {formatDate(item.created_at)}</small></span><StatusPill value={statusLabels[item.status]} /><ArrowRight className="feed-arrow" size={15} /></Link>)}</div>}
        </section>
        <section className="panel system-panel"><div className="panel-heading"><div><span className="panel-kicker">LIVE API DATA</span><h2>Categories</h2></div></div>
          {canViewDashboard ? Object.entries(categories).length ? Object.entries(categories).map(([category, count]) => <div className="detail-field" key={category}><span>{categoryLabels[category as Category] ?? category}</span><b>{count}</b></div>) : <p className="muted-copy">No category counts returned.</p> : <p className="muted-copy">Full dashboard statistics are available to coordinators and administrators.</p>}
          <div className="system-detail"><span>Backend</span><b>Configured FastAPI API</b></div>
        </section>
      </div>
      {canViewDashboard && <div className="dashboard-grid dashboard-extra"><section className="panel detail-panel"><div className="panel-heading"><div><span className="panel-kicker">LIVE API DATA</span><h2>Status totals</h2></div></div>{Object.entries(statuses).length ? Object.entries(statuses).map(([status, count]) => <div className="detail-field" key={status}><span>{statusLabels[status as IncidentStatus] ?? status}</span><b>{count}</b></div>) : <p className="muted-copy">No status counts returned.</p>}</section><section className="panel detail-panel"><div className="panel-heading"><div><span className="panel-kicker">LOCATION SNAPSHOT</span><h2>Reported locations</h2></div></div><p className="muted-copy">{locations.length} locations returned (endpoint maximum: 500).</p>{locations.slice(0, 5).map((location) => <div className="detail-field" key={location.id}><span>{location.title}</span><a href={`https://www.openstreetmap.org/?mlat=${location.latitude}&mlon=${location.longitude}#map=16/${location.latitude}/${location.longitude}`} target="_blank" rel="noreferrer">{location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}</a></div>)}</section><section className="panel detail-panel"><div className="panel-heading"><div><span className="panel-kicker">INCIDENT TRENDS</span><h2>Created by date</h2></div></div>{trends.slice(-7).map((trend) => <div className="detail-field" key={trend.date}><span>{trend.date}</span><b>{trend.count}</b></div>)}{trends.length === 0 && <p className="muted-copy">No trend data returned.</p>}</section></div>}
    </Shell>
  );
}

function StatCard({ label, value, note, icon, tone }: { label: string; value: string | number; note: string; icon: ReactNode; tone: string }) {
  return <div className="stat-card"><div className="stat-top"><span>{label}</span><span className={`stat-icon ${tone}`}>{icon}</span></div><div className="stat-value">{value}</div><div className="stat-note">{note}</div></div>;
}

function Incidents() {
  const [items, setItems] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [reload, setReload] = useState(0);
  const [createOpen, setCreateOpen] = useState(false);
  const pageSize = 20;

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    fetchIncidents({
      page,
      page_size: pageSize,
      ...(category ? { category: category as Category } : {}),
      ...(status ? { status: status as IncidentStatus } : {}),
    }).then((records) => {
      if (active) {
        setItems(records);
        setHasNext(records.length === pageSize);
      }
    }).catch((requestError: unknown) => {
      if (active) setError(readableError(requestError));
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [page, category, status, reload]);

  const visible = items.filter((item) =>
    `${item.title} ${item.description} ${item.id} ${categoryLabels[item.category]}`
      .toLowerCase().includes(query.toLowerCase()),
  );
  const changeFilter = (setter: (value: string) => void, value: string) => {
    setter(value);
    setPage(1);
  };
  return (
    <Shell title="Incidents">
      <div className="incident-toolbar">
        <div className="search-box"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search this page…" aria-label="Search incidents" /></div>
        <div className="toolbar-actions">
          <label className="select-wrap"><Filter size={15} /><select value={status} onChange={(event) => changeFilter(setStatus, event.target.value)} aria-label="Filter by status"><option value="">All statuses</option>{incidentStatuses.map((item) => <option key={item} value={item}>{statusLabels[item]}</option>)}</select></label>
          <label className="select-wrap"><select value={category} onChange={(event) => changeFilter(setCategory, event.target.value)} aria-label="Filter by category"><option value="">All categories</option>{Object.entries(categoryLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <button className="button button-outline button-small" onClick={() => setReload((value) => value + 1)}><RefreshCw size={14} /> Refresh</button>
          <button className="button button-dark button-small" onClick={() => setCreateOpen(true)}><Plus size={15} /> New incident</button>
        </div>
      </div>
      {error && <ConnectionBanner error={error} onRetry={() => setReload((value) => value + 1)} />}
      <section className="panel table-panel"><div className="table-top"><div><span className="panel-kicker">RECORDS</span><h2>Incident register <span className="count-chip">{loading ? '…' : visible.length}</span></h2></div></div>
        {loading ? <Loading label="Loading incidents…" /> : visible.length === 0 ? <Empty title={query ? 'No matching incidents on this page' : 'No incident records'} detail={query ? 'Try another search or move to a different page.' : 'The backend returned no records for these filters.'} /> : <div className="table-scroll"><table><thead><tr><th>INCIDENT</th><th>ID</th><th>CATEGORY</th><th>STATUS</th><th>CREATED</th><th /></tr></thead><tbody>{visible.map((item) => <tr key={item.id}><td><Link className="incident-title-link" to={`/app/incidents/${item.id}`}>{item.title}</Link><small>{item.description}</small></td><td className="mono">{item.id}</td><td>{categoryLabels[item.category]}</td><td><StatusPill value={statusLabels[item.status]} /></td><td className="date-cell">{formatDate(item.created_at)}</td><td><Link className="row-open" aria-label={`Open ${item.title}`} to={`/app/incidents/${item.id}`}><ArrowRight size={16} /></Link></td></tr>)}</tbody></table></div>}
        <div className="table-foot"><span>Page {page} · {visible.length} returned records</span><div className="pagination"><button className="button button-outline button-small" disabled={page === 1 || loading} onClick={() => setPage((value) => value - 1)}>Previous</button><button className="button button-outline button-small" disabled={!hasNext || loading} onClick={() => setPage((value) => value + 1)}>Next</button></div></div>
      </section>
      {createOpen && <CreateIncident onClose={() => setCreateOpen(false)} onCreated={() => { setCreateOpen(false); setPage(1); setReload((value) => value + 1); }} />}
    </Shell>
  );
}

function CreateIncident({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (Boolean(latitude) !== Boolean(longitude)) {
      setError('Enter both latitude and longitude, or leave both empty.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await createIncident({
        title,
        description,
        ...(latitude ? { latitude: Number(latitude), longitude: Number(longitude) } : {}),
      });
      onCreated();
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setBusy(false);
    }
  };
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="modal" role="dialog" aria-modal="true" aria-labelledby="create-title"><div className="modal-head"><div><span className="panel-kicker">NEW RECORD</span><h2 id="create-title">Create incident</h2></div><button className="icon-button" onClick={onClose} aria-label="Close"><X size={18} /></button></div><form onSubmit={submit} className="incident-form"><label>Title<input minLength={4} maxLength={120} required value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Brief incident title" /></label><label>Description<textarea minLength={10} maxLength={5000} required value={description} onChange={(event) => setDescription(event.target.value)} rows={4} placeholder="Relevant details" /></label><div className="form-row"><label>Latitude<input type="number" min="-90" max="90" step="any" value={latitude} onChange={(event) => setLatitude(event.target.value)} /></label><label>Longitude<input type="number" min="-180" max="180" step="any" value={longitude} onChange={(event) => setLongitude(event.target.value)} /></label></div><small>Category and AI review flags are generated by the backend.</small>{error && <div className="form-error" role="alert">{error}</div>}<div className="modal-actions"><button type="button" className="button button-outline" onClick={onClose}>Cancel</button><button className="button button-dark" disabled={busy}>{busy ? <LoaderCircle className="spin" size={15} /> : <Plus size={15} />} Create incident</button></div></form></motion.section></div>;
}

const allowedTransitions: Record<IncidentStatus, IncidentStatus[]> = {
  reported: ['under_review', 'closed'],
  under_review: ['assigned', 'in_progress', 'closed'],
  assigned: ['in_progress', 'closed'],
  in_progress: ['resolved', 'closed'],
  resolved: ['closed', 'in_progress'],
  closed: ['under_review'],
};

function IncidentDetail() {
  const { id = '' } = useParams();
  const incidentId = Number(id);
  const { user } = useAuth();
  const coordinator = user?.role === 'coordinator' || user?.role === 'administrator';
  const [item, setItem] = useState<Incident | null>(null);
  const [notes, setNotes] = useState<IncidentNote[]>([]);
  const [attachments, setAttachments] = useState<IncidentAttachment[]>([]);
  const [history, setHistory] = useState<StatusHistoryEntry[]>([]);
  const [duplicates, setDuplicates] = useState<DuplicateCandidate[]>([]);
  const [classification, setClassification] = useState<Classification | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [reload, setReload] = useState(0);
  const [noteText, setNoteText] = useState('');
  const [statusReason, setStatusReason] = useState('');
  const [nextStatus, setNextStatus] = useState<IncidentStatus | ''>('');
  const [coordinatorId, setCoordinatorId] = useState('');
  const [busy, setBusy] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');

  useEffect(() => {
    let active = true;
    if (!Number.isInteger(incidentId) || incidentId < 1) {
      setError('Incident ID must be a positive number.');
      setLoading(false);
      return () => { active = false; };
    }
    setLoading(true);
    setError('');
    const load = async () => {
      try {
        const [record, noteRecords, attachmentRecords] = await Promise.all([
          fetchIncident(incidentId),
          fetchNotes(incidentId),
          fetchAttachments(incidentId),
        ]);
        const [historyRecords, duplicateRecords] = coordinator
          ? await Promise.all([fetchHistory(incidentId), fetchDuplicates(incidentId)])
          : [[], []];
        if (active) {
          setItem(record);
          setEditTitle(record.title);
          setEditDescription(record.description);
          setNotes(noteRecords);
          setAttachments(attachmentRecords);
          setHistory(historyRecords);
          setDuplicates(duplicateRecords);
        }
      } catch (requestError) {
        if (active) setError(readableError(requestError));
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => { active = false; };
  }, [incidentId, coordinator, reload]);

  const perform = async (action: () => Promise<unknown>, successMessage?: string) => {
    setBusy(true);
    setActionError('');
    try {
      await action();
      if (successMessage) setActionError(successMessage);
      setReload((value) => value + 1);
    } catch (requestError) {
      setActionError(readableError(requestError));
    } finally {
      setBusy(false);
    }
  };

  const download = async (attachment: IncidentAttachment) => {
    try {
      const blob = await downloadAttachment(incidentId, attachment.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = attachment.original_filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setActionError(readableError(requestError));
    }
  };

  if (loading) return <Shell title="Incident details"><section className="panel"><Loading label="Retrieving incident from API…" /></section></Shell>;
  if (error || !item) return <Shell title="Incident details"><ConnectionBanner error={error || 'Incident was not returned by the API.'} onRetry={() => setReload((value) => value + 1)} /></Shell>;
  return (
    <Shell title="Incident details">
      <div className="detail-back"><Link to="/app/incidents" className="text-link"><ArrowRight className="back-arrow" size={15} /> Back to incidents</Link><button className="button button-outline button-small" onClick={() => setReload((value) => value + 1)}><RefreshCw size={14} /> Refresh</button></div>
      <section className="detail-hero"><div className="detail-hero-top"><span className="detail-label"><Siren size={15} /> INCIDENT RECORD</span><span className="mono">#{item.id}</span></div><h2>{item.title}</h2><p>{item.description}</p><div className="detail-pills"><StatusPill value={categoryLabels[item.category]} /><StatusPill value={statusLabels[item.status]} /></div><p className="detail-meta">Created {formatDate(item.created_at)} · {item.ai_review_flag ? 'Human review required' : 'No review flag returned'}</p></section>
      {actionError && <div className={actionError.startsWith('Request') || actionError.includes('permission') ? 'form-error' : 'success-message'} role="status">{actionError}</div>}
      <div className="detail-columns">
        <section className="panel detail-panel"><div className="panel-heading"><div><span className="panel-kicker">RECORD INFORMATION</span><h2>Incident overview</h2></div></div><div className="detail-field"><span>Reporter ID</span><b>{item.reporter_id}</b></div><div className="detail-field"><span>Assigned to</span><b>{item.assigned_to ?? 'Unassigned'}</b></div><div className="detail-field"><span>Coordinates</span><b>{item.latitude !== null && item.longitude !== null ? `${item.latitude}, ${item.longitude}` : 'Not supplied'}</b></div><div className="detail-field"><span>AI confidence</span><b>{item.ai_confidence === null ? 'Not provided' : `${(item.ai_confidence * 100).toFixed(1)}% (uncalibrated score)`}</b></div><div className="detail-field"><span>AI summary</span><b>{item.ai_summary || 'Not provided'}</b></div></section>
        <section className="panel detail-panel"><div className="panel-heading"><div><span className="panel-kicker">AI DECISION SUPPORT</span><h2>Classification</h2></div></div><p className="muted-copy">AI output is decision support only; this is not emergency triage.</p>{classification && <div className="classification-result"><b>{categoryLabels[classification.category]}</b><p>{classification.summary}</p><small>{classification.method} · {classification.review_required ? 'Human review required' : 'Review not flagged'} · {classification.confidence === null ? 'No confidence score' : `Score ${(classification.confidence * 100).toFixed(1)}%`}</small><p>{classification.notice}</p></div>}<button className="button button-outline full-button" disabled={busy} onClick={() => void perform(async () => setClassification(await classifyIncident(item.description)))}>Classify description</button></section>
      </div>
      <section className="panel detail-panel workflow-panel"><div className="panel-heading"><div><span className="panel-kicker">DISCUSSION</span><h2>Incident notes</h2></div></div>{notes.length ? notes.map((note) => <article className="note-row" key={note.id}><p>{note.content}</p><small>User {note.author_id} · {formatDate(note.created_at)}</small></article>) : <p className="muted-copy">No notes have been added.</p>}<form className="inline-form" onSubmit={(event) => { event.preventDefault(); void perform(async () => { await createNote(incidentId, noteText); setNoteText(''); }); }}><label className="sr-only" htmlFor="new-note">Add a note</label><textarea id="new-note" required maxLength={2000} value={noteText} onChange={(event) => setNoteText(event.target.value)} placeholder="Add a note (up to 2,000 characters)" /><button className="button button-dark button-small" disabled={busy || !noteText.trim()}>Add note</button></form></section>
      <section className="panel detail-panel workflow-panel"><div className="panel-heading"><div><span className="panel-kicker">EVIDENCE</span><h2>Attachments</h2></div></div><p className="muted-copy">JPEG, PNG, and WebP images up to 5 MB.</p>{attachments.map((attachment) => <div className="attachment-row" key={attachment.id}><span>{attachment.original_filename}</span><button className="button button-outline button-small" onClick={() => void download(attachment)}>Download</button></div>)}{attachments.length === 0 && <p className="muted-copy">No attachments uploaded.</p>}<label className="upload-control">Upload image<input type="file" accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={(event) => { const file = event.target.files?.[0]; if (!file) return; if (file.size > 5 * 1024 * 1024) { setActionError('Image exceeds the 5 MB limit.'); event.target.value = ''; return; } void perform(() => uploadAttachment(incidentId, file)); event.target.value = ''; }} /></label></section>
      {coordinator && <div className="detail-columns">
        <section className="panel detail-panel"><div className="panel-heading"><div><span className="panel-kicker">COORDINATION</span><h2>Status and assignment</h2></div></div><div className="inline-form"><label>Next status<select value={nextStatus} onChange={(event) => setNextStatus(event.target.value as IncidentStatus | '')}><option value="">Choose status</option>{allowedTransitions[item.status].map((status) => <option key={status} value={status}>{statusLabels[status]}</option>)}</select></label><label>Reason<input maxLength={500} value={statusReason} onChange={(event) => setStatusReason(event.target.value)} /></label><button className="button button-dark button-small" disabled={busy || !nextStatus} onClick={() => nextStatus && void perform(() => changeIncidentStatus(incidentId, nextStatus, statusReason))}>Update status</button></div><form className="inline-form" onSubmit={(event) => { event.preventDefault(); const target = Number(coordinatorId); if (Number.isInteger(target) && target > 0) void perform(() => assignIncident(incidentId, target)); else setActionError('Enter a valid coordinator user ID.'); }}><label>Coordinator user ID<input type="number" min="1" required value={coordinatorId} onChange={(event) => setCoordinatorId(event.target.value)} /></label><button className="button button-outline button-small" disabled={busy}>Assign incident</button></form></section>
        <section className="panel detail-panel"><div className="panel-heading"><div><span className="panel-kicker">AUDIT TRAIL</span><h2>Status history</h2></div></div>{history.length ? history.map((entry, index) => <div className="history-row" key={`${entry.created_at}-${index}`}><b>{entry.old_status} → {entry.new_status}</b><small>{entry.reason || 'No reason supplied'} · {formatDate(entry.created_at)}</small></div>) : <p className="muted-copy">No status changes recorded.</p>}<div className="panel-heading duplicates-heading"><div><span className="panel-kicker">POSSIBLE MATCHES</span><h2>Duplicate suggestions</h2></div></div>{duplicates.length ? duplicates.map((match) => <div className="history-row" key={match.incident_id}><Link to={`/app/incidents/${match.incident_id}`}>Incident #{match.incident_id}</Link><small>{Math.round(match.similarity * 100)}% text similarity · {match.reason}</small></div>) : <p className="muted-copy">No similar incidents returned.</p>}</section>
      </div>}
      <section className="panel detail-panel workflow-panel"><div className="panel-heading"><div><span className="panel-kicker">EDIT RECORD</span><h2>Update incident details</h2></div></div><p className="muted-copy">The backend permits reporter edits only on their own incidents while status is reported. Coordinator permissions are enforced by the API.</p><form className="incident-form" onSubmit={(event) => { event.preventDefault(); void perform(() => updateIncident(incidentId, { title: editTitle, description: editDescription })); }}><label>Title<input minLength={4} maxLength={120} required value={editTitle} onChange={(event) => setEditTitle(event.target.value)} /></label><label>Description<textarea minLength={10} maxLength={5000} required value={editDescription} onChange={(event) => setEditDescription(event.target.value)} rows={3} /></label><button className="button button-outline button-small" disabled={busy}>Save changes</button></form></section>
    </Shell>
  );
}

function Login() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const { user, ready, signIn, signUp } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/app';
  useEffect(() => { if (ready && user) navigate(from, { replace: true }); }, [ready, user, navigate, from]);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      if (mode === 'register') await signUp(email, password);
      else await signIn(email, password);
      navigate(from, { replace: true });
    } catch (requestError) {
      setError(readableError(requestError));
    } finally {
      setBusy(false);
    }
  };
  return <div className="login-page"><div className="login-top"><Brand light /><Link className="text-link" to="/">Back to home <ArrowRight size={15} /></Link></div><div className="login-card"><div className="login-emblem"><HeartPulse size={25} /></div><div className="section-kicker">LIFELINE AI / AUTHENTICATION</div><h1>{mode === 'login' ? <>Welcome to<br /><em>operations.</em></> : <>Create your<br /><em>reporter account.</em></>}</h1><p>{mode === 'login' ? 'Sign in using your backend account.' : 'New accounts are created with the reporter role.'}</p><form onSubmit={submit} className="incident-form"><label>Email<input type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label><label>Password<input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={mode === 'register' ? 10 : undefined} maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} placeholder={mode === 'register' ? 'At least 10 characters' : 'Your password'} /></label>{error && <div className="form-error" role="alert">{error}</div>}<button className="button button-dark full-button" disabled={busy || !ready}>{busy ? <LoaderCircle size={16} className="spin" /> : <LogIn size={16} />}{mode === 'login' ? 'Sign in securely' : 'Create account'}</button></form><button className="text-link auth-toggle" onClick={() => { setMode((value) => value === 'login' ? 'register' : 'login'); setError(''); }}>{mode === 'login' ? 'Need an account? Register' : 'Already registered? Sign in'}</button><div className="login-security"><ShieldCheck size={15} /> Authentication and authorization are handled by FastAPI.</div></div><div className="login-foot">LifeLine AI <span>·</span> Not an emergency service</div></div>;
}

function NotFound() {
  return <div className="not-found"><Brand light /><div><span className="section-kicker">404 / NOT FOUND</span><h1>This page isn't<br /><em>on the map.</em></h1><Link to="/app" className="button button-dark">Back to overview <ArrowRight size={16} /></Link></div></div>;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export default function App() {
  return <AuthProvider><Routes><Route path="/" element={<PublicHome />} /><Route path="/app/login" element={<Login />} /><Route path="/app" element={<Protected><Overview /></Protected>} /><Route path="/app/incidents" element={<Protected><Incidents /></Protected>} /><Route path="/app/incidents/:id" element={<Protected><IncidentDetail /></Protected>} /><Route path="*" element={<NotFound />} /></Routes></AuthProvider>;
}
