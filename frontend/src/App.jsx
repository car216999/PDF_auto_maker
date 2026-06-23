import { useState, useEffect } from 'react'
import {
  uploadForm, generateFields, downloadFilled, fileUrl, fetchRecent, fetchIndexStats,
} from './api'

const STEPS = ['양식 업로드', '컨셉 입력', '미리보기·다운로드']

// 대시보드 최근 작업 (샘플 — 히스토리 API 연동 전까지 화면 설계용)
const RECENT = [
  { name: '2025_06_견적서_A사납품.pdf', meta: '오늘 14:22 · 필드 18개', status: 'done' },
  { name: '교육훈련_수강신청서_김세경.pdf', meta: '오늘 11:05 · 필드 11개', status: 'done' },
  { name: '비품구매_신청서_07.pdf', meta: '어제 16:40 · 필드 9개', status: 'progress' },
]

export default function App() {
  const [view, setView] = useState('dashboard') // dashboard | create | manage
  const [docCount, setDocCount] = useState(null)
  const [step, setStep] = useState(0)
  const [form, setForm] = useState(null)
  const [concept, setConcept] = useState('')
  const [rows, setRows] = useState([])
  const [model, setModel] = useState('')
  const [downloaded, setDownloaded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const labelOf = (name) => form?.fields.find((f) => f.name === name)?.label || name

  async function handleUpload(file) {
    if (!file) return
    setError(''); setLoading(true)
    try {
      const f = await uploadForm(file)
      setForm(f); setStep(1)
    } catch (e) { setError(e.message) } finally { setLoading(false) }
  }

  async function handleGenerate() {
    setError(''); setLoading(true)
    try {
      const result = await generateFields(form.form_id, concept)
      setModel(result.model)
      setRows(result.fields.map((f) => ({
        name: f.name, label: labelOf(f.name), value: f.value, grounded: f.grounded,
      })))
      setDownloaded(false); setStep(2)
    } catch (e) { setError(e.message) } finally { setLoading(false) }
  }

  function editValue(i, v) {
    setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, value: v } : r)))
  }

  async function handleDownload() {
    setError(''); setLoading(true)
    try {
      await downloadFilled(form.form_id,
        rows.map((r) => ({ name: r.name, value: r.value, grounded: r.grounded })))
      setDownloaded(true)
    } catch (e) { setError(e.message) } finally { setLoading(false) }
  }

  function reset() {
    setStep(0); setForm(null); setConcept(''); setRows([])
    setDownloaded(false); setError('')
  }

  function goCreate() { reset(); setView('create') }
  function goDashboard() { reset(); setView('dashboard') }
  function goManage() { reset(); setView('manage') }

  useEffect(() => {
    fetchRecent(1).then((r) => setDocCount(r.count ?? null))
  }, [view]) // 화면 전환 시 배지 갱신

  const groundedCount = rows.filter((r) => r.grounded).length

  return (
    <div className="layout">
      <Sidebar view={view} onDashboard={goDashboard} onCreate={goCreate}
        onManage={goManage} docCount={docCount} />

      <div className="main-col">
        <Topbar />

        <div className="content">
          {error && <div className="alert">⚠ {error}</div>}

          {view === 'dashboard' && <Dashboard onCreate={goCreate} onManage={goManage} />}

          {view === 'manage' && <DocManage onCreate={goCreate} />}

          {view === 'create' && (
            <div className="card-wrap">
              <Stepper step={step} />
              <main className="card">
                {step === 0 && <UploadStep onUpload={handleUpload} loading={loading} />}
                {step === 1 && (
                  <ConceptStep form={form} concept={concept} setConcept={setConcept}
                    onGenerate={handleGenerate} onBack={goDashboard} loading={loading} />
                )}
                {step === 2 && (
                  <PreviewStep rows={rows} model={model} groundedCount={groundedCount}
                    editValue={editValue} onDownload={handleDownload} downloaded={downloaded}
                    fileHref={fileUrl(form.form_id)} onRestart={goCreate} loading={loading} />
                )}
              </main>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ---------- 레이아웃 ---------- */
function Brand() {
  const [logoOk, setLogoOk] = useState(true)
  return (
    <div className="brand">
      {logoOk ? (
        <img src="/logo.png" alt="TOOKTAK" className="brand-logo"
          onError={() => setLogoOk(false)} />
      ) : (
        <>
          <span className="brand-mark">🧰</span>
          <span className="brand-name">TOOKTAK</span>
        </>
      )}
    </div>
  )
}

function Sidebar({ view, onDashboard, onCreate, onManage, docCount }) {
  return (
    <aside className="sidebar">
      <Brand />
      <nav className="nav">
        <div className="nav-group">메인</div>
        <button className={`nav-item ${view === 'dashboard' ? 'on' : ''}`} onClick={onDashboard}>
          <span className="nav-ico">▦</span> 대시보드
        </button>
        <button className={`nav-item ${view === 'create' ? 'on' : ''}`} onClick={onCreate}>
          <span className="nav-ico">＋</span> 새 문서 작성
        </button>
        <div className="nav-group">관리</div>
        <button className={`nav-item ${view === 'manage' ? 'on' : ''}`} onClick={onManage}>
          <span className="nav-ico">🗂</span> 문서 관리
          {docCount != null && docCount > 0 && <span className="nav-badge">{docCount}</span>}
        </button>
        <div className="nav-group">시스템</div>
        <button className="nav-item" disabled>
          <span className="nav-ico">⚙</span> 설정
        </button>
      </nav>
    </aside>
  )
}

function Topbar() {
  return (
    <header className="topbar">
      <span className="secure">● 🛡 Secure Local</span>
      <div className="topbar-right">
        <span className="user">👤 김세경 님</span>
        <button className="logout">⎋ 로그아웃</button>
        <span className="more">⋯</span>
      </div>
    </header>
  )
}

/* ---------- 대시보드 ---------- */
function fmtTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const today = new Date()
  const sameDay = d.toDateString() === today.toDateString()
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return sameDay ? `오늘 ${hh}:${mm}` : `${d.getMonth() + 1}월 ${d.getDate()}일 ${hh}:${mm}`
}

function Dashboard({ onCreate, onManage }) {
  const [items, setItems] = useState(RECENT) // 기본 샘플 → DB 있으면 교체
  useEffect(() => {
    fetchRecent().then((r) => {
      if (r.items && r.items.length) {
        setItems(r.items.map((it) => ({
          name: it.name,
          meta: `${fmtTime(it.created_at)} · 필드 ${it.fields}개`,
          status: it.status === '완료' || it.status === 'done' ? 'done' : 'progress',
        })))
      }
    })
  }, [])
  return (
    <div className="dash">
      <h1 className="dash-title">LLM·RAG 기반 지능형 문서처리(IDP) 에이전트</h1>
      <p className="dash-sub">빈 PDF 양식과 몇 가지 키워드만으로 완성된 문서를 뚝딱 생성하세요.</p>

      <div className="dash-cards">
        <button className="dash-card" onClick={onCreate}>
          <span className="dash-card-ico blue">📄</span>
          <div>
            <b>새 문서 작성</b>
            <p>AI가 PDF를 자동으로 작성합니다.</p>
          </div>
        </button>
        <button className="dash-card" onClick={onManage}>
          <span className="dash-card-ico gray">🗂</span>
          <div>
            <b>문서 관리</b>
            <p>RAG 인덱스 및 히스토리 관리.</p>
          </div>
        </button>
      </div>

      <section className="recent">
        <div className="row-between">
          <h2>최근 작업</h2>
          <a className="link">전체 보기 ›</a>
        </div>
        <ul className="recent-list">
          {items.map((r, i) => (
            <li key={r.name + i} className="recent-item">
              <span className="file-ico">📄</span>
              <div className="recent-meta">
                <b>{r.name}</b>
                <span>{r.meta}</span>
              </div>
              <span className={`status ${r.status}`}>
                {r.status === 'done' ? '완료' : '처리 중'}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

/* ---------- 문서 관리 ---------- */
function DocManage({ onCreate }) {
  const [docs, setDocs] = useState([])
  const [stats, setStats] = useState(null)
  const [loaded, setLoaded] = useState(false)
  useEffect(() => {
    fetchRecent(50).then((r) => { setDocs(r.items || []); setLoaded(true) })
    fetchIndexStats().then(setStats)
  }, [])
  return (
    <div className="dash">
      <h1 className="dash-title">문서 관리</h1>
      <p className="dash-sub">RAG 인덱스 현황과 생성 문서 이력을 관리해요.</p>

      <section className="recent" style={{ marginBottom: 18 }}>
        <h2>RAG 인덱스 현황</h2>
        <div className="stat-grid">
          <div className="stat"><b>{stats ? stats.chunks.toLocaleString() : '—'}</b><span>인덱싱된 청크</span></div>
          <div className="stat"><b>{stats ? stats.knowledge_files : '—'}</b><span>지식 문서</span></div>
          <div className="stat"><b>{stats ? stats.embed_model : '—'}</b><span>임베딩 모델</span></div>
          <div className="stat"><b>{stats ? stats.vector_db : '—'}</b><span>벡터 DB</span></div>
        </div>
        {stats && <p className="hint" style={{ marginTop: 10 }}>검색 방식: {stats.retrieval}</p>}
      </section>

      <section className="recent">
        <div className="row-between">
          <h2>문서 이력 ({docs.length})</h2>
          <a className="link" style={{ cursor: 'pointer' }} onClick={onCreate}>+ 새 문서 작성</a>
        </div>
        {loaded && docs.length === 0 ? (
          <p className="hint" style={{ padding: '24px 0', textAlign: 'center' }}>
            아직 생성한 문서가 없어요. <b>새 문서 작성</b>으로 시작하세요.
          </p>
        ) : (
          <div className="doc-table-wrap">
            <table className="doc-table">
              <thead>
                <tr><th>문서</th><th>필드</th><th>근거율</th><th>모델</th><th>상태</th><th>생성</th></tr>
              </thead>
              <tbody>
                {docs.map((d, i) => (
                  <tr key={i}>
                    <td className="doc-name">📄 {d.name}</td>
                    <td>{d.fields}개</td>
                    <td>{Math.round((d.grounded || 0) * 100)}%</td>
                    <td className="doc-model">{d.model}</td>
                    <td>
                      <span className={`status ${d.status === '완료' || d.status === 'done' ? 'done' : 'progress'}`}>
                        {d.status}
                      </span>
                    </td>
                    <td className="doc-date">{fmtTime(d.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

/* ---------- 작성 마법사 (기존 스텝) ---------- */
function Stepper({ step }) {
  return (
    <ol className="stepper">
      {STEPS.map((label, i) => (
        <li key={i} className={i === step ? 'active' : i < step ? 'done' : ''}>
          <span className="dot">{i < step ? '✓' : i + 1}</span>
          {label}
        </li>
      ))}
    </ol>
  )
}

function UploadStep({ onUpload, loading }) {
  const [dragging, setDragging] = useState(false)
  return (
    <div
      className={`dropzone ${dragging ? 'drag' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); onUpload(e.dataTransfer.files[0]) }}
    >
      <p className="big">📄 빈 PDF 양식을 끌어다 놓거나 선택하세요</p>
      <p className="hint">AcroForm 입력 필드가 있는 견적서·신청서 등</p>
      <label className="btn">
        {loading ? '분석 중…' : '파일 선택'}
        <input type="file" accept="application/pdf" hidden disabled={loading}
          onChange={(e) => onUpload(e.target.files[0])} />
      </label>
    </div>
  )
}

const GEN_STEPS = [
  { ico: '🔍', text: '사내 문서에서 근거를 찾는 중', sub: '하이브리드 검색 · BM25 + BGE-M3' },
  { ico: '🎯', text: '가장 정확한 근거를 고르는 중', sub: '2단계 정밀 검색 · cross-encoder 리랭킹' },
  { ico: '✍️', text: '근거를 바탕으로 항목을 채우는 중', sub: '로컬 LLM · Qwen3 8B (환각 제어)' },
  { ico: '🔒', text: '모든 처리를 기기 안에서 끝내는 중', sub: '외부 전송 0건 · 완전 로컬' },
]

function GeneratingOverlay({ filename, fields }) {
  const [i, setI] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setI((x) => (x + 1) % GEN_STEPS.length), 2800)
    return () => clearInterval(t)
  }, [])
  const s = GEN_STEPS[i]
  return (
    <div className="gen-overlay">
      <div className="gen-spinner" />
      <div className="gen-step" key={i}>
        <div className="gen-ico">{s.ico}</div>
        <b>{s.text}</b>
        <p>{s.sub}</p>
      </div>
      <ol className="gen-track">
        {GEN_STEPS.map((g, idx) => (
          <li key={idx} className={idx === i ? 'on' : idx < i ? 'done' : ''} />
        ))}
      </ol>
      <p className="gen-foot">{filename} · 필드 {fields}개 채우는 중 — 로컬 LLM, 보통 20~30초</p>
    </div>
  )
}

function ConceptStep({ form, concept, setConcept, onGenerate, onBack, loading }) {
  if (loading) return <GeneratingOverlay filename={form.filename} fields={form.fields.length} />
  return (
    <div>
      <div className="row-between">
        <h2>{form.filename}</h2>
        <span className="badge">필드 {form.fields.length}개 추출됨</span>
      </div>
      <div className="chips">
        {form.fields.map((f) => (
          <span key={f.name} className="chip">{f.label || f.name}</span>
        ))}
      </div>
      <label className="field-label">어떤 문서를 작성할까요? (컨셉·지시)</label>
      <textarea className="textarea" rows={3}
        placeholder="예: 스마트인재개발원이 발행하는 클라우드 서버 구축 견적. 단가 300만원, 수량 2대."
        value={concept} onChange={(e) => setConcept(e.target.value)} />
      <div className="actions">
        <button className="btn ghost" onClick={onBack} disabled={loading}>대시보드</button>
        <button className="btn" onClick={onGenerate} disabled={loading || !concept.trim()}>
          {loading ? '생성 중… (로컬 LLM)' : '문서 생성'}
        </button>
      </div>
    </div>
  )
}

function PreviewStep({
  rows, model, groundedCount, editValue, onDownload, downloaded, fileHref, onRestart, loading,
}) {
  return (
    <div>
      <div className="row-between">
        <h2>미리보기</h2>
        <span className="badge">{model} · 근거 기반 {groundedCount}/{rows.length}</span>
      </div>
      <p className="hint">
        값을 직접 수정할 수 있습니다. <b className="g-on">근거</b>는 사내 문서에서 찾은 값,
        <b className="g-off"> 추론</b>은 모델이 계산·추정한 값입니다.
      </p>
      <table className="preview">
        <thead><tr><th>항목</th><th>값</th><th>출처</th></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.name}>
              <td className="label-cell">{r.label}</td>
              <td>
                <input className="cell-input" value={r.value}
                  onChange={(e) => editValue(i, e.target.value)} />
              </td>
              <td>
                <span className={r.grounded ? 'g-on' : 'g-off'}>
                  {r.grounded ? '근거' : '추론'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="actions">
        <button className="btn ghost" onClick={onRestart} disabled={loading}>새 문서</button>
        <button className="btn" onClick={onDownload} disabled={loading}>
          {loading ? '주입 중…' : 'PDF 생성'}
        </button>
        {downloaded && (
          <a className="btn primary" href={fileHref} target="_blank" rel="noreferrer">
            ⬇ 완성 PDF 열기
          </a>
        )}
      </div>
    </div>
  )
}
