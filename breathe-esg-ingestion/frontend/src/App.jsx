import React, { useState, useEffect, useRef } from 'react'
import { 
  Upload, Database, Shield, AlertTriangle, CheckCircle, XCircle, 
  Search, Filter, Edit2, Check, RefreshCw, BarChart2, Eye, Info, Clock,
  PlusCircle, Trash2
} from 'lucide-react'

// Backend API Base URL
const API_BASE = (import.meta.env.VITE_API_URL || '') + '/api'

export default function App() {
  // Tenant State
  const [organizations, setOrganizations] = useState([])
  const [activeOrg, setActiveOrg] = useState(1) // Default to Acme seeded ID
  
  // Dashboard & Records State
  const [summary, setSummary] = useState(null)
  const [records, setRecords] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [facilities, setFacilities] = useState([])
  
  // Filters
  const [scopeFilter, setScopeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sourceFilter, setSourceFilter] = useState('')
  const [facilityFilter, setFacilityFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  
  // Active UI views: 'ledger', 'upload', 'audit'
  const [activeView, setActiveView] = useState('ledger')
  
  // File upload state
  const [uploadSource, setUploadSource] = useState('SAP')
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadStatus, setUploadStatus] = useState(null) // { success, message, raw_source }
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef(null)
  
  // Modal editor state
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [editQty, setEditQty] = useState('')
  const [editFactor, setEditFactor] = useState('')
  const [editComments, setEditComments] = useState('')
  const [changeReason, setChangeReason] = useState('')
  const [editError, setEditError] = useState('')
  
  // Reload trigger
  const [reloadTrigger, setReloadTrigger] = useState(0)

  // New client creation state
  const [showNewOrgForm, setShowNewOrgForm] = useState(false)
  const [newOrgName, setNewOrgName] = useState('')
  const [isCreatingOrg, setIsCreatingOrg] = useState(false)

  // Clear data / delete environment confirmation dialogs
  const [showClearConfirm, setShowClearConfirm] = useState(false)
  const [isClearingData, setIsClearingData] = useState(false)
  const [showDeleteOrgConfirm, setShowDeleteOrgConfirm] = useState(false)
  const [isDeletingOrg, setIsDeletingOrg] = useState(false)

  // Fetch organizations (refetchable)
  const fetchOrganizations = () => {
    fetch(`${API_BASE}/organizations/`)
      .then(res => res.json())
      .then(data => {
        setOrganizations(data)
        if (data.length > 0) {
          // Keep current active if still exists, else first org
          const stillExists = data.find(o => o.id === activeOrg)
          if (!stillExists) {
            setActiveOrg(data[0].id)
          }
        } else {
          setActiveOrg(null)
        }
      })
      .catch(err => console.error("Error fetching organizations:", err))
  }

  // Initial load
  useEffect(() => {
    fetchOrganizations()
  }, [])

  // Fetch data on active tenant or reload trigger change
  useEffect(() => {
    if (!activeOrg) return

    // 1. Fetch dashboard summary
    fetch(`${API_BASE}/dashboard-summary/?org_id=${activeOrg}`)
      .then(res => res.json())
      .then(data => {
        if (!data.error) setSummary(data)
      })
      .catch(err => console.error("Error fetching summary:", err))

    // 2. Fetch facilities
    fetch(`${API_BASE}/facilities/?org_id=${activeOrg}`)
      .then(res => res.json())
      .then(data => {
        if (!data.error) setFacilities(data)
      })
      .catch(err => console.error("Error fetching facilities:", err))

    // 3. Fetch audit logs
    fetch(`${API_BASE}/audit-logs/?org_id=${activeOrg}`)
      .then(res => res.json())
      .then(data => {
        if (!data.error) setAuditLogs(data)
      })
      .catch(err => console.error("Error fetching audits:", err))
  }, [activeOrg, reloadTrigger])

  // Fetch records with active filters
  useEffect(() => {
    if (!activeOrg) return
    
    let url = `${API_BASE}/records/?org_id=${activeOrg}`
    if (scopeFilter) url += `&scope=${scopeFilter}`
    if (statusFilter) url += `&status=${statusFilter}`
    if (sourceFilter) url += `&source_type=${sourceFilter}`
    if (facilityFilter) url += `&facility_id=${facilityFilter}`
    if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`
    
    fetch(url)
      .then(res => res.json())
      .then(data => {
        if (!data.error) setRecords(data)
      })
      .catch(err => console.error("Error fetching records:", err))
  }, [activeOrg, scopeFilter, statusFilter, sourceFilter, facilityFilter, searchQuery, reloadTrigger])

  // Handle file ingestion
  const handleUploadSubmit = (e) => {
    e.preventDefault()
    if (uploadSource !== 'TRAVEL' && !uploadFile) {
      setUploadStatus({ success: false, message: "Please select a file to upload." })
      return
    }
    
    setIsUploading(true)
    setUploadStatus(null)
    
    const formData = new FormData()
    formData.append('organization_id', activeOrg)
    formData.append('source_type', uploadSource)
    
    if (uploadSource !== 'TRAVEL') {
      formData.append('file', uploadFile)
    } else {
      // Simulate Travel API Pull payload
      // In real deployment, this pulls from travel platform. Here we send mock JSON text.
      const simulatedConcurJSON = [
        {
          "trip_id": `TRIP-API-${Math.floor(Math.random() * 90000) + 10000}`,
          "employee_id": `EMP-VAL-${Math.floor(Math.random() * 800) + 100}`,
          "booking_date": new Date().toISOString().split('T')[0],
          "segments": [
            { "type": "flight", "origin": "SFO", "destination": "LHR", "cabin_class": "business", "distance_km": null },
            { "type": "hotel", "city": "London", "country": "GB", "room_nights": 3 },
            { "type": "ground", "transport_type": "taxi", "distance_km": 12.8, "spend_usd": 38.00 }
          ]
        },
        {
          "trip_id": `TRIP-API-${Math.floor(Math.random() * 90000) + 10000}`,
          "employee_id": `EMP-SUS-${Math.floor(Math.random() * 800) + 100}`,
          "booking_date": new Date().toISOString().split('T')[0],
          "segments": [
            { "type": "flight", "origin": "FRA", "destination": "XYZ", "cabin_class": "economy", "distance_km": null },
            { "type": "hotel", "city": "Frankfurt", "country": "DE", "room_nights": -2 },
            { "type": "ground", "transport_type": "car_rental", "distance_km": null, "spend_usd": null }
          ]
        }
      ]
      formData.append('raw_payload', JSON.stringify(simulatedConcurJSON))
    }
    
    fetch(`${API_BASE}/ingest/`, {
      method: 'POST',
      body: formData
    })
      .then(async res => {
        const data = await res.json()
        if (res.ok) {
          setUploadStatus({
            success: true,
            message: data.message,
            raw_source: data.raw_source,
            count: data.records_count
          })
          setUploadFile(null)
          if (fileInputRef.current) fileInputRef.current.value = ''
          setReloadTrigger(prev => prev + 1)
        } else {
          setUploadStatus({
            success: false,
            message: data.error || "Upload process failed."
          })
        }
      })
      .catch(err => {
        console.error("Upload error:", err)
        setUploadStatus({ success: false, message: "Network error during ingestion." })
      })
      .finally(() => {
        setIsUploading(false)
      })
  }

  // Open Edit Review Modal
  const openReviewModal = (record) => {
    setSelectedRecord(record)
    setEditQty(record.normalized_quantity)
    setEditFactor(record.emission_factor_value)
    setEditComments(record.comments || '')
    setChangeReason('')
    setEditError('')
  }

  // Submit edits
  const handleEditSubmit = (e) => {
    e.preventDefault()
    if (!changeReason.trim()) {
      setEditError("A change reason is required to log manual updates to the ledger.")
      return
    }
    
    fetch(`${API_BASE}/records/${selectedRecord.id}/`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken') // Django CSRF helper
      },
      body: JSON.stringify({
        normalized_quantity: editQty,
        emission_factor_value: editFactor,
        comments: editComments,
        change_reason: changeReason
      })
    })
      .then(async res => {
        const data = await res.json()
        if (res.ok) {
          setSelectedRecord(null)
          setReloadTrigger(prev => prev + 1)
        } else {
          setEditError(data.error || "Failed to update record.")
        }
      })
      .catch(err => {
        console.error("Edit error:", err)
        setEditError("Network error trying to edit record.")
      })
  }

  // Approve Record
  const handleApprove = (recordId) => {
    fetch(`${API_BASE}/records/${recordId}/approve/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })
      .then(async res => {
        if (res.ok) {
          if (selectedRecord && selectedRecord.id === recordId) {
            setSelectedRecord(null)
          }
          setReloadTrigger(prev => prev + 1)
        } else {
          const data = await res.json()
          alert(data.error || "Approval failed.")
        }
      })
      .catch(err => console.error("Approve error:", err))
  }

  // Reject Record
  const handleReject = (recordId) => {
    const reason = prompt("Enter rejection reason:")
    if (reason === null) return // cancelled
    if (!reason.trim()) {
      alert("A reason is required to reject.")
      return
    }
    
    fetch(`${API_BASE}/records/${recordId}/reject/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ change_reason: reason })
    })
      .then(async res => {
        if (res.ok) {
          if (selectedRecord && selectedRecord.id === recordId) {
            setSelectedRecord(null)
          }
          setReloadTrigger(prev => prev + 1)
        } else {
          const data = await res.json()
          alert(data.error || "Rejection failed.")
        }
      })
      .catch(err => console.error("Reject error:", err))
  }

  // Helper cookie read for Django CSRF
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // Create New Client Environment
  const handleCreateOrg = (e) => {
    e.preventDefault()
    if (!newOrgName.trim()) return
    setIsCreatingOrg(true)
    fetch(`${API_BASE}/organizations/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newOrgName.trim() })
    })
      .then(async res => {
        const data = await res.json()
        if (res.ok) {
          setNewOrgName('')
          setShowNewOrgForm(false)
          // Refresh org list and switch to new org
          fetchOrganizations()
          setActiveOrg(data.id)
        } else {
          alert(data.name ? data.name.join(', ') : 'Failed to create environment.')
        }
      })
      .catch(err => {
        console.error('Create org error:', err)
        alert('Network error creating environment.')
      })
      .finally(() => setIsCreatingOrg(false))
  }

  // Clear All Data for Active Environment
  const handleClearAllData = () => {
    setIsClearingData(true)
    fetch(`${API_BASE}/records/clear-all/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ org_id: activeOrg })
    })
      .then(async res => {
        if (res.ok) {
          setShowClearConfirm(false)
          setReloadTrigger(prev => prev + 1)
        } else {
          const data = await res.json()
          alert(data.error || 'Failed to clear data.')
        }
      })
      .catch(err => {
        console.error('Clear data error:', err)
        alert('Network error clearing data.')
      })
      .finally(() => setIsClearingData(false))
  }

  // Delete Entire Client Environment
  const handleDeleteOrg = () => {
    setIsDeletingOrg(true)
    fetch(`${API_BASE}/organizations/${activeOrg}/`, {
      method: 'DELETE'
    })
      .then(async res => {
        if (res.ok || res.status === 204) {
          setShowDeleteOrgConfirm(false)
          fetchOrganizations()
        } else {
          const data = await res.json().catch(() => ({}))
          alert(data.error || 'Failed to delete environment.')
        }
      })
      .catch(err => {
        console.error('Delete org error:', err)
        alert('Network error deleting environment.')
      })
      .finally(() => setIsDeletingOrg(false))
  }

  // Format Helper functions
  const formatNumber = (num, decimals = 2) => {
    if (num === null || num === undefined) return '0.00'
    return Number(num).toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    })
  }

  const getSourceIcon = (source) => {
    switch (source) {
      case 'SAP': return <Database className="text-emerald-400" size={16} />
      case 'UTILITY': return <RefreshCw className="text-blue-400" size={16} />
      case 'TRAVEL': return <Clock className="text-purple-400" size={16} />
      default: return <Database size={16} />
    }
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case 'APPROVED':
        return <span className="badge badge-approved"><CheckCircle size={12} /> Approved (Locked)</span>
      case 'REJECTED':
        return <span className="badge badge-rejected"><XCircle size={12} /> Rejected</span>
      case 'SUSPICIOUS':
        return <span className="badge badge-suspicious"><AlertTriangle size={12} /> Suspicious</span>
      case 'FAILED':
        return <span className="badge badge-failed"><AlertTriangle size={12} /> Failed Ingestion</span>
      default:
        return <span className="badge badge-pending"><Info size={12} /> Pending Analyst</span>
    }
  }

  const getScopeBadge = (scope) => {
    switch (scope) {
      case 1: return <span className="badge badge-scope1">Scope 1 (Direct)</span>
      case 2: return <span className="badge badge-scope2">Scope 2 (Indirect)</span>
      case 3: return <span className="badge badge-scope3">Scope 3 (Supply Chain)</span>
      default: return <span className="badge">Scope {scope}</span>
    }
  }

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="navbar">
        <div className="navbar-brand">
          <span style={{ fontSize: '1.75rem' }}>🌱</span>
          <span className="navbar-logo">Breathe ESG</span>
          <span style={{ fontSize: '0.8rem', opacity: 0.5, borderLeft: '1px solid rgba(255,255,255,0.15)', paddingLeft: '0.75rem', marginLeft: '0.25rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Data Ingestion Hub
          </span>
        </div>
        
        <div className="navbar-actions">
          <div className="form-group" style={{ flexDirection: 'row', alignItems: 'center', gap: '0.5rem' }}>
            <span className="form-label" style={{ margin: 0 }}>Client Environment:</span>
            <select 
              className="tenant-selector"
              value={activeOrg || ''}
              onChange={(e) => setActiveOrg(Number(e.target.value))}
            >
              {organizations.length === 0 && <option value="">No environments</option>}
              {organizations.map(org => (
                <option key={org.id} value={org.id}>{org.name}</option>
              ))}
            </select>
            
            {/* Create New Client Button */}
            <button
              className="btn btn-primary btn-sm"
              onClick={() => setShowNewOrgForm(!showNewOrgForm)}
              title="Create a new client environment"
              style={{ padding: '0.35rem 0.5rem', borderRadius: 'var(--radius-md)' }}
            >
              <PlusCircle size={16} />
            </button>
          </div>

          {/* Inline New Org Form */}
          {showNewOrgForm && (
            <form 
              onSubmit={handleCreateOrg}
              style={{ 
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                padding: '0.4rem 0.6rem',
                background: 'rgba(16,185,129,0.08)',
                border: '1px solid rgba(16,185,129,0.25)',
                borderRadius: 'var(--radius-md)',
                animation: 'fadeIn 0.2s ease'
              }}
            >
              <input
                type="text"
                className="form-input"
                placeholder="New client name..."
                value={newOrgName}
                onChange={(e) => setNewOrgName(e.target.value)}
                autoFocus
                style={{ 
                  fontSize: '0.8rem', padding: '0.3rem 0.6rem', 
                  width: '180px', margin: 0,
                  background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border-color)'
                }}
              />
              <button 
                type="submit" 
                className="btn btn-primary btn-sm"
                disabled={isCreatingOrg || !newOrgName.trim()}
                style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem', whiteSpace: 'nowrap' }}
              >
                {isCreatingOrg ? <RefreshCw className="animate-spin" size={12} /> : <CheckCircle size={12} />}
                {isCreatingOrg ? ' Creating...' : ' Create'}
              </button>
              <button 
                type="button" 
                className="btn btn-secondary btn-sm"
                onClick={() => { setShowNewOrgForm(false); setNewOrgName(''); }}
                style={{ padding: '0.3rem 0.5rem', fontSize: '0.8rem' }}
              >
                <XCircle size={12} />
              </button>
            </form>
          )}
        </div>
      </header>

      <main className="main-content">
        
        {/* KPI Row */}
        {summary && (
          <div className="stats-grid animate-fade">
            <div className="glass-card stat-card" style={{ borderLeft: '4px solid var(--color-primary)' }}>
              <div className="stat-label">Total Ingested Emissions</div>
              <div className="stat-value">{formatNumber(summary.total_emissions)} <span style={{ fontSize: '1rem', fontWeight: 400, color: 'var(--text-secondary)' }}>tCO2e</span></div>
              <div className="stat-sub">Across Scopes 1, 2, and 3</div>
            </div>
            
            <div className="glass-card stat-card" style={{ borderLeft: '4px solid var(--color-scope2)' }}>
              <div className="stat-label">Locked & Approved (Audit Ready)</div>
              <div className="stat-value text-emerald-400">{formatNumber(summary.approved_emissions)} <span style={{ fontSize: '1rem', fontWeight: 400, color: 'var(--text-secondary)' }}>tCO2e</span></div>
              <div className="stat-sub">({formatNumber(summary.total_emissions > 0 ? (summary.approved_emissions / summary.total_emissions) * 100 : 0, 1)}% of total emissions)</div>
            </div>
            
            <div className="glass-card stat-card" style={{ borderLeft: '4px solid var(--color-pending)' }}>
              <div className="stat-label">Review Actions Required</div>
              <div className="stat-value text-amber-400" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {summary.counts.pending + summary.counts.suspicious}
                {(summary.counts.suspicious > 0) && (
                  <AlertTriangle className="text-amber-500 animate-pulse" size={24} />
                )}
              </div>
              <div className="stat-sub">{summary.counts.pending} standard, {summary.counts.suspicious} flagged suspicious</div>
            </div>

            <div className="glass-card stat-card" style={{ borderLeft: '4px solid var(--color-rejected)' }}>
              <div className="stat-label">Ingestion Failures</div>
              <div className="stat-value text-red-400" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {summary.counts.failed}
                {summary.counts.failed > 0 && <AlertTriangle className="text-red-500" size={24} />}
              </div>
              <div className="stat-sub">Rows requiring syntax/unit reconciliation</div>
            </div>
          </div>
        )}

        {/* Charts & Analytics Panel (Pure SVG to prevent install hiccups) */}
        {summary && (
          <div className="split-layout animate-fade">
            {/* Historical Emissions Trend (Pro-rated representation) */}
            <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyBetween: 'space-between' }}>
                <h3 style={{ fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <BarChart2 size={18} className="text-emerald-400" /> Ingested Monthly Footprint Trend (Daily Allocations)
                </h3>
              </div>
              
              <div style={{ height: '200px', display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', padding: '1rem 0.5rem 0', borderBottom: '1px solid var(--border-color)', borderLeft: '1px solid var(--border-color)', position: 'relative' }}>
                {summary.monthly_trend.length === 0 ? (
                  <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                    No valid monthly trend data found. Please ingest records first.
                  </div>
                ) : (
                  summary.monthly_trend.map((t, idx) => {
                    const maxVal = Math.max(...summary.monthly_trend.map(m => Number(m.emissions)), 1)
                    const heightPercent = (Number(t.emissions) / maxVal) * 80 + 5 // min 5% height
                    
                    return (
                      <div key={idx} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                          {formatNumber(t.emissions, 0)}t
                        </span>
                        <div 
                          className="animate-slide"
                          style={{ 
                            width: '45px', 
                            height: `${heightPercent}%`, 
                            background: 'linear-gradient(to top, rgba(16, 185, 129, 0.2), var(--color-primary))', 
                            borderRadius: '4px 4px 0 0',
                            border: '1px solid rgba(16, 185, 129, 0.4)',
                            boxShadow: '0 0 10px rgba(16, 185, 129, 0.15)',
                            transition: 'height var(--transition-normal)'
                          }}
                        />
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', paddingBottom: '0.25rem', whiteSpace: 'nowrap' }}>
                          {t.month}
                        </span>
                      </div>
                    )
                  })
                )}
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
                💡 <b>Note:</b> Utility bills are parsed and split daily. Their footprint is dynamically allocated across calendar months.
              </p>
            </div>

            {/* Scope Divisions and Facility Breakdown */}
            <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <h3 style={{ fontSize: '1.1rem' }}>Data Normalization Breakdown</h3>
              
              {/* Scopes Stack bar */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                  <span>Scope Category Aggregates (tCO2e)</span>
                </div>
                
                <div style={{ display: 'flex', gap: '0.25rem', height: '14px', borderRadius: '9999px', overflow: 'hidden', backgroundColor: 'rgba(255,255,255,0.05)' }}>
                  {Object.entries(summary.scopes).map(([scopeLabel, val], idx) => {
                    const totalVal = Object.values(summary.scopes).reduce((a, b) => Number(a) + Number(b), 0)
                    const percent = totalVal > 0 ? (Number(val) / totalVal) * 100 : 0
                    
                    let bg = 'var(--color-primary)'
                    if (scopeLabel.includes('2')) bg = 'var(--color-scope2)'
                    if (scopeLabel.includes('3')) bg = 'var(--color-scope3)'
                    
                    return (
                      <div 
                        key={idx} 
                        style={{ width: `${percent}%`, backgroundColor: bg, height: '100%' }}
                        title={`${scopeLabel}: ${formatNumber(val)} tCO2e (${formatNumber(percent, 1)}%)`}
                      />
                    )
                  })}
                </div>
                
                <div style={{ display: 'flex', gap: '1rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
                  {Object.entries(summary.scopes).map(([scopeLabel, val], idx) => {
                    let indicator = 'var(--color-primary)'
                    if (scopeLabel.includes('2')) indicator = 'var(--color-scope2)'
                    if (scopeLabel.includes('3')) indicator = 'var(--color-scope3)'
                    
                    return (
                      <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem' }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: indicator }} />
                        <span style={{ color: 'var(--text-secondary)' }}>{scopeLabel}:</span>
                        <span style={{ fontWeight: 600 }}>{formatNumber(val, 1)} t</span>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Facility distribution */}
              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1rem' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 500, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                  Top Emission Assets / Facility Codes:
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {summary.facilities.slice(0, 3).map((fac, idx) => {
                    const maxVal = summary.facilities[0] ? Number(summary.facilities[0].emissions) : 1
                    const widthPercent = maxVal > 0 ? (Number(fac.emissions) / maxVal) * 100 : 0
                    
                    return (
                      <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                          <span>{fac.name}</span>
                          <span style={{ fontWeight: 600 }}>{formatNumber(fac.emissions, 2)} tCO2e</span>
                        </div>
                        <div style={{ height: '6px', borderRadius: '9999px', backgroundColor: 'rgba(255,255,255,0.05)', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${widthPercent}%`, backgroundColor: 'var(--color-scope2)' }} />
                        </div>
                      </div>
                    )
                  })}
                  {summary.facilities.length === 0 && (
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No facility carbon metrics mapped.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* View Selection Navigation */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.25rem' }}>
          <div className="tabs-container" style={{ border: 0, margin: 0 }}>
            <button 
              className={`tab-btn ${activeView === 'ledger' ? 'active' : ''}`}
              onClick={() => setActiveView('ledger')}
            >
              <Database size={16} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} />
              Ingested Activity Ledger
            </button>
            <button 
              className={`tab-btn ${activeView === 'upload' ? 'active' : ''}`}
              onClick={() => setActiveView('upload')}
            >
              <Upload size={16} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} />
              Data Source Upload Ingest
            </button>
            <button 
              className={`tab-btn ${activeView === 'audit' ? 'active' : ''}`}
              onClick={() => setActiveView('audit')}
            >
              <Shield size={16} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} />
              System Audit Trails
            </button>
          </div>
          
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button 
              className="btn btn-secondary btn-sm" 
              onClick={() => setReloadTrigger(p => p + 1)}
              title="Refresh Ingested Data"
            >
              <RefreshCw size={14} /> Refresh Data
            </button>
            
            <button 
              className="btn btn-sm" 
              onClick={() => setShowClearConfirm(true)}
              title="Clear all ingested records, sources, and audit logs for this client"
              style={{ 
                background: 'rgba(245,158,11,0.1)', 
                border: '1px solid rgba(245,158,11,0.3)', 
                color: '#f59e0b',
                cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: '0.35rem',
                padding: '0.35rem 0.6rem', borderRadius: 'var(--radius-md)',
                fontSize: '0.8rem', fontWeight: 500
              }}
            >
              <Trash2 size={13} /> Clear Data
            </button>

            <button 
              className="btn btn-sm" 
              onClick={() => setShowDeleteOrgConfirm(true)}
              title="Permanently delete this client environment"
              disabled={organizations.length <= 1}
              style={{ 
                background: 'rgba(239,68,68,0.1)', 
                border: '1px solid rgba(239,68,68,0.3)', 
                color: organizations.length <= 1 ? 'rgba(239,68,68,0.3)' : '#ef4444',
                cursor: organizations.length <= 1 ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', gap: '0.35rem',
                padding: '0.35rem 0.6rem', borderRadius: 'var(--radius-md)',
                fontSize: '0.8rem', fontWeight: 500
              }}
            >
              <Trash2 size={13} /> Delete Environment
            </button>
          </div>
        </div>

        {/* VIEW 1: ACTIVITY LEDGER */}
        {activeView === 'ledger' && (
          <div className="animate-fade" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            
            {/* Filter Bar */}
            <div className="filter-bar">
              <div className="form-group" style={{ minWidth: '150px' }}>
                <span className="form-label">Scope</span>
                <select 
                  className="tenant-selector" 
                  value={scopeFilter} 
                  onChange={(e) => setScopeFilter(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="">All Scopes</option>
                  <option value="1">Scope 1</option>
                  <option value="2">Scope 2</option>
                  <option value="3">Scope 3</option>
                </select>
              </div>

              <div className="form-group" style={{ minWidth: '150px' }}>
                <span className="form-label">Status</span>
                <select 
                  className="tenant-selector" 
                  value={statusFilter} 
                  onChange={(e) => setStatusFilter(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="">All States</option>
                  <option value="PENDING_REVIEW">Pending Review</option>
                  <option value="APPROVED">Approved (Locked)</option>
                  <option value="REJECTED">Rejected</option>
                  <option value="SUSPICIOUS">Suspicious Anomalies</option>
                  <option value="FAILED">Failed Ingestion</option>
                </select>
              </div>

              <div className="form-group" style={{ minWidth: '150px' }}>
                <span className="form-label">Ingestion Source</span>
                <select 
                  className="tenant-selector" 
                  value={sourceFilter} 
                  onChange={(e) => setSourceFilter(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="">All Sources</option>
                  <option value="SAP">SAP ERP (Fuel & Spend)</option>
                  <option value="UTILITY">Utility Portal (Electricity)</option>
                  <option value="TRAVEL">Corporate Travel (Concur API)</option>
                </select>
              </div>

              <div className="form-group" style={{ minWidth: '180px' }}>
                <span className="form-label">Facility Filter</span>
                <select 
                  className="tenant-selector" 
                  value={facilityFilter} 
                  onChange={(e) => setFacilityFilter(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="">All Facilities</option>
                  {facilities.map(f => (
                    <option key={f.id} value={f.id}>{f.name} ({f.facility_code})</option>
                  ))}
                </select>
              </div>

              <div className="form-group" style={{ flex: 1, minWidth: '220px' }}>
                <span className="form-label">Search Context</span>
                <div style={{ position: 'relative' }}>
                  <Search size={16} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', opacity: 0.4 }} />
                  <input 
                    type="text" 
                    placeholder="Search category, anomalies, details..." 
                    className="form-input" 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    style={{ width: '100%', paddingLeft: '2.25rem' }}
                  />
                </div>
              </div>
            </div>

            {/* Ingested Table */}
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Scope</th>
                    <th>Source</th>
                    <th>Activity Detail</th>
                    <th>Asset Location</th>
                    <th>Original Data</th>
                    <th>Normalized Ingestion</th>
                    <th>Footprint</th>
                    <th>Status</th>
                    <th>Audit Action</th>
                  </tr>
                </thead>
                <tbody>
                  {records.length === 0 ? (
                    <tr>
                      <td colSpan="10" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                        No records match the current filter state.
                      </td>
                    </tr>
                  ) : (
                    records.map(rec => {
                      const isSusp = rec.status === 'SUSPICIOUS';
                      const isFail = rec.status === 'FAILED';
                      
                      return (
                        <tr 
                          key={rec.id} 
                          className={`${isSusp ? 'row-suspicious' : ''} ${isFail ? 'row-failed' : ''}`}
                        >
                          <td style={{ whiteSpace: 'nowrap' }}>{rec.activity_date}</td>
                          <td>{getScopeBadge(rec.scope)}</td>
                          <td style={{ whiteSpace: 'nowrap' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                              {getSourceIcon(rec.raw_source_details.source_type)}
                              <span>{rec.raw_source_details.source_type}</span>
                            </div>
                          </td>
                          <td>
                            <div style={{ fontWeight: 600 }}>{rec.category}</div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{rec.activity_type}</div>
                            {rec.comments && (
                              <div style={{ fontSize: '0.75rem', fontStyle: 'italic', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                                "{rec.comments}"
                              </div>
                            )}
                          </td>
                          <td>
                            {rec.facility_details ? (
                              <div>
                                <div>{rec.facility_details.name}</div>
                                <span style={{ fontSize: '0.75rem', opacity: 0.5, textTransform: 'uppercase' }}>
                                  Code: {rec.facility_details.facility_code} ({rec.facility_details.location})
                                </span>
                              </div>
                            ) : (
                              <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>-</span>
                            )}
                          </td>
                          <td style={{ whiteSpace: 'nowrap' }}>
                            <div>{formatNumber(rec.original_quantity)}</div>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{rec.original_unit}</span>
                          </td>
                          <td style={{ whiteSpace: 'nowrap' }}>
                            <div>{formatNumber(rec.normalized_quantity)}</div>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{rec.normalized_unit}</span>
                          </td>
                          <td style={{ whiteSpace: 'nowrap', fontWeight: 700 }}>
                            {formatNumber(rec.emissions_tco2e, 4)} t
                          </td>
                          <td>{getStatusBadge(rec.status)}</td>
                          <td style={{ whiteSpace: 'nowrap' }}>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                              <button 
                                className="btn btn-secondary btn-sm"
                                onClick={() => openReviewModal(rec)}
                                title={rec.is_locked ? "View raw payload details (Locked)" : "Edit and adjust normalized values"}
                              >
                                {rec.is_locked ? <Eye size={14} /> : <Edit2 size={14} />} 
                                {rec.is_locked ? "View" : "Review"}
                              </button>
                              
                              {!rec.is_locked && rec.status !== 'FAILED' && (
                                <button 
                                  className="btn btn-primary btn-sm"
                                  onClick={() => handleApprove(rec.id)}
                                  title="Sign off and Lock for audit"
                                >
                                  <Check size={14} /> Approve
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* VIEW 2: UPLOAD & INGEST */}
        {activeView === 'upload' && (
          <div className="animate-fade" style={{ maxWidth: '650px', margin: '0 auto', width: '100%', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <h3 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Upload className="text-emerald-400" /> File Upload & Mock API Ingestion Portal
              </h3>
              
              <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                Select an enterprise source data category. You can upload custom formatted text/CSV files, or simulate live REST API data pulls from travel platforms.
              </p>

              <form onSubmit={handleUploadSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                
                {/* Source Selection */}
                <div className="form-group">
                  <span className="form-label">Data Stream Category</span>
                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <label 
                      style={{ 
                        flex: 1, 
                        minWidth: '150px', 
                        padding: '1rem', 
                        borderRadius: 'var(--radius-md)', 
                        border: '1px solid',
                        borderColor: uploadSource === 'SAP' ? 'var(--color-primary)' : 'var(--border-color)',
                        backgroundColor: uploadSource === 'SAP' ? 'var(--color-primary-glow)' : 'transparent',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '0.5rem',
                        transition: 'all var(--transition-fast)'
                      }}
                    >
                      <input 
                        type="radio" 
                        name="source" 
                        value="SAP" 
                        checked={uploadSource === 'SAP'} 
                        onChange={() => { setUploadSource('SAP'); setUploadFile(null); setUploadStatus(null); }}
                        style={{ display: 'none' }}
                      />
                      <span style={{ fontWeight: 600 }}>SAP ERP</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textAlign: 'center' }}>Fuel & General Procurement</span>
                    </label>

                    <label 
                      style={{ 
                        flex: 1, 
                        minWidth: '150px', 
                        padding: '1rem', 
                        borderRadius: 'var(--radius-md)', 
                        border: '1px solid',
                        borderColor: uploadSource === 'UTILITY' ? 'var(--color-scope2)' : 'var(--border-color)',
                        backgroundColor: uploadSource === 'UTILITY' ? 'var(--color-scope2-glow)' : 'transparent',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '0.5rem',
                        transition: 'all var(--transition-fast)'
                      }}
                    >
                      <input 
                        type="radio" 
                        name="source" 
                        value="UTILITY" 
                        checked={uploadSource === 'UTILITY'} 
                        onChange={() => { setUploadSource('UTILITY'); setUploadFile(null); setUploadStatus(null); }}
                        style={{ display: 'none' }}
                      />
                      <span style={{ fontWeight: 600 }}>Utility Portals</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textAlign: 'center' }}>Electric Smart Meters (CSV)</span>
                    </label>

                    <label 
                      style={{ 
                        flex: 1, 
                        minWidth: '150px', 
                        padding: '1rem', 
                        borderRadius: 'var(--radius-md)', 
                        border: '1px solid',
                        borderColor: uploadSource === 'TRAVEL' ? 'var(--color-scope3)' : 'var(--border-color)',
                        backgroundColor: uploadSource === 'TRAVEL' ? 'var(--color-scope3-glow)' : 'transparent',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '0.5rem',
                        transition: 'all var(--transition-fast)'
                      }}
                    >
                      <input 
                        type="radio" 
                        name="source" 
                        value="TRAVEL" 
                        checked={uploadSource === 'TRAVEL'} 
                        onChange={() => { setUploadSource('TRAVEL'); setUploadFile(null); setUploadStatus(null); }}
                        style={{ display: 'none' }}
                      />
                      <span style={{ fontWeight: 600 }}>Concur API</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textAlign: 'center' }}>Simulated JSON Expense Pull</span>
                    </label>
                  </div>
                </div>

                {/* File picker vs API button */}
                {uploadSource !== 'TRAVEL' ? (
                  <div className="form-group">
                    <span className="form-label">Data File (TXT/CSV)</span>
                    <div 
                      className="uploader-box"
                      onClick={() => fileInputRef.current && fileInputRef.current.click()}
                    >
                      <Upload size={32} className="text-secondary" />
                      <div>
                        {uploadFile ? (
                          <div style={{ color: 'var(--color-primary)', fontWeight: 600 }}>{uploadFile.name}</div>
                        ) : (
                          <>
                            <div style={{ fontWeight: 500 }}>Click to browse computer files</div>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              Select files from sample_data/ folder (e.g. sap_export_raw.txt)
                            </span>
                          </>
                        )}
                      </div>
                      <input 
                        type="file" 
                        ref={fileInputRef}
                        style={{ display: 'none' }} 
                        onChange={(e) => {
                          if (e.target.files.length > 0) {
                            setUploadFile(e.target.files[0])
                            setUploadStatus(null)
                          }
                        }}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="glass-card" style={{ backgroundColor: 'rgba(0,0,0,0.15)', borderStyle: 'dashed', textAlign: 'center', padding: '2rem' }}>
                    <Database size={32} className="text-purple-400" style={{ marginBottom: '0.5rem' }} />
                    <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Simulated Corporate Travel Platform Pull</div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', maxWidth: '400px', margin: '0 auto 1rem' }}>
                      Click the button below to issue a mock pull command to the Navan/Concur API. This downloads flights, lodging, and ground taxi JSON records.
                    </p>
                  </div>
                )}

                {/* Status indicators */}
                {uploadStatus && (
                  <div className={`suspicious-alert ${uploadStatus.success ? 'text-emerald-400' : 'text-red-400'}`} style={{ backgroundColor: uploadStatus.success ? 'rgba(16, 185, 129, 0.06)' : 'rgba(239, 68, 68, 0.06)', borderColor: uploadStatus.success ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
                      {uploadStatus.success ? <CheckCircle size={16} /> : <XCircle size={16} />}
                      {uploadStatus.success ? "Ingestion Completed Successfully" : "Ingestion Failed"}
                    </div>
                    <div style={{ fontSize: '0.8rem', marginTop: '0.25rem', color: 'var(--text-secondary)' }}>
                      {uploadStatus.message}
                    </div>
                    {uploadStatus.success && uploadStatus.raw_source && (
                      <div style={{ fontSize: '0.75rem', marginTop: '0.5rem', color: 'var(--text-muted)', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.5rem' }}>
                        <div>Source ID: #{uploadStatus.raw_source.id}</div>
                        <div>Log: {uploadStatus.raw_source.processing_logs}</div>
                      </div>
                    )}
                  </div>
                )}

                {/* Ingest submit */}
                <button 
                  type="submit" 
                  className="btn btn-primary"
                  disabled={isUploading}
                  style={{ justifyContent: 'center', padding: '0.75rem' }}
                >
                  {isUploading ? (
                    <>
                      <RefreshCw className="animate-spin" size={16} /> Processing Data Pipeline...
                    </>
                  ) : (
                    <>
                      <CheckCircle size={16} /> {uploadSource === 'TRAVEL' ? 'Simulate API Data Fetch' : 'Ingest and Normalize File'}
                    </>
                  )}
                </button>

              </form>
            </div>
          </div>
        )}

        {/* VIEW 3: SYSTEM AUDIT LOG */}
        {activeView === 'audit' && (
          <div className="animate-fade" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <h3 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Shield className="text-emerald-400" /> Database Ledger Transaction Logs (SOX Compliance Audit Trail)
            </h3>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              Below is the comprehensive, immutable audit ledger. It catalogs system loads, manual analyst corrections, adjustments, and review approvals.
            </p>

            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Action</th>
                    <th>Activity Record Ref</th>
                    <th>Analyst</th>
                    <th>Field Adjustments (Old → New)</th>
                    <th>Reason / Justification</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.length === 0 ? (
                    <tr>
                      <td colSpan="6" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                        No audit ledger transactions recorded yet.
                      </td>
                    </tr>
                  ) : (
                    auditLogs.map(log => {
                      const hasOld = log.old_values && Object.keys(log.old_values).length > 0;
                      return (
                        <tr key={log.id}>
                          <td style={{ whiteSpace: 'nowrap' }}>
                            {new Date(log.timestamp).toLocaleString()}
                          </td>
                          <td style={{ whiteSpace: 'nowrap' }}>
                            <span 
                              className={`badge`}
                              style={{ 
                                backgroundColor: log.action === 'APPROVE' ? 'rgba(16,185,129,0.1)' : log.action === 'EDIT' ? 'rgba(59,130,246,0.1)' : 'rgba(255,255,255,0.05)',
                                color: log.action === 'APPROVE' ? '#34d399' : log.action === 'EDIT' ? '#60a5fa' : 'inherit',
                                border: '1px solid rgba(255,255,255,0.1)'
                              }}
                            >
                              {log.action}
                            </span>
                          </td>
                          <td>
                            <div style={{ fontWeight: 600 }}>{log.record_label}</div>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Record ID: #{log.record}</span>
                          </td>
                          <td style={{ whiteSpace: 'nowrap' }}>
                            {log.user_name || <span style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>System Parser</span>}
                          </td>
                          <td>
                            {hasOld ? (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.8rem' }}>
                                {Object.keys(log.old_values).map((k) => (
                                  <div key={k} style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                    <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>{k}:</span>
                                    <span style={{ textDecoration: 'line-through', color: '#f87171' }}>{log.old_values[k]}</span>
                                    <span style={{ color: 'var(--text-secondary)' }}>→</span>
                                    <span style={{ color: '#34d399', fontWeight: 600 }}>{log.new_values[k]}</span>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                                Row initialized with original parsing parameters.
                              </span>
                            )}
                          </td>
                          <td style={{ fontSize: '0.85rem' }}>
                            {log.change_reason ? (
                              <span style={{ fontStyle: 'italic' }}>"{log.change_reason}"</span>
                            ) : (
                              <span style={{ color: 'var(--text-muted)' }}>-</span>
                            )}
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </main>

      {/* REVIEW & LOCK DETAILS MODAL */}
      {selectedRecord && (
        <div className="modal-overlay">
          <div className="modal-content animate-slide">
            
            <div className="modal-header">
              <div>
                <h3 style={{ fontSize: '1.25rem' }}>
                  {selectedRecord.is_locked ? "Audit Signed Record Viewer" : "Audit Sign-off & Adjustments"}
                </h3>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Record ID: #{selectedRecord.id} | Ingested: {new Date(selectedRecord.raw_source_details.ingested_at).toLocaleDateString()}
                </span>
              </div>
              <button 
                style={{ background: 'none', border: 0, fontSize: '1.5rem', cursor: 'pointer', opacity: 0.5 }}
                onClick={() => setSelectedRecord(null)}
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleEditSubmit}>
              <div className="modal-body">
                
                {/* Warning Flags */}
                {selectedRecord.anomalies && (
                  <div className={selectedRecord.status === 'FAILED' ? 'anomaly-alert' : 'suspicious-alert'}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
                      <AlertTriangle size={16} />
                      Parser Validation Warning Flagged
                    </div>
                    <div>{selectedRecord.anomalies}</div>
                  </div>
                )}

                <div className="split-layout">
                  {/* LEFT PANE: SOURCE OF TRUTH REFERENCE */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', borderRight: '1px solid var(--border-color)', paddingRight: '1.5rem' }}>
                    <h4 style={{ fontSize: '1rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Database size={16} /> Original Ingestion Traceability
                    </h4>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.9rem' }}>
                      <div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Ingestion Source Stream</div>
                        <div style={{ fontWeight: 500 }}>{selectedRecord.raw_source_details.source_type} ({selectedRecord.raw_source_details.filename})</div>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                        <div>
                          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Parsed Date</div>
                          <div style={{ fontWeight: 500 }}>{selectedRecord.activity_date}</div>
                        </div>
                        <div>
                          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Mapped Scope</div>
                          <div>{getScopeBadge(selectedRecord.scope)}</div>
                        </div>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                        <div>
                          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Raw Client Quantity</div>
                          <div style={{ fontWeight: 500 }}>{formatNumber(selectedRecord.original_quantity)} {selectedRecord.original_unit}</div>
                        </div>
                        <div>
                          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Computed Emissions</div>
                          <div style={{ fontWeight: 700, color: 'var(--color-primary)' }}>{formatNumber(selectedRecord.emissions_tco2e, 4)} tCO2e</div>
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Raw Record Line (Source of Truth):</div>
                      <div className="payload-viewer">
                        {selectedRecord.raw_source_details.raw_payload}
                      </div>
                    </div>
                  </div>

                  {/* RIGHT PANE: NORMALIZATION ADJUSTER */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <h4 style={{ fontSize: '1rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <Edit2 size={16} /> Normalization Adjustment
                    </h4>

                    {selectedRecord.is_locked ? (
                      <div className="suspicious-alert" style={{ backgroundColor: 'rgba(255,255,255,0.03)', borderColor: 'var(--border-color)', color: 'var(--text-secondary)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
                          <CheckCircle size={16} className="text-emerald-400" />
                          Auditor Record Locked
                        </div>
                        <p style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
                          This record has been signed off and locked by <b>{selectedRecord.reviewed_by_name || 'Analyst'}</b> on {new Date(selectedRecord.reviewed_at).toLocaleDateString()}. Manual adjustments are disabled for compliance preservation.
                        </p>
                      </div>
                    ) : (
                      <>
                        <div className="form-group">
                          <label className="form-label">Normalized Quantity ({selectedRecord.normalized_unit})</label>
                          <input 
                            type="number" 
                            step="any"
                            className="form-input"
                            value={editQty}
                            onChange={(e) => setEditQty(e.target.value)}
                            required
                          />
                        </div>

                        <div className="form-group">
                          <label className="form-label">Emission Factor Value (tCO2e / {selectedRecord.normalized_unit})</label>
                          <input 
                            type="number" 
                            step="any"
                            className="form-input"
                            value={editFactor}
                            onChange={(e) => setEditFactor(e.target.value)}
                            required
                          />
                        </div>

                        <div className="form-group">
                          <label className="form-label">Analyst Audit Description / Notes</label>
                          <textarea 
                            className="form-input form-textarea"
                            value={editComments}
                            onChange={(e) => setEditComments(e.target.value)}
                            placeholder="Provide details about normalization adjustments (e.g. density conversion mismatch)..."
                          />
                        </div>

                        <div className="form-group" style={{ borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
                          <label className="form-label" style={{ color: 'var(--color-pending)', fontWeight: 600 }}>
                            Reason for Manual Change (Logged to Audit Trail) *
                          </label>
                          <input 
                            type="text" 
                            className="form-input"
                            value={changeReason}
                            onChange={(e) => setChangeReason(e.target.value)}
                            placeholder="e.g. Corrected Plant Code mapping/reconciled wrong unit of measure"
                            style={{ borderColor: 'rgba(245, 158, 11, 0.4)' }}
                          />
                        </div>

                        {editError && (
                          <div style={{ color: '#ef4444', fontSize: '0.85rem', fontWeight: 500 }}>
                            ⚠️ {editError}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>

              </div>
              
              <div className="modal-footer">
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  onClick={() => setSelectedRecord(null)}
                >
                  Close
                </button>
                
                {!selectedRecord.is_locked && (
                  <>
                    <button 
                      type="button" 
                      className="btn btn-danger" 
                      onClick={() => handleReject(selectedRecord.id)}
                    >
                      Reject Record
                    </button>
                    
                    <button 
                      type="submit" 
                      className="btn btn-secondary"
                      style={{ color: 'var(--color-scope2)', borderColor: 'rgba(59, 130, 246, 0.4)' }}
                    >
                      Save Adjustments
                    </button>
                    
                    {selectedRecord.status !== 'FAILED' && (
                      <button 
                        type="button" 
                        className="btn btn-primary"
                        onClick={() => handleApprove(selectedRecord.id)}
                      >
                        <Check size={16} /> Approve & Lock
                      </button>
                    )}
                  </>
                )}
              </div>
            </form>

          </div>
        </div>
      )}

      {/* CLEAR DATA CONFIRMATION MODAL */}
      {showClearConfirm && (
        <div className="modal-overlay">
          <div className="modal-content animate-slide" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <h3 style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertTriangle size={20} className="text-amber-500" /> Clear All Ingested Data
              </h3>
              <button 
                style={{ background: 'none', border: 0, fontSize: '1.5rem', cursor: 'pointer', opacity: 0.5 }}
                onClick={() => setShowClearConfirm(false)}
              >
                &times;
              </button>
            </div>
            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="suspicious-alert" style={{ 
                backgroundColor: 'rgba(245,158,11,0.06)', 
                borderColor: 'rgba(245,158,11,0.2)' 
              }}>
                <div style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>
                  This action will <b>permanently delete</b> all of the following for <b>"{organizations.find(o => o.id === activeOrg)?.name}"</b>:
                  <ul style={{ margin: '0.5rem 0 0 1.25rem', padding: 0 }}>
                    <li>Normalized activity records</li>
                    <li>Raw ingestion source logs</li>
                    <li>Audit trail entries</li>
                  </ul>
                </div>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: 0 }}>
                The client environment and facilities will be preserved. You can re-ingest fresh data afterwards.
              </p>
            </div>
            <div className="modal-footer">
              <button 
                className="btn btn-secondary" 
                onClick={() => setShowClearConfirm(false)}
              >
                Cancel
              </button>
              <button 
                className="btn"
                onClick={handleClearAllData}
                disabled={isClearingData}
                style={{ 
                  background: 'rgba(245,158,11,0.15)', 
                  border: '1px solid rgba(245,158,11,0.5)',
                  color: '#f59e0b', fontWeight: 600 
                }}
              >
                {isClearingData ? (
                  <><RefreshCw className="animate-spin" size={14} /> Clearing...</>
                ) : (
                  <><Trash2 size={14} /> Clear All Data</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* DELETE ENVIRONMENT CONFIRMATION MODAL */}
      {showDeleteOrgConfirm && (
        <div className="modal-overlay">
          <div className="modal-content animate-slide" style={{ maxWidth: '480px' }}>
            <div className="modal-header">
              <h3 style={{ fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertTriangle size={20} className="text-red-500" /> Delete Client Environment
              </h3>
              <button 
                style={{ background: 'none', border: 0, fontSize: '1.5rem', cursor: 'pointer', opacity: 0.5 }}
                onClick={() => setShowDeleteOrgConfirm(false)}
              >
                &times;
              </button>
            </div>
            <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div className="anomaly-alert">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                  <XCircle size={16} /> Destructive Action — Cannot Be Undone
                </div>
                <div style={{ fontSize: '0.9rem', lineHeight: 1.6 }}>
                  This will <b>permanently delete</b> the entire client environment <b>"{organizations.find(o => o.id === activeOrg)?.name}"</b>, including:
                  <ul style={{ margin: '0.5rem 0 0 1.25rem', padding: 0 }}>
                    <li>All facilities & emission factor mappings</li>
                    <li>All ingested records & raw sources</li>
                    <li>All audit trail entries</li>
                    <li>The organization profile itself</li>
                  </ul>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button 
                className="btn btn-secondary" 
                onClick={() => setShowDeleteOrgConfirm(false)}
              >
                Cancel
              </button>
              <button 
                className="btn btn-danger"
                onClick={handleDeleteOrg}
                disabled={isDeletingOrg}
              >
                {isDeletingOrg ? (
                  <><RefreshCw className="animate-spin" size={14} /> Deleting...</>
                ) : (
                  <><Trash2 size={14} /> Delete Environment</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
