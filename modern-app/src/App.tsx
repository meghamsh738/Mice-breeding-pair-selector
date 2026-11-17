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
import { GuidedTutorial, type TutorialStep } from './GuidedTutorial'
import exampleCsv from '../example_data/animals.csv?raw'
import './App.css'

type Breeder = Record<string, string | number | null>

const API_BASE = 'http://127.0.0.1:18522'

interface PairResult {
  Pair_ID: string
  Male_ID: string
  Female_ID: string
  Male: string
  Female: string
  Probability?: number | null
  Ranking_Score?: number
  Rank_Basis?: string
  Locus_Probabilities?: Record<string, number>
  Similarity?: number
  Male_Sheet?: string
  Female_Sheet?: string
  Same_Strain?: boolean
  Breeder_Genotypes?: Record<string, Record<string, string>>
  Relationship?: string
  Shared_Parent_IDs?: string[]
  Status?: string
  Reasons?: string[]
  Assumptions?: string[]
}

interface PairResults {
  algorithm_version: string
  direct_pairs: PairResult[]
  indirect_pairs: PairResult[]
  needs_review_pairs: PairResult[]
  excluded_pairs: PairResult[]
  below_threshold_pairs: PairResult[]
  probability_method: string
  assumptions: Record<string, boolean>
}

interface SavedBreedingReview {
  breeders: Breeder[]
  desiredGenotypeText: string
  minProb: number
  useExample: boolean
  assumeMissingWildtype: boolean
  confirmSimpleInheritance: boolean
  confirmIndependentAssortment: boolean
  excludeSharedParent: boolean
  allowUnknownRelationship: boolean
  excludedPairs: string[][]
  results: PairResults | null
  selectedPairId: string
  selectionReason: string
  lockedPairId: string
}

const REVIEW_STORAGE_KEY = 'easylab-next:breeding:review:v1'

