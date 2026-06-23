css = """
/* ═══════════════════════════════════════════════════════════════
   MOBILE RESPONSIVENESS
═══════════════════════════════════════════════════════════════ */
@media (max-width: 900px) {
  /* Header Adjustments */
  .header {
    height: auto;
    min-height: 64px;
    padding: var(--space-sm) var(--space-md);
    flex-wrap: wrap;
    gap: var(--space-sm);
  }
  
  .logo {
    font-size: 16px;
  }
  
  .header-nav {
    margin-left: auto;
    gap: var(--space-md);
    order: 2;
  }
  
  .header-actions {
    order: 3;
  }

  .pipeline-status span:not(.status-dot), .last-updated {
    display: none; /* Hide text on mobile to save space */
  }
  
  .search-container {
    order: 4;
    width: 100%;
    max-width: 100%;
    margin-top: 4px;
    margin-bottom: 4px;
  }
  
  /* Main Container & Sidebar */
  .main-container {
    flex-direction: column;
    margin-top: 110px; /* Account for wrapped header */
    height: calc(100vh - 110px);
  }
  
  .sidebar {
    width: 100%;
    height: auto;
    max-height: 250px; /* Scrollable filter box above results */
    border-right: none;
    border-bottom: 1px solid var(--border-subtle);
    padding: var(--space-md);
  }
  
  .results-area {
    padding: var(--space-md);
  }
  
  /* Controls Row */
  .controls-row {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-md);
  }
  
  .results-meta {
    justify-content: space-between;
    width: 100%;
  }

  /* Table Container */
  .table-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    width: 100%;
  }
  
  #results-table {
    min-width: 800px; /* Ensure columns don't squish */
  }
  
  /* Modals Full Screen */
  .stock-modal {
    width: 100%;
    height: 100%;
    max-width: none;
    max-height: none;
    top: 0 !important;
    left: 0 !important;
    transform: none !important;
    border-radius: 0;
    border: none;
    overflow-y: auto;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .modal-actions {
    flex-direction: column;
  }
  
  .modal-actions button {
    width: 100%;
  }
}
"""

with open('frontend/css/styles.css', 'a') as f:
    f.write(css)

print("CSS appended.")
