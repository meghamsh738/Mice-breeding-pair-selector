import { useEffect, useMemo, useState } from 'react'
import {
  Database,
  Download,
  Dna,
  FlaskConical,
  RefreshCw,
  Search,
  Upload
} from 'lucide-react'
import exampleCsv from '../example_data/animals.csv?raw'
import './App.css'

type Breeder = Record<string, string | number | null>

interface PairResult {
  Male: string
  Female: string
  Probability?: number
  Similarity?: number
  Male_Sheet?: string
  Female_Sheet?: string
  Same_Strain?: boolean
  Breeder_Genotypes?: Record<string, Record<string, string>>
}

const parseCsvBreeders = (text: string): Breeder[] => {
  const lines = text.trim().split('\n').filter(Boolean)
  if (lines.length < 2) return []
  const headers = lines[0].split(',').map(h => h.trim().toLowerCase())
  return lines.slice(1).map(line => {
    const cols = line.split(',').map(c => c.trim())
    const row: Breeder = {}
    headers.forEach((h, idx) => { row[h] = cols[idx] ?? '' })
    return row
  })
}

const parseDesiredGenotype = (input: string): Record<string, string> => {
  const tokens = input.trim().split(/\s+/)
  const result: Record<string, string> = {}
  for (let i = 0; i < tokens.length - 1; i += 2) {
    const gene = tokens[i].replace(':', '').toLowerCase()
    const allele = tokens[i + 1]
    if (gene && allele) result[gene] = allele
  }
  // also support gene:allele pairs separated by spaces
  input.split(/\s+/).forEach(token => {
    const [g, a] = token.split(':')
    if (g && a) result[g.toLowerCase()] = a
  })
  return result
}