const loadSavedReview = (): Partial<SavedBreedingReview> => {
  try {
    const saved = localStorage.getItem(REVIEW_STORAGE_KEY)
    if (!saved) return {}
    const parsed = JSON.parse(saved) as Partial<SavedBreedingReview>
    if (parsed.results?.algorithm_version !== 'breeding-review-v2') {
      parsed.results = null
      parsed.selectedPairId = ''
      parsed.selectionReason = ''
      parsed.lockedPairId = ''
      parsed.assumeMissingWildtype = false
      parsed.confirmSimpleInheritance = false
      parsed.confirmIndependentAssortment = false
      parsed.allowUnknownRelationship = false
    }
    return parsed
  } catch {
    return {}
  }
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
  const [saved] = useState(loadSavedReview)
  const [breeders, setBreeders] = useState<Breeder[]>(saved.breeders ?? [])
  const [genes, setGenes] = useState<Record<string, string[]>>({})
  const [desiredGenotypeText, setDesiredGenotypeText] = useState(saved.desiredGenotypeText ?? 'cre +/- reporter +/+')
  const [minProb, setMinProb] = useState(saved.minProb ?? 0)
  const [useExample, setUseExample] = useState(saved.useExample ?? false)
  const [assumeMissingWildtype, setAssumeMissingWildtype] = useState(saved.assumeMissingWildtype ?? false)
  const [confirmSimpleInheritance, setConfirmSimpleInheritance] = useState(saved.confirmSimpleInheritance ?? false)
  const [confirmIndependentAssortment, setConfirmIndependentAssortment] = useState(saved.confirmIndependentAssortment ?? false)
  const [excludeSharedParent, setExcludeSharedParent] = useState(saved.excludeSharedParent ?? true)
  const [allowUnknownRelationship, setAllowUnknownRelationship] = useState(saved.allowUnknownRelationship ?? false)
  const [excludedPairs, setExcludedPairs] = useState<string[][]>(saved.excludedPairs ?? [])
  const [results, setResults] = useState<PairResults | null>(saved.results ?? null)
  const [selectedPairId, setSelectedPairId] = useState(saved.selectedPairId ?? '')
  const [selectionReason, setSelectionReason] = useState(saved.selectionReason ?? '')
  const [lockedPairId, setLockedPairId] = useState(saved.lockedPairId ?? '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [geneName, setGeneName] = useState('')
  const [geneClass, setGeneClass] = useState('')

  const parsedDesired = useMemo(() => parseDesiredGenotype(desiredGenotypeText), [desiredGenotypeText])
  const directPairs = results?.direct_pairs ?? []
  const indirectPairs = results?.indirect_pairs ?? []
  const needsReviewPairs = results?.needs_review_pairs ?? []
  const excludedResults = results?.excluded_pairs ?? []

  const invalidateReview = () => {
    setResults(null)
    setSelectedPairId('')
    setSelectionReason('')
    setLockedPairId('')
  }

  const startNewTargetReview = () => {
    invalidateReview()
    setAssumeMissingWildtype(false)
    setConfirmSimpleInheritance(false)
    setConfirmIndependentAssortment(false)
    setAllowUnknownRelationship(false)
  }

  useEffect(() => {
    const review: SavedBreedingReview = {
      breeders, desiredGenotypeText, minProb, useExample, assumeMissingWildtype, confirmSimpleInheritance,
      confirmIndependentAssortment, excludeSharedParent, allowUnknownRelationship,
      excludedPairs, results, selectedPairId, selectionReason, lockedPairId
    }
    try {
      localStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify(review))
    } catch {
      setError('This browser could not save the review on this device.')
    }
  }, [breeders, desiredGenotypeText, minProb, useExample, assumeMissingWildtype, confirmSimpleInheritance,
    confirmIndependentAssortment, excludeSharedParent, allowUnknownRelationship,
    excludedPairs, results, selectedPairId, selectionReason, lockedPairId])

  useEffect(() => {
    if (useExample) {
      const parsed = parseCsvBreeders(exampleCsv)
      setBreeders(parsed)
    }
  }, [useExample])

  const loadGenes = async () => {
    const res = await fetch(`${API_BASE}/genes`)
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
      const response = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData })
      if (!response.ok) throw new Error('Upload failed')
      const data = await response.json()
      setBreeders(data.breeders || [])
      setGenes(data.genes || {})
      setUseExample(false)
      startNewTargetReview()
      setExcludedPairs([])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  const runPairReview = async (specificExclusions = excludedPairs) => {
    if (!breeders.length && !useExample) {
      setError('Load breeder records or choose the example data before calculating pairs.')
      return
    }
    if (!Object.keys(parsedDesired).length) {
      setError('Enter a desired genotype (e.g., "cre +/- reporter +/+")')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/find-pairs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          breeders,
          desired_genotype: parsedDesired,
          min_prob: minProb,
          use_example: useExample,
          assume_missing_wildtype: assumeMissingWildtype,
          confirm_simple_inheritance: confirmSimpleInheritance,
          confirm_independent_assortment: confirmIndependentAssortment,
          exclude_shared_parent: excludeSharedParent,
          allow_unknown_relationship: allowUnknownRelationship,
          excluded_pairs: specificExclusions
        })
      })
      if (!response.ok) throw new Error('Pairing failed')
      const data = await response.json()
      setResults(data)
      setSelectedPairId('')
      setSelectionReason('')
      setLockedPairId('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pairing failed')
    } finally {
      setLoading(false)
    }
  }

  const handleFindPairs = () => runPairReview()

  const handleExport = async () => {
    try {
      const response = await fetch(`${API_BASE}/export-breeders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          breeders,
          desired_genotype: parsedDesired,
          min_prob: minProb,
          use_example: useExample,
          assume_missing_wildtype: assumeMissingWildtype,
          confirm_simple_inheritance: confirmSimpleInheritance,
          confirm_independent_assortment: confirmIndependentAssortment,
          exclude_shared_parent: excludeSharedParent,
          allow_unknown_relationship: allowUnknownRelationship,
          excluded_pairs: excludedPairs,
          reviewed_results: results,
          review_metadata: {
            target_genotype: parsedDesired,
            min_probability_percent: minProb,
            selected_pair_id: selectedPairId,
            selection_reason: selectionReason,
            locked_pair_id: lockedPairId,
            excluded_pairs: excludedPairs,
            saved_at: new Date().toISOString()
          }
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

  const selectedPair = directPairs.find(pair => pair.Pair_ID === selectedPairId)
  const rankedPosition = directPairs.findIndex(pair => pair.Pair_ID === selectedPairId)
  const lockSelectedPair = () => {
    if (!selectedPair) return
    if (rankedPosition > 0 && !selectionReason.trim()) {
      setError('Add a short reason when choosing a different eligible pair.')
      return
    }
    setLockedPairId(selectedPair.Pair_ID)
    setError(null)
  }

  const excludePair = (pair: PairResult) => {
    const updated = [...excludedPairs, [pair.Male_ID, pair.Female_ID]]
    setExcludedPairs(updated)
    setSelectedPairId('')
    setLockedPairId('')
    setSelectionReason('')
    runPairReview(updated)
  }

  const removeExclusion = (pair: PairResult) => {
    const updated = excludedPairs.filter(ids => !(
      ids[0] === pair.Male_ID && ids[1] === pair.Female_ID
      || ids[0] === pair.Female_ID && ids[1] === pair.Male_ID
    ))
    setExcludedPairs(updated)
    runPairReview(updated)
  }

  const previewColumns = useMemo(() => {
    if (!breeders.length) return []
    const available = Object.keys(breeders[0])
    const identityFields = ['breeder_id', 'breeder_name', 'gender', 'sire_id', 'dam_id', 'father_id', 'mother_id']
    return [...identityFields.filter(field => available.includes(field)), ...available.filter(field => !identityFields.includes(field))].slice(0, 8)
  }, [breeders])

  const renderCandidateTable = (
    pairs: PairResult[],
    rankOffset = 0,
    selectable = true,
  ) => (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Male</th>
            <th>Female</th>
            <th>{selectable ? (results?.probability_method === 'Independent assortment confirmed' || Object.keys(parsedDesired).length === 1 ? 'Probability' : 'Lowest locus') : 'Similarity score'}</th>
            <th>Per-locus results</th>
            <th>Relationship</th>
            <th>Review</th>
          </tr>
        </thead>
        <tbody>
          {pairs.map((pair, index) => (
            <tr key={pair.Pair_ID}>
              <td>{rankOffset + index + 1}</td>
              <td>{pair.Male}<span className="muted tiny">{pair.Male_Sheet ? ` · ${pair.Male_Sheet}` : ''}</span></td>
              <td>{pair.Female}<span className="muted tiny">{pair.Female_Sheet ? ` · ${pair.Female_Sheet}` : ''}</span></td>
              <td>{selectable
                ? pair.Probability === null || pair.Probability === undefined
                  ? `${pair.Ranking_Score?.toFixed(2) ?? '—'}%`
                  : `${pair.Probability.toFixed(2)}%`
                : pair.Similarity?.toFixed(2) ?? '—'}</td>
              <td>{Object.entries(pair.Locus_Probabilities ?? {}).map(([gene, value]) => <span className="pill soft" key={gene}>{gene}: {value.toFixed(1)}%</span>)}</td>
              <td>{pair.Relationship}{pair.Same_Strain ? ' · same strain' : ''}</td>
              <td>
                <div className="edit-actions">
                  {selectable && <button
                    type="button"
                    className={selectedPairId === pair.Pair_ID ? 'accent' : 'ghost'}
                    disabled={Boolean(lockedPairId)}
                    onClick={() => { setSelectedPairId(pair.Pair_ID); setSelectionReason(''); setError(null) }}
                  >{selectedPairId === pair.Pair_ID ? 'Selected' : 'Select'}</button>}
                  <button type="button" className="ghost" disabled={Boolean(lockedPairId)} onClick={() => excludePair(pair)}>Exclude</button>
                </div>
                {pair.Reasons?.map(reason => <p className="muted tiny" key={reason}>{reason}</p>)}
                {pair.Assumptions?.map(assumption => <p className="muted tiny" key={assumption}>{assumption}</p>)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  const handleAddGene = async (gene: string, geneClassValue: string) => {
    invalidateReview()
    const form = new FormData()
    form.append('gene', gene)
    form.append('gene_class', geneClassValue)
    await fetch(`${API_BASE}/genes/add`, { method: 'POST', body: form })
    loadGenes().catch(() => {})
  }

  const hasResults = Boolean(results)
  const statusLabel = loading ? 'Processing' : 'Ready'
  const statusClass = loading ? 'warning' : 'success'
  const geneCount = Object.values(genes).flat().length
  const tutorialSteps: TutorialStep[] = useMemo(
    () => [
      {
        selector: '[data-testid="breeding-use-example-toggle"]',
        title: 'Use example data toggle',
        description: 'Enable to load bundled breeders when testing workflow behavior.',
      },
      {
        selector: '[data-testid="breeders-upload-field"]',
        title: 'Upload breeder sheet',
        description: 'Upload CSV/XLSX breeder records to populate the candidate pool.',
      },
      {
        selector: '[data-testid="desired-genotype-input"]',
        title: 'Desired genotype',
        description: 'Enter target genotype using gene:allele or paired token format.',
        details: [
          'Example: cre +/- reporter +/+ flox1 f/+',
        ],
      },
      {
        selector: '[data-testid="min-probability-input"]',
        title: 'Min probability (%)',
        description: 'Filters direct-pair suggestions below this probability threshold.',
      },
      {
        selector: '[data-testid="gene-library-section"]',
        title: 'Gene library',
        description: 'Review detected genes or add custom gene/class entries.',
      },
      {
        selector: '[data-testid="process-btn"]',
        title: 'Find breeder pairs',
        description: 'Runs pairing against loaded breeders with current genotype constraints.',
      },
      {
        selector: '[data-testid="breeding-export-btn"]',
        title: 'Export Excel',
        description: 'Download pair recommendations for colony planning records.',
      },
      {
        selector: '[data-testid="breeding-results-panel"]',
        title: 'Review direct/indirect matches (final step)',
        description: 'Validate confidence and strain match before final selection.',
      },
    ],
    []
  )

  return (
    <div className="app-bg">
      <header className="panel">
        <div className="lab-head">
          <div>
            <p className="eyebrow">Breeder pairing</p>
            <h2>Mice Breeding Pair Selector</h2>
        <p className="muted">Confirm the inheritance assumptions, then rank eligible pairs for your target.</p>
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
            <button className="pill soft" onClick={() => { startNewTargetReview(); setExcludedPairs([]); setUseExample(true) }} type="button">
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
                  onChange={(e) => {
                    startNewTargetReview()
                    setExcludedPairs([])
                    setUseExample(e.target.checked)
                    if (!e.target.checked) setBreeders([])
                  }}
                  data-testid="breeding-use-example-toggle"
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
                  data-testid="breeders-upload-field"
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
                onChange={(e) => { startNewTargetReview(); setDesiredGenotypeText(e.target.value) }}
                placeholder="cre +/- reporter +/+ flox1 f/+"
                aria-label="Desired genotype"
                data-testid="desired-genotype-input"
              />
            </label>
            <div className="field-row">
              <button className="pill soft" onClick={() => { startNewTargetReview(); setDesiredGenotypeText('cre +/- reporter +/+') }} type="button">
                Example genotype
              </button>
              <label className="field">
                <span className="eyebrow">{confirmIndependentAssortment || Object.keys(parsedDesired).length === 1 ? 'Minimum probability (%)' : 'Minimum per-locus probability (%)'}</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={minProb}
                  onChange={(e) => { invalidateReview(); setMinProb(parseFloat(e.target.value) || 0) }}
                  data-testid="min-probability-input"
                />
              </label>
            </div>
            <div className="edit-actions">
              <label className="field checkbox-field">
                <input type="checkbox" checked={assumeMissingWildtype} onChange={event => { invalidateReview(); setAssumeMissingWildtype(event.target.checked) }} />
                <span>Assume blank gene values use the configured wild type</span>
              </label>
              <p className="muted tiny">Blank genotypes stay unresolved unless you confirm this. The gene library must define a wild type for each affected gene.</p>
              <label className="field checkbox-field">
                <input type="checkbox" checked={confirmSimpleInheritance} onChange={event => { invalidateReview(); setConfirmSimpleInheritance(event.target.checked) }} />
                <span>Use a simple two-allele inheritance model for each gene</span>
              </label>
              <p className="muted tiny">The probabilities assume one allele is passed from each parent at each gene. Confirm only when this model fits the cross.</p>
              <label className="field checkbox-field">
                <input type="checkbox" checked={confirmIndependentAssortment} disabled={Object.keys(parsedDesired).length < 2} onChange={event => { invalidateReview(); setConfirmIndependentAssortment(event.target.checked) }} />
                <span>Calculate a combined probability assuming loci assort independently</span>
              </label>
              <p className="muted tiny">For multiple genes, confirm independent assortment to combine per-locus probabilities. Otherwise pairs rank by their lowest per-locus probability.</p>
            </div>
          </div>

          <div className="sidebar-section">
            <div className="section-title">Parent review and exclusions</div>
            <label className="field checkbox-field">
              <input type="checkbox" checked={excludeSharedParent} onChange={event => { invalidateReview(); setExcludeSharedParent(event.target.checked) }} />
              <span>Exclude pairs with a known shared parent</span>
            </label>
            <label className="field checkbox-field">
              <input type="checkbox" checked={allowUnknownRelationship} onChange={event => { invalidateReview(); setAllowUnknownRelationship(event.target.checked) }} />
              <span>Allow pairs when parent IDs are incomplete</span>
            </label>
            <p className="muted tiny">Parent IDs are optional. If shared-parent screening is active, pairs with missing parent IDs need your explicit review.</p>
            {excludedPairs.length > 0 && <p className="muted tiny">Specific pair exclusions: {excludedPairs.length}</p>}
          </div>

          <div className="sidebar-section" data-testid="gene-library-section">
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
              <GuidedTutorial
                steps={tutorialSteps}
                startLabel="Tutorial"
              />
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
                <button onClick={handleExport} className="ghost" type="button" data-testid="breeding-export-btn">
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
                Convert to CSV with headers: breeder_id, breeder_name, gender, strain, sheet, sire_id, dam_id, cre, reporter, flox1, flox2, age. Include breeder IDs and parent IDs only when present in my source. Normalize gender to male/female, keep gene markers as typed, and leave unknown genotypes blank. Output CSV only.
              </pre>
            </div>
          </div>
        </aside>

        <section className="panel editor" data-testid="breeding-results-panel">
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
              {needsReviewPairs.length > 0 && <span className="pill soft">Needs review: {needsReviewPairs.length}</span>}
              {results && <span className="pill soft"><Search className="icon" aria-hidden="true" />{results.probability_method}</span>}
            </div>
          </div>

          <div className="editor-body">
            {hasResults && <div className="today-card">
              <h2>Review candidates</h2>
              <p className="muted tiny">Review each locus and parent record. Probabilities describe the stated genotype model, not a guaranteed litter outcome.</p>
              <p className="muted tiny">Blank genotype assumption: {results?.assumptions.missing_wildtype_confirmed ? 'confirmed where a gene-library wild type exists' : 'not confirmed'} · Inheritance model: {results?.assumptions.simple_inheritance_confirmed ? 'confirmed' : 'not confirmed'} · Independent assortment: {results?.assumptions.independent_assortment_confirmed ? 'confirmed for combined probability' : 'combined probability withheld'} · Shared-parent exclusion: {results?.assumptions.shared_parent_exclusion_enabled ? 'on' : 'off'}</p>
              <p className="muted tiny">Review saves automatically on this device. Change a target or assumption and calculate again before choosing a pair.</p>
            </div>}

            {selectedPair && <div className="today-card">
              <div className="today-head">
                <div>
                  <h2>{lockedPairId === selectedPair.Pair_ID ? 'Pair locked' : 'Selected pair'}</h2>
                  <p className="muted">{selectedPair.Male} × {selectedPair.Female}</p>
                </div>
                {lockedPairId === selectedPair.Pair_ID && <span className="pill">Locked for this review</span>}
              </div>
              <label className="field">
                <span className="eyebrow">Reason for this choice</span>
                <textarea value={selectionReason} onChange={event => setSelectionReason(event.target.value)} disabled={Boolean(lockedPairId)} placeholder="Required when choosing a different eligible pair" />
              </label>
              {lockedPairId ? <button className="ghost" type="button" onClick={() => setLockedPairId('')}>Unlock selection</button> : <button className="accent" type="button" onClick={lockSelectedPair}>Lock selected pair</button>}
            </div>}

            {directPairs.length > 0 && (
              <div className="today-card">
                <div className="today-head">
                  <div>
                    <h2>Pairs that can produce the target at each locus</h2>
                    <p className="muted tiny">Ranked by the confirmed combined probability or, when that assumption is not confirmed, the lowest per-locus probability.</p>
                  </div>
                </div>
                {renderCandidateTable(directPairs)}
              </div>
            )}

            {indirectPairs.length > 0 && (
              <div className="today-card" data-testid="indirect-results">
                <div className="today-head">
                  <div>
                    <h2>Pairs that cannot produce all target loci</h2>
                    <p className="muted tiny">Included for review and ranked by similarity only. A similarity score is not an offspring probability.</p>
                  </div>
                </div>
                {renderCandidateTable(indirectPairs, 0, false)}
              </div>
            )}

            {needsReviewPairs.length > 0 && <div className="today-card">
              <h2>Needs review before ranking</h2>
              {needsReviewPairs.map(pair => <p key={pair.Pair_ID}>{pair.Male} × {pair.Female}: {pair.Reasons?.join(' ')}</p>)}
            </div>}

            {excludedResults.length > 0 && <div className="today-card">
              <h2>Excluded pairs</h2>
              {excludedResults.map(pair => <p key={pair.Pair_ID}>{pair.Male} × {pair.Female}: {pair.Reasons?.join(' ')}</p>)}
            </div>}

            {(results?.below_threshold_pairs.length ?? 0) > 0 && <div className="today-card">
              <h2>Below your minimum score</h2>
              <p className="muted tiny">These pairs could produce the target genotype at each locus, but do not meet the selected minimum score.</p>
              {results?.below_threshold_pairs.map(pair => <p key={pair.Pair_ID}>{pair.Male} × {pair.Female}: {pair.Reasons?.join(' ')}</p>)}
            </div>}

            {excludedPairs.length > 0 && <div className="today-card">
              <h2>Specific exclusions</h2>
              {excludedPairs.map(ids => <p key={ids.join(':')}>{ids.join(' × ')}</p>)}
              {results?.excluded_pairs.filter(pair => excludedPairs.some(ids => (
                ids[0] === pair.Male_ID && ids[1] === pair.Female_ID
                || ids[0] === pair.Female_ID && ids[1] === pair.Male_ID
              ))).map(pair => <button key={pair.Pair_ID} className="ghost" type="button" onClick={() => removeExclusion(pair)}>Restore {pair.Male} × {pair.Female}</button>)}
            </div>}

            {results && directPairs.length === 0 && indirectPairs.length === 0 && needsReviewPairs.length === 0 && excludedResults.length === 0 && (
              <div className="empty">
                <p className="muted">No eligible pairs were found with these settings.</p>
              </div>
            )}

            {!results && <div className="empty"><p className="muted">Results will appear here after you review your assumptions and calculate pairings.</p></div>}

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
                        {previewColumns.map((key) => (
                          <th key={key}>{key}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {breeders.slice(0, 5).map((row, idx) => (
                        <tr key={idx}>
                          {previewColumns.map((key) => (
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

      <footer className="signature" data-testid="signature">
        <span className="sig-primary">Made by Meghamsh Teja Konda</span>
        <span className="sig-dot" aria-hidden="true" />
        <a className="sig-link" href="mailto:meghamshteja555@gmail.com">
          meghamshteja555@gmail.com
        </a>
      </footer>
    </div>
  )
}

export default App
