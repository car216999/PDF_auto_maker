import { useState } from 'react'
import { uploadForm, generateFields, downloadFilled, fileUrl } from './api'

const STEPS = ['양식 업로드', '컨셉 입력', '미리보기·다운로드']

export default function App() {
  const [step, setStep] = useState(0)
  const [form, setForm] = useState(null) // { form_id, fields[], ... }
  const [concept, setConcept] = useState('')
  const [rows, setRows] = useState([]) // [{ name, label, value, grounded }]
  const [model, setModel] = useState('')
  const [downloaded, setDownloaded] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const labelOf = (name) =>
    form?.fields.find((f) => f.name === name)?.label || name

  async function handleUpload(file) {
    if (!file) return
    setError('')
    setLoading(true)
    try {
      const f = await uploadForm(file)
      setForm(f)
      setStep(1)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleGenerate() {
    setError('')
    setLoading(true)
    try {
      const result = await generateFields(form.form_id, concept)
      setModel(result.model)
      setRows(
        result.fields.map((f) => ({
          name: f.name,
          label: labelOf(f.name),
          value: f.value,
          grounded: f.grounded,
        })),
      )
      setDownloaded(false)
      setStep(2)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function editValue(i, v) {
    setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, value: v } : r)))
  }

  async function handleDownload() {
    setError('')
    setLoading(true)
    try {
      await downloadFilled(
        form.form_id,
        rows.map((r) => ({ name: r.name, value: r.value, grounded: r.grounded })),
      )
      setDownloaded(true)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setStep(0)
    setForm(null)
    setConcept('')
    setRows([])
    setDownloaded(false)
    setError('')
  }

  const groundedCount = rows.filter((r) => r.grounded).length

  return (
    <div className="app">
      <header className="header">
        <h1>뚝딱 <span>TookTak</span></h1>
        <p>빈 PDF 양식 + 컨셉 입력만으로 완성 문서를 — 완전 로컬, 외부 전송 0건</p>
      </header>

      <Stepper step={step} />

      {error && <div className="alert">⚠ {error}</div>}

      <main className="card">
        {step === 0 && <UploadStep onUpload={handleUpload} loading={loading} />}

        {step === 1 && (
          <ConceptStep
            form={form}
            concept={concept}
            setConcept={setConcept}
            onGenerate={handleGenerate}
            onBack={reset}
            loading={loading}
          />
        )}

        {step === 2 && (
          <PreviewStep
            rows={rows}
            model={model}
            groundedCount={groundedCount}
            editValue={editValue}
            onDownload={handleDownload}
            downloaded={downloaded}
            fileHref={fileUrl(form.form_id)}
            onRestart={reset}
            loading={loading}
          />
        )}
      </main>

      <footer className="footer">
        Qwen3 8B · nomic-embed-text · PyMuPDF · ChromaDB — 모두 로컬에서 동작
      </footer>
    </div>
  )
}

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
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragging(false)
        onUpload(e.dataTransfer.files[0])
      }}
    >
      <p className="big">📄 빈 PDF 양식을 끌어다 놓거나 선택하세요</p>
      <p className="hint">AcroForm 입력 필드가 있는 견적서·신청서 등</p>
      <label className="btn">
        {loading ? '분석 중…' : '파일 선택'}
        <input
          type="file"
          accept="application/pdf"
          hidden
          disabled={loading}
          onChange={(e) => onUpload(e.target.files[0])}
        />
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
      <textarea
        className="textarea"
        rows={3}
        placeholder="예: 주식회사 엑시오의 클라우드 서버 구축 견적. 단가 300만원, 수량 2대."
        value={concept}
        onChange={(e) => setConcept(e.target.value)}
      />

      <div className="actions">
        <button className="btn ghost" onClick={onBack} disabled={loading}>
          처음으로
        </button>
        <button
          className="btn"
          onClick={onGenerate}
          disabled={loading || !concept.trim()}
        >
          {loading ? '생성 중… (로컬 LLM)' : '문서 생성'}
        </button>
      </div>
    </div>
  )
}

function PreviewStep({
  rows, model, groundedCount, editValue, onDownload, downloaded, fileHref,
  onRestart, loading,
}) {
  return (
    <div>
      <div className="row-between">
        <h2>미리보기</h2>
        <span className="badge">
          {model} · 근거 기반 {groundedCount}/{rows.length}
        </span>
      </div>
      <p className="hint">
        값을 직접 수정할 수 있습니다. <b className="g-on">근거</b>는 사내 문서에서 찾은 값,
        <b className="g-off"> 추론</b>은 모델이 계산·추정한 값입니다.
      </p>

      <table className="preview">
        <thead>
          <tr><th>항목</th><th>값</th><th>출처</th></tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.name}>
              <td className="label-cell">{r.label}</td>
              <td>
                <input
                  className="cell-input"
                  value={r.value}
                  onChange={(e) => editValue(i, e.target.value)}
                />
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
        <button className="btn ghost" onClick={onRestart} disabled={loading}>
          새 문서
        </button>
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