function App() {
  const [breeders, setBreeders] = useState<Breeder[]>([])
  const [genes, setGenes] = useState<Record<string, string[]>>({})
  const [desiredGenotypeText, setDesiredGenotypeText] = useState('cre +/- reporter +/+')
  const [minProb, setMinProb] = useState(0)
  const [directPairs, setDirectPairs] = useState<PairResult[]>([])
  const [indirectPairs, setIndirectPairs] = useState<PairResult[]>([])
  const [useExample, setUseExample] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [geneName, setGeneName] = useState('')
  const [geneClass, setGeneClass] = useState('')

  const parsedDesired = useMemo(() => parseDesiredGenotype(desiredGenotypeText), [desiredGenotypeText])

  useEffect(() => {
    if (useExample) {
      const parsed = parseCsvBreeders(exampleCsv)
      setBreeders(parsed)
    }
  }, [useExample])

  const loadGenes = async () => {
    const res = await fetch('http://localhost:8002/genes')
    if (res.ok) {
      setGenes(await res.json())
    }
  }

  useEffect(() => {
    loadGenes().catch(() => {})
  }, [])

  const handleUpload = async (file: File) => {
    setLoading(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const response = await fetch('http://localhost:8002/upload', { method: 'POST', body: formData })
      if (!response.ok) throw new Error('Upload failed')
      const data = await response.json()
      setBreeders(data.breeders || [])
      setGenes(data.genes || {})
      setUseExample(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  const handleFindPairs = async () => {
    if (!Object.keys(parsedDesired).length) {
      setError('Enter a desired genotype (e.g., "cre +/- reporter +/+")')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('http://localhost:8002/find-pairs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          breeders,
          desired_genotype: parsedDesired,
          min_prob: minProb,
          use_example: useExample
        })
      })
      if (!response.ok) throw new Error('Pairing failed')
      const data = await response.json()
      setDirectPairs(data.direct_pairs || [])
      setIndirectPairs(data.indirect_pairs || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pairing failed')
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    try {
      const response = await fetch('http://localhost:8002/export-breeders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          breeders,
          desired_genotype: parsedDesired,
          min_prob: minProb,
          use_example: useExample
        })
      })
      if (!response.ok) throw new Error('Export failed')
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'breeder_pairs.xlsx'
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed')
    }
  }

  const handleAddGene = async (gene: string, geneClassValue: string) => {
    const form = new FormData()
    form.append('gene', gene)
    form.append('gene_class', geneClassValue)
    await fetch('http://localhost:8002/genes/add', { method: 'POST', body: form })
    loadGenes().catch(() => {})
  }

  const hasResults = directPairs.length > 0 || indirectPairs.length > 0
  const statusLabel = loading ? 'Processing' : 'Ready'
  const statusClass = loading ? 'warning' : 'success'
  const geneCount = Object.values(genes).flat().length

  return (
    <div className="app-bg">
      <header className="panel">
        <div className="lab-head">
          <div>
            <p className="eyebrow">Breeder pairing</p>
            <h2>Mice Breeding Pair Selector</h2>
            <p className="muted">Target a genotype and surface direct + indirect breeder matches.</p>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <span className={`status-chip ${statusClass}`}>{statusLabel}</span>
            <span className="pill soft">
              <Database className="icon" aria-hidden="true" />
              {breeders.length} breeders
            </span>
            <span className="pill">
              <Dna className="icon" aria-hidden="true" />
              Genes: {geneCount}
            </span>
            <span className="pill">
              <FlaskConical className="icon" aria-hidden="true" />
              Colony ready
            </span>
          </div>
        </div>
      </header>

      {error && (
        <div className="panel" role="alert">
          <div className="lab-head">
            <div>
              <p className="eyebrow">Alert</p>
              <h2>Error</h2>
              <p className="muted">{error}</p>
            </div>
            <button onClick={() => setError(null)} className="ghost">Dismiss</button>
          </div>
        </div>
      )}

      <div className="app-shell">
        <aside className="panel sidebar">
          <div className="lab-head">
            <div>
              <p className="eyebrow">Inputs</p>
              <h2>Data Intake</h2>
              <p className="muted">Upload breeders, tune genotype targets, and set pairing thresholds.</p>
            </div>
            <button className="pill soft" onClick={() => setUseExample(true)} type="button">
              <RefreshCw className="icon" aria-hidden="true" />
              Sample
            </button>
          </div>

          <div className="sidebar-section">
            <div className="section-title">Data Source</div>
            <p className="muted tiny">Upload CSV/XLSX or use the bundled example sheet.</p>
            <div className="chip-row">
              <label className="pill soft">
                <input
                  type="checkbox"
                  checked={useExample}
                  onChange={(e) => setUseExample(e.target.checked)}
                />
                <span>Use Example Data</span>
              </label>
              <label className="ghost">
                <Upload className="icon" aria-hidden="true" />
                Upload File
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) handleUpload(file)
                  }}
                />
              </label>
            </div>
            <div className="chip-row">
              <span className="pill soft">Loaded breeders: {breeders.length}</span>
              <span className="pill soft">Genes detected: {geneCount}</span>
            </div>
          </div>

          <div className="sidebar-section">
            <div className="section-title">Target Genotype</div>
            <p className="muted tiny">Use gene:allele or gene allele pairs (e.g., cre +/- reporter +/+).</p>
            <label className="field">
              <span className="eyebrow">Desired genotype</span>
              <input
                value={desiredGenotypeText}
                onChange={(e) => setDesiredGenotypeText(e.target.value)}
                placeholder="cre +/- reporter +/+ flox1 f/+"
                aria-label="Desired genotype"
              />
            </label>
            <div className="field-row">
              <button className="pill soft" onClick={() => setDesiredGenotypeText('cre +/- reporter +/+')} type="button">
                Example genotype
              </button>
              <label className="field">
                <span className="eyebrow">Min probability (%)</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={minProb}
                  onChange={(e) => setMinProb(parseFloat(e.target.value) || 0)}
                />
              </label>
            </div>
          </div>

          <div className="sidebar-section">
            <div className="section-title">Gene Library</div>
            <div className="chip-row">
              {Object.entries(genes).map(([cls, list]) => (
                <span key={cls} className="pill soft">{cls}: {list.join(', ')}</span>
              ))}
              {!Object.keys(genes).length && <span className="muted tiny">No genes loaded</span>}
            </div>
            <div className="template-row">
              <label className="field">
                <span className="eyebrow">Gene name</span>
                <input
                  value={geneName}
                  onChange={(e) => setGeneName(e.target.value)}
                  placeholder="gene name"
                />
              </label>
              <label className="field">
                <span className="eyebrow">Gene class</span>
                <input
                  value={geneClass}
                  onChange={(e) => setGeneClass(e.target.value)}
                  placeholder="Class e.g. Cre"
                />
              </label>
            </div>
            <button
              className="ghost"
              type="button"
              onClick={() => {
                if (!geneName || !geneClass) return
                handleAddGene(geneName, geneClass).then(() => {
                  setGeneName('')
                  setGeneClass('')
                })
              }}
            >
              <Dna className="icon" aria-hidden="true" />
              Add Gene
            </button>
          </div>

          <div className="sidebar-section">
            <div className="section-title">Actions</div>
            <div className="edit-actions">
              <button
                onClick={handleFindPairs}
                disabled={loading}
                data-testid="process-btn"
                className="accent"
                type="button"
              >
                {loading ? 'Processing…' : 'Find Breeder Pairs'}
              </button>
              {hasResults && (
                <button onClick={handleExport} className="ghost" type="button">
                  <Download className="icon" aria-hidden="true" />
                  Export to Excel
                </button>
              )}
            </div>
          </div>

          <div className="sidebar-section">
            <div className="section-title">Sheet Helper</div>
            <div className="link-panel">
              <div className="field">
                <span className="muted tiny">Paste this prompt into ChatGPT, Gemini, or Grok; upload the returned CSV.</span>
              </div>
              <div className="edit-actions">
                <a href="https://chat.openai.com/" target="_blank" rel="noreferrer" className="pill soft">ChatGPT</a>
                <a href="https://gemini.google.com/app" target="_blank" rel="noreferrer" className="pill soft">Gemini</a>
                <a href="https://grok.com/" target="_blank" rel="noreferrer" className="pill soft">Grok</a>
              </div>
              <pre className="data-textarea" aria-label="Formatting prompt">
                Convert to CSV with headers: breeder_name, gender, strain, sheet, cre, reporter, flox1, flox2, age. Normalize gender to male/female, set sheet to Sheet1 if missing, keep gene markers as typed, age in weeks numeric. Output CSV only.
              </pre>
            </div>
          </div>
        </aside>

        <section className="panel editor">
          <div className="editor-header">
            <div className="title-row">
              <h1>Results</h1>
              <span className={`status-chip ${hasResults ? 'success' : 'warning'}`}>
                {hasResults ? 'Ready' : 'Waiting'}
              </span>
            </div>
            <div className="chip-row">
              {directPairs.length > 0 && <span className="pill">Direct: {directPairs.length}</span>}
              {indirectPairs.length > 0 && <span className="pill soft">Indirect: {indirectPairs.length}</span>}
              <span className="pill soft">
                <Search className="icon" aria-hidden="true" />
                Min probability: {minProb}%
              </span>
            </div>
          </div>

          <div className="editor-body">
            {directPairs.length > 0 && (
              <div className="today-card">
                <div className="today-head">
                  <div>
                    <h2>Direct Pairs</h2>
                    <p className="muted tiny">Probability above minimum threshold.</p>
                  </div>
                  <span className="pill soft">High confidence</span>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Male</th>
                        <th>Female</th>
                        <th>Prob %</th>
                        <th>Strain match</th>
                      </tr>
                    </thead>
                    <tbody>
                      {directPairs.map((p, idx) => (
                        <tr key={idx}>
                          <td>{p.Male}</td>
                          <td>{p.Female}</td>
                          <td>{p.Probability?.toFixed(2)}</td>
                          <td>{p.Same_Strain ? 'Yes' : 'No'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {indirectPairs.length > 0 && (
              <div className="today-card">
                <div className="today-head">
                  <div>
                    <h2>Indirect Pairs</h2>
                    <p className="muted tiny">Similarity-based matches when direct pairs are unavailable.</p>
                  </div>
                  <span className="pill soft">Exploratory</span>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Male</th>
                        <th>Female</th>
                        <th>Similarity</th>
                        <th>Strain match</th>
                      </tr>
                    </thead>
                    <tbody>
                      {indirectPairs.map((p, idx) => (
                        <tr key={idx}>
                          <td>{p.Male}</td>
                          <td>{p.Female}</td>
                          <td>{p.Similarity?.toFixed(2)}</td>
                          <td>{p.Same_Strain ? 'Yes' : 'No'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {directPairs.length === 0 && indirectPairs.length === 0 && (
              <div className="empty">
                <p className="muted">Results will appear here after processing.</p>
              </div>
            )}

            {breeders.length > 0 && (
              <div className="today-card">
                <div className="today-head">
                  <div>
                    <h2>Breeder Preview</h2>
                    <p className="muted tiny">Showing the first 5 rows of your sheet.</p>
                  </div>
                  {breeders.length > 5 && <span className="pill soft">Total: {breeders.length}</span>}
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        {Object.keys(breeders[0]).slice(0, 6).map((key) => (
                          <th key={key}>{key}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {breeders.slice(0, 5).map((row, idx) => (
                        <tr key={idx}>
                          {Object.keys(breeders[0]).slice(0, 6).map((key) => (
                            <td key={key}>{String(row[key] ?? '')}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}

export default App
