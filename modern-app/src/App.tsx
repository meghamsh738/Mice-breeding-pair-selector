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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <header className="text-center mb-10">
          <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent mb-3">
            Mice Breeding Pair Selector
          </h1>
          <p className="text-gray-600 text-lg">Upload colony sheets, manage genes, and compute direct/indirect breeder pairs.</p>
        </header>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            <strong>Error:</strong> {error}
            <button onClick={() => setError(null)} className="ml-4 text-red-900 underline">Dismiss</button>
          </div>
        )}

        <div className="grid lg:grid-cols-2 gap-6 items-start">
          <div className="bg-white rounded-2xl shadow-xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-gray-700">Data Source</p>
                <p className="text-xs text-gray-500">Excel/CSV upload or example data</p>
              </div>
              <div className="flex gap-3">
                <label className="inline-flex items-center gap-2 text-sm font-semibold text-gray-700">
                  <input
                    type="checkbox"
                    className="w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    checked={useExample}
                    onChange={(e) => setUseExample(e.target.checked)}
                  />
                  Use Example Data
                </label>
                <label className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-1 rounded cursor-pointer">
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

            <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-3 text-xs text-indigo-900">
              Loaded breeders: {breeders.length} | Genes detected: {Object.values(genes).flat().length}
            </div>

            <div className="space-y-2">
              <p className="text-sm font-semibold text-gray-700">Desired Genotype</p>
              <div className="flex gap-2">
                <input
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  value={desiredGenotypeText}
                  onChange={(e) => setDesiredGenotypeText(e.target.value)}
                  placeholder="cre +/- reporter +/+ flox1 f/+"
                />
                <button
                  className="text-xs bg-gray-100 px-3 py-2 rounded-lg"
                  onClick={() => setDesiredGenotypeText('cre +/- reporter +/+')}
                >
                  Example Genotype
                </button>
              </div>
              <label className="text-xs text-gray-600 flex items-center gap-2">
                Min probability (%)
                <input
                  type="number"
                  min="0"
                  max="100"
                  className="w-20 px-2 py-1 border border-gray-300 rounded"
                  value={minProb}
                  onChange={(e) => setMinProb(parseFloat(e.target.value) || 0)}
                />
              </label>
            </div>

            <div className="space-y-3">
              <button
                onClick={handleFindPairs}
                disabled={loading}
                data-testid="process-btn"
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold py-3 px-6 rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Processing...' : 'Find Breeder Pairs'}
              </button>
              {(directPairs.length > 0 || indirectPairs.length > 0) && (
                <button
                  onClick={handleExport}
                  className="w-full bg-green-600 text-white font-semibold py-3 px-6 rounded-lg hover:bg-green-700 transition-all duration-200 shadow-lg hover:shadow-xl"
                >
                  Export to Excel
                </button>
              )}
            </div>

            <div>
              <p className="text-sm font-semibold text-gray-700 mb-2">Gene Library</p>
              <div className="flex flex-wrap gap-2 text-xs">
                {Object.entries(genes).map(([cls, list]) => (
                  <span key={cls} className="bg-gray-100 px-3 py-1 rounded">{cls}: {list.join(', ')}</span>
                ))}
                {!Object.keys(genes).length && <span className="text-gray-500 text-xs">No genes loaded</span>}
              </div>
              <div className="mt-2 flex gap-2">
                <input id="gene-name" className="flex-1 px-2 py-1 border border-gray-300 rounded" placeholder="gene name" />
                <input id="gene-class" className="w-28 px-2 py-1 border border-gray-300 rounded" placeholder="Class e.g. Cre" />
                <button
                  className="text-xs bg-gray-200 px-3 rounded"
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

          <div className="bg-white rounded-2xl shadow-xl p-6 space-y-4">
            <h2 className="text-2xl font-bold text-gray-800">Results</h2>

            {directPairs.length > 0 && (
              <div className="border border-green-100 rounded-lg p-4">
                <h3 className="font-semibold text-green-800 mb-2">Direct Pairs (probability above min)</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-green-50">
                        <th className="px-2 py-1 text-left">Male</th>
                        <th className="px-2 py-1 text-left">Female</th>
                        <th className="px-2 py-1 text-left">Prob %</th>
                        <th className="px-2 py-1 text-left">Strain match</th>
                      </tr>
                    </thead>
                    <tbody>
                      {directPairs.map((p, idx) => (
                        <tr key={idx} className="border-t border-green-100">
                          <td className="px-2 py-1">{p.Male}</td>
                          <td className="px-2 py-1">{p.Female}</td>
                          <td className="px-2 py-1">{p.Probability?.toFixed(2)}</td>
                          <td className="px-2 py-1">{p.Same_Strain ? 'Yes' : 'No'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {indirectPairs.length > 0 && (
              <div className="border border-amber-100 rounded-lg p-4">
                <h3 className="font-semibold text-amber-800 mb-2">Indirect Pairs (similarity)</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-amber-50">
                        <th className="px-2 py-1 text-left">Male</th>
                        <th className="px-2 py-1 text-left">Female</th>
                        <th className="px-2 py-1 text-left">Similarity</th>
                        <th className="px-2 py-1 text-left">Strain match</th>
                      </tr>
                    </thead>
                    <tbody>
                      {indirectPairs.map((p, idx) => (
                        <tr key={idx} className="border-t border-amber-100">
                          <td className="px-2 py-1">{p.Male}</td>
                          <td className="px-2 py-1">{p.Female}</td>
                          <td className="px-2 py-1">{p.Similarity?.toFixed(2)}</td>
                          <td className="px-2 py-1">{p.Same_Strain ? 'Yes' : 'No'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {directPairs.length === 0 && indirectPairs.length === 0 && (
              <div className="text-center text-gray-400 py-10">
                Results will appear here after processing
              </div>
            )}

            {breeders.length > 0 && (
              <div>
                <h3 className="font-semibold text-gray-800 mb-2">Breeder Preview</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-gray-50">
                        {Object.keys(breeders[0]).slice(0, 6).map(key => (
                          <th key={key} className="px-2 py-1 text-left capitalize">{key}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {breeders.slice(0, 5).map((row, idx) => (
                        <tr key={idx} className="border-t border-gray-100">
                          {Object.keys(breeders[0]).slice(0, 6).map(key => (
                            <td key={key} className="px-2 py-1">{String(row[key] ?? '')}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {breeders.length > 5 && <p className="text-xs text-gray-500 mt-1">Showing first 5 of {breeders.length}</p>}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
