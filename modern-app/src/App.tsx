import { useEffect, useMemo, useState } from 'react'
import exampleCsv from '../example_data/animals.csv?raw'

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

  const handleAddGene = async (gene: string, geneClass: string) => {
    const form = new FormData()
    form.append('gene', gene)
    form.append('gene_class', geneClass)
    await fetch('http://localhost:8002/genes/add', { method: 'POST', body: form })
    loadGenes().catch(() => {})
  }

  const hasResults = directPairs.length > 0 || indirectPairs.length > 0

  return (
    <div className="ui-container">
      <div className="ui-stack">
        <header className="ui-header">
          <h1 className="ui-title">Mice Breeding Pair Selector</h1>
          <p className="ui-subtitle">Upload colony sheets, manage genes, and compute direct/indirect breeder pairs.</p>
        </header>

        {error && (
          <div className="ui-alert error">
            <div>
              <strong>Error:</strong> {error}
            </div>
            <button onClick={() => setError(null)} className="ui-btn ghost compact">Dismiss</button>
          </div>
        )}

        <section className="ui-panel">
          <div className="ui-stack sm">
            <div className="ui-row">
              <div>
                <div className="ui-label">Data Source</div>
                <div className="ui-hint">Excel/CSV upload or example data.</div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={useExample}
                    onChange={(e) => setUseExample(e.target.checked)}
                  />
                  <span>Use Example Data</span>
                </label>
                <label className="ui-btn ghost compact">
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
            </div>

            <div className="ui-alert">
              <div>
                <strong>Loaded breeders:</strong> {breeders.length} · <strong>Genes detected:</strong> {Object.values(genes).flat().length}
              </div>
            </div>

            <div className="ui-panel compact">
              <div className="ui-row">
                <div>
                  <div className="ui-label">Need to reformat your sheet?</div>
                  <div className="ui-hint">Paste this prompt into ChatGPT, Gemini, or Grok; upload the returned CSV.</div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <a href="https://chat.openai.com/" target="_blank" rel="noreferrer" className="ui-btn ghost compact">ChatGPT</a>
                  <a href="https://gemini.google.com/app" target="_blank" rel="noreferrer" className="ui-btn ghost compact">Gemini</a>
                  <a href="https://grok.com/" target="_blank" rel="noreferrer" className="ui-btn ghost compact">Grok</a>
                </div>
              </div>
              <pre className="ui-codeblock">Convert to CSV with headers: breeder_name, gender, strain, sheet, cre, reporter, flox1, flox2, age. Normalize gender to male/female, set sheet to Sheet1 if missing, keep gene markers as typed, age in weeks numeric. Output CSV only.</pre>
            </div>

            <div className="ui-field">
              <div className="ui-label">Desired Genotype</div>
              <div className="flex gap-2">
                <input
                  className="ui-input flex-1"
                  value={desiredGenotypeText}
                  onChange={(e) => setDesiredGenotypeText(e.target.value)}
                  placeholder="cre +/- reporter +/+ flox1 f/+"
                />
                <button className="ui-btn secondary" onClick={() => setDesiredGenotypeText('cre +/- reporter +/+')}>
                  Example
                </button>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <span className="ui-hint">Min probability (%)</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  className="ui-input compact w-24"
                  value={minProb}
                  onChange={(e) => setMinProb(parseFloat(e.target.value) || 0)}
                />
              </label>
            </div>

            <div className="grid gap-2">
              <button
                onClick={handleFindPairs}
                disabled={loading}
                data-testid="process-btn"
                className="ui-btn primary w-full"
              >
                {loading ? 'Processing…' : 'Find Breeder Pairs'}
              </button>
              {hasResults && (
                <button onClick={handleExport} className="ui-btn secondary w-full">
                  Export to Excel
                </button>
              )}
            </div>

            <div className="ui-field">
              <div className="ui-label">Gene Library</div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(genes).map(([cls, list]) => (
                  <span key={cls} className="ui-pill">{cls}: {list.join(', ')}</span>
                ))}
                {!Object.keys(genes).length && <span className="ui-hint">No genes loaded</span>}
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                <input id="gene-name" className="ui-input compact flex-1" placeholder="gene name" />
                <input id="gene-class" className="ui-input compact w-32" placeholder="Class e.g. Cre" />
                <button
                  className="ui-btn secondary compact"
                  onClick={() => {
                    const g = (document.getElementById('gene-name') as HTMLInputElement).value
                    const c = (document.getElementById('gene-class') as HTMLInputElement).value
                    if (g && c) handleAddGene(g, c)
                  }}
                >
                  Add Gene
                </button>
              </div>
            </div>
          </div>
        </section>

        <section className="ui-panel">
          <h2 className="ui-h2">Results</h2>

          {directPairs.length > 0 && (
            <div className="ui-panel compact">
              <h3 className="ui-h2">Direct Pairs (probability above min)</h3>
              <div className="overflow-x-auto">
                <table className="ui-table">
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
            <div className="ui-panel compact">
              <h3 className="ui-h2">Indirect Pairs (similarity)</h3>
              <div className="overflow-x-auto">
                <table className="ui-table">
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
            <div className="ui-panel compact text-center">
              <p className="ui-hint">Results will appear here after processing.</p>
            </div>
          )}

          {breeders.length > 0 && (
            <div className="ui-panel compact">
              <h3 className="ui-h2">Breeder Preview</h3>
              <div className="overflow-x-auto">
                <table className="ui-table">
                  <thead>
                    <tr>
                      {Object.keys(breeders[0]).slice(0, 6).map(key => (
                        <th key={key}>{key}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {breeders.slice(0, 5).map((row, idx) => (
                      <tr key={idx}>
                        {Object.keys(breeders[0]).slice(0, 6).map(key => (
                          <td key={key}>{String(row[key] ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                {breeders.length > 5 && <p className="ui-hint">Showing first 5 of {breeders.length}</p>}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

export default App
