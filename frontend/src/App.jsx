import { useState } from 'react'
import { uploadForm, generateFields, downloadFilled, fileUrl } from './api'

const STEPS = ['양식 업로드', '컨셉 입력', '미리보기·다운로드']

// 대시보드 최근 작업 (샘플 — 히스토리 API 연동 전까지 화면 설계용)
const RECENT = [
  { name: '2025_06_견적서_A사납품.pdf', meta: '오늘 14:22 · 필드 18개', status: 'done' },
  { name: '교육훈련_수강신청서_김세경.pdf', meta: '오늘 11:05 · 필드 11개', status: 'done' },
  { name: '비품구매_신청서_07.pdf', meta: '어제 16:40 · 필드 9개', status: 'progress' },
]

export default function App() {
  const [view, setView] = useState('dashboard') // dashboard | create
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

  const groundedCount = rows.filter((r) => r.grounded).length

  return (
    <div className="layout">
      <Sidebar view={view} onDashboard={goDashboard} onCreate={goCreate} />

      <div className="main-col">
        <Topbar />

        <div className="content">
          {error && <div className="alert">⚠ {error}</div>}

          {view === 'dashboard' && <Dashboard onCreate={goCreate} />}

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

function Sidebar({ view, onDashboard, onCreate }) {
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
        <button className="nav-item" disabled>
          <span className="nav-ico">🗂</span> 문서 관리 <span className="nav-badge">12</span>
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
function Dashboard({ onCreate }) {
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
        <button className="dash-card" disabled>
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
          {RECENT.map((r) => (
            <li key={r.name} className="recent-item">
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

function ConceptStep({ form, concept, setConcept, onGenerate, onBack, loading }) {
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
