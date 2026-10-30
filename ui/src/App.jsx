import React, { useState, useEffect } from 'react'
import './App.css'

const STAGES = [
  { id: 'document_ingestor', label: 'Ingest Text' },
  { id: 'story_analyst', label: 'Story Analyst' },
  { id: 'director', label: 'Director' },
  { id: 'char_consistency', label: 'Consistency' },
  { id: 'scene_writer', label: 'Scene Writer' },
  { id: 'art_director', label: 'Art Director' },
  { id: 'image_generator', label: 'SDXL Images' },
  { id: 'video_animator', label: 'Veo 3.1 Fast' },
  { id: 'sound_designer', label: 'Sound Prompt' },
  { id: 'audio_generator', label: 'Audio & Music' },
  { id: 'subtitle_generator', label: 'Subtitles' },
  { id: 'editor', label: 'FFmpeg Assembly' }
]

export default function App() {
  const [textContent, setTextContent] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [estimating, setEstimating] = useState(false)
  const [currentRunId, setCurrentRunId] = useState('')
  const [jobStatus, setJobStatus] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')

  // Studio Access Token State
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem('studio_access_token') || '')
  const [savedTokenMsg, setSavedTokenMsg] = useState('')

  // GPU Endpoint Management State
  const [gpuStatus, setGpuStatus] = useState({ deployed: false, loading: true })
  const [undeploying, setUndeploying] = useState(false)

  // Cost Modal & Draft State
  const [showModal, setShowModal] = useState(false)
  const [draftData, setDraftData] = useState(null)

  // Fetch Endpoint GPU Status
  const fetchGpuStatus = async () => {
    try {
      const res = await fetch('/api/v1/endpoint/status')
      if (res.ok) {
        const data = await res.json()
        setGpuStatus({ ...data, loading: false })
      } else {
        setGpuStatus({ deployed: false, loading: false })
      }
    } catch (err) {
      console.warn('Failed to fetch GPU status:', err)
      setGpuStatus({ deployed: false, loading: false })
    }
  }

  useEffect(() => {
    fetchGpuStatus()
    const timer = setInterval(fetchGpuStatus, 30000)
    return () => clearInterval(timer)
  }, [])

  // Poll status when a video generation job is active
  useEffect(() => {
    if (!currentRunId) return

    const poll = async () => {
      try {
        const res = await fetch(`/api/v1/status/${currentRunId}`)
        if (res.ok) {
          const data = await res.json()
          setJobStatus(data)
          if (data.status === 'completed' || data.status === 'failed') {
            setLoading(false)
          }
        }
      } catch (err) {
        console.error('Error fetching job status:', err)
      }
    }

    poll()
    const timer = setInterval(poll, 3000)
    return () => clearInterval(timer)
  }, [currentRunId])

  // Handle GPU Undeploy
  const handleUndeploy = async () => {
    if (!window.confirm('Are you sure you want to undeploy the SDXL GPU endpoint? This stops the ~$0.85/hr billing immediately.')) {
      return
    }
    setUndeploying(true)
    try {
      const res = await fetch('/api/v1/endpoint/undeploy', {
        method: 'POST',
        headers: { 'X-Access-Token': accessToken },
      })
      const data = await res.json()
      if (res.ok) {
        alert(data.message || 'Undeploy initiated successfully.')
        await fetchGpuStatus()
      } else {
        alert(data.detail || 'Failed to undeploy endpoint.')
      }
    } catch (err) {
      alert(`Error during undeploy: ${err.message}`)
    } finally {
      setUndeploying(false)
    }
  }

  // Phase 1: Analyze & Estimate Cost
  const handleEstimate = async (e) => {
    e.preventDefault()
    setErrorMsg('')
    if (!accessToken.trim()) {
      setErrorMsg('🔐 Studio Access Token required: Please enter your access token in the bar above to unlock generation.')
      return
    }
    if (!selectedFile && !textContent.trim()) {
      setErrorMsg('Please upload a file or write a story excerpt.')
      return
    }

    setEstimating(true)
    const formData = new FormData()
    if (selectedFile) {
      formData.append('file', selectedFile)
    } else {
      formData.append('text_content', textContent)
    }

    try {
      const res = await fetch('/api/v1/estimate', {
        method: 'POST',
        headers: {
          'X-Access-Token': accessToken,
        },
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to analyze story & estimate cost.')
      }

      const data = await res.json()
      setDraftData(data)
      setShowModal(true)
    } catch (err) {
      setErrorMsg(err.message)
    } finally {
      setEstimating(false)
    }
  }

  // Phase 2: Confirm Cost & Start Generation
  const handleConfirmJob = async () => {
    if (!draftData) return
    setShowModal(false)
    setLoading(true)
    setErrorMsg('')

    try {
      const res = await fetch(`/api/v1/confirm/${draftData.draft_id}`, {
        method: 'POST',
        headers: {
          'X-Access-Token': accessToken,
        },
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to start video generation.')
      }

      const data = await res.json()
      setCurrentRunId(data.run_id)
      setJobStatus({
        status: 'queued',
        current_node: 'Starting',
        cost_breakdown: draftData.cost_breakdown,
      })
    } catch (err) {
      setErrorMsg(err.message)
      setLoading(false)
    }
  }

  const loadSampleStory = () => {
    setTextContent(`Once upon a time, at the edge of the Whispering Woods, lived a tiny firefly named Pip. While all the other fireflies flashed in bright neon yellow, Pip glowed with a gentle, starlit lavender.

The ancient forest had fallen into a deep, unending slumber under a heavy grey mist. The great Elder Oak had closed its leaves and sighed, "Unless the light of dawn touches each crown, the forest will sleep forever."

Pip carried a pocketful of moon-dew. Flying high into the branches, Pip touched the bough of the Elder Oak. Radiant lavender warmth spread outward, illuminating the silver moss and chasing away shadows.

One by one, the trees opened their emerald leaves, rejoicing as the sun broke through the canopy.`)
    setSelectedFile(null)
  }

  return (
    <div className="app-container">
      <header className="header">
        <h1>Animated Video Studio</h1>
        <p>Agentic Story-to-Animation Pipeline powered by LangGraph, Vertex AI SDXL, Veo 3.1 & Lyria 3</p>
      </header>

      {/* GPU Endpoint Status Bar */}
      <div className="gpu-bar">
        <div className="gpu-status-info">
          <span className={`gpu-indicator ${gpuStatus.deployed ? 'online' : 'offline'}`}></span>
          <span>
            <strong>SDXL Dedicated GPU (Vertex AI):</strong>{' '}
            {gpuStatus.loading ? (
              'Checking...'
            ) : gpuStatus.deployed ? (
              <span style={{ color: '#4ade80' }}>
                Online & Deployed (1x NVIDIA L4 ~$0.85/hr)
              </span>
            ) : (
              <span style={{ color: '#94a3b8' }}>
                Undeployed (Local Canvas fallback active, $0.00/hr)
              </span>
            )}
          </span>
        </div>

        {gpuStatus.deployed && (
          <button
            type="button"
            className="btn-undeploy"
            onClick={handleUndeploy}
            disabled={undeploying}
          >
            {undeploying ? 'Undeploying...' : 'Undeploy GPU (Stop Billing)'}
          </button>
        )}
      </div>

      {/* Studio Access Token Input Bar */}
      <div className="token-bar">
        <span className="token-label">🔐 Studio Access Token:</span>
        <input
          type="password"
          className="token-input"
          placeholder="Enter authorization token to unlock generation..."
          value={accessToken}
          onChange={(e) => {
            const val = e.target.value
            setAccessToken(val)
            localStorage.setItem('studio_access_token', val)
            setSavedTokenMsg('Token Saved')
            setTimeout(() => setSavedTokenMsg(''), 2500)
          }}
        />
        {savedTokenMsg && <span className="token-saved-tag">✓ {savedTokenMsg}</span>}
      </div>

      <div className="grid-layout">
        {/* Story Input Form */}
        <div className="card">
          <h2 className="card-title">📖 Story Input</h2>
          <form onSubmit={handleEstimate}>
            <div className="form-group">
              <label className="form-label">Write or Paste Story Text</label>
              <textarea
                className="textarea"
                placeholder="Type or paste your story here..."
                value={textContent}
                onChange={(e) => { setTextContent(e.target.value); setSelectedFile(null); }}
              />
            </div>

            <div style={{ textAlign: 'center', margin: '12px 0', color: 'var(--text-muted)' }}>- OR -</div>

            <div className="form-group">
              <label className="form-label">Upload Story Document (.txt, .pdf, .docx)</label>
              <div className="file-input-wrapper" onClick={() => document.getElementById('story-file').click()}>
                <input
                  id="story-file"
                  type="file"
                  accept=".txt,.pdf,.docx"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    if (e.target.files[0]) {
                      setSelectedFile(e.target.files[0])
                      setTextContent('')
                    }
                  }}
                />
                <div>{selectedFile ? `Selected: ${selectedFile.name}` : 'Click to select PDF, TXT or DOCX file'}</div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
              <button
                type="button"
                onClick={loadSampleStory}
                className="btn btn-secondary"
                disabled={estimating || loading}
              >
                Load Sample Story
              </button>
              <button
                type="submit"
                disabled={estimating || loading}
                className="btn btn-primary"
              >
                {estimating
                  ? 'Analyzing & Estimating Cost...'
                  : loading
                  ? 'Generating Video Pipeline...'
                  : 'Analyze & Estimate Cost'}
              </button>
            </div>

            {errorMsg && <div style={{ color: 'var(--danger)', marginTop: '12px', fontSize: '0.9rem' }}>{errorMsg}</div>}
          </form>
        </div>

        {/* Current Job Status & Video Player */}
        <div className="card">
          <h2 className="card-title">
            🎬 Generation Pipeline
            {jobStatus && (
              <span className={`badge badge-${jobStatus.status}`}>
                {jobStatus.status}
              </span>
            )}
          </h2>

          {!jobStatus ? (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px 0' }}>
              Submit a story on the left to analyze scenes and preview estimated generation cost.
            </div>
          ) : (
            <div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '8px' }}>
                Run ID: <code style={{ color: '#a5b4fc' }}>{jobStatus.run_id}</code>
              </div>

              {jobStatus.error && (
                <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--danger)', padding: '12px', borderRadius: '6px', color: '#fca5a5', marginTop: '10px', fontSize: '0.85rem' }}>
                  <strong>Error:</strong> {jobStatus.error}
                </div>
              )}

              <div className="stepper">
                {STAGES.map((s) => (
                  <span
                    key={s.id}
                    className={`step-pill ${jobStatus.current_node === s.id ? 'active' : ''}`}
                  >
                    {s.label}
                  </span>
                ))}
              </div>

              {jobStatus.final_video_url && (
                <div style={{ marginTop: '24px' }}>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '8px' }}>Final 1080p Animated Video</h3>
                  <video
                    controls
                    style={{ width: '100%', borderRadius: '8px', background: '#000', maxHeight: '280px' }}
                    src={jobStatus.final_video_url}
                  />
                  <a
                    href={`/api/v1/download/${jobStatus.run_id}`}
                    download
                    className="btn btn-primary"
                    style={{ marginTop: '12px', textDecoration: 'none' }}
                  >
                    Download MP4 (1080p)
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Storyboard and Generated Scene Assets */}
      {jobStatus && jobStatus.scenes && jobStatus.scenes.length > 0 && (
        <div className="card" style={{ marginTop: '24px' }}>
          <h2 className="card-title">🖼️ Scene Storyboard & Audio Clips</h2>
          <div className="scene-grid">
            {jobStatus.scenes.map((scene) => (
              <div key={scene.scene_id} className="scene-card">
                {scene.clip_url ? (
                  <video controls className="scene-media" src={scene.clip_url} />
                ) : scene.keyframe_url ? (
                  <img src={scene.keyframe_url} alt={scene.scene_id} className="scene-media" />
                ) : (
                  <div className="scene-media">Rendering scene...</div>
                )}
                <div className="scene-content">
                  <strong style={{ fontSize: '1rem', textTransform: 'capitalize' }}>
                    {scene.scene_id.replace('_', ' ')}
                  </strong>
                  {scene.music_url && (
                    <div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Background Music:</span>
                      <audio controls className="audio-player" src={scene.music_url} />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Cost Confirmation & Guardrail Modal */}
      {showModal && draftData && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Cost Estimation & Scene Plan</h3>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', fontSize: '1.5rem', cursor: 'pointer' }}
              >
                &times;
              </button>
            </div>

            <div>
              <p style={{ color: '#cbd5e1', fontSize: '0.95rem' }}>
                Director planned <strong>{draftData.cost_breakdown.total_scenes} scenes</strong> with a total target duration of{' '}
                <strong>{draftData.cost_breakdown.total_duration_sec} seconds</strong> (1080p MP4).
              </p>

              {/* Guardrail Warning Banners */}
              {draftData.cost_breakdown.is_hard_blocked ? (
                <div className="alert-banner danger">
                  🛑 <strong>Hard Budget Limit Exceeded ($7.00 USD)</strong>:
                  <div style={{ marginTop: '4px' }}>
                    This generation is calculated at ${draftData.cost_breakdown.total_estimated_cost_usd.toFixed(2)}, which exceeds your hard safety cap. Execution is blocked to protect your budget.
                  </div>
                </div>
              ) : draftData.cost_breakdown.is_soft_warned ? (
                <div className="alert-banner warning">
                  ⚠️ <strong>Advisory Soft Limit ($5.00 USD)</strong>:
                  <div style={{ marginTop: '4px' }}>
                    Total estimated cost (${draftData.cost_breakdown.total_estimated_cost_usd.toFixed(2)}) is above the soft warning threshold. Please review the breakdown before confirming.
                  </div>
                </div>
              ) : (
                <div className="alert-banner info">
                  ✅ <strong>Within Budget</strong>: Estimated generation cost is within your configured safety thresholds.
                </div>
              )}

              {/* Itemized Cost Breakdown Table */}
              <table className="cost-table">
                <thead>
                  <tr>
                    <th>Resource / Pipeline Stage</th>
                    <th style={{ textAlign: 'right' }}>Est. Cost (USD)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>
                      Veo 3.1 Fast Video ({draftData.cost_breakdown.total_duration_sec}s @ $0.10/s)
                    </td>
                    <td className="amount">${draftData.cost_breakdown.veo_video_cost_usd.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td>
                      Stable Diffusion XL Keyframes ({draftData.cost_breakdown.total_scenes} images @ $0.01)
                    </td>
                    <td className="amount">${draftData.cost_breakdown.sdxl_image_cost_usd.toFixed(2)}</td>
                  </tr>
                  <tr>
                    <td>Gemini 2.5 Flash (Story analysis, directing & scripting)</td>
                    <td className="amount">${draftData.cost_breakdown.gemini_llm_cost_usd.toFixed(3)}</td>
                  </tr>
                  <tr className="cost-total-row">
                    <td><strong>Total Estimated Cost</strong></td>
                    <td className="amount">${draftData.cost_breakdown.total_estimated_cost_usd.toFixed(2)}</td>
                  </tr>
                </tbody>
              </table>

              {/* Scene Plan Overview */}
              <div style={{ marginTop: '16px' }}>
                <strong style={{ fontSize: '0.9rem', color: '#94a3b8' }}>Planned Scene Breakdown:</strong>
                <div className="modal-scenes-list">
                  {draftData.scenes.map((s, idx) => (
                    <div key={s.scene_id || idx} className="modal-scene-item">
                      <span style={{ color: '#e2e8f0' }}>
                        <strong>{s.scene_id}:</strong> {s.title || s.story_excerpt?.slice(0, 45)}...
                      </span>
                      <span style={{ color: '#a5b4fc', whiteSpace: 'nowrap', marginLeft: '12px' }}>
                        {s.estimated_duration_sec || 6}s ({s.emotional_beat || 'narrative'})
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Modal Actions */}
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setShowModal(false)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleConfirmJob}
                  disabled={draftData.cost_breakdown.is_hard_blocked}
                >
                  {draftData.cost_breakdown.is_hard_blocked
                    ? 'Blocked by Hard Budget Limit ($7.00)'
                    : `Approve & Generate Video ($${draftData.cost_breakdown.total_estimated_cost_usd.toFixed(2)})`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
