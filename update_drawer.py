import re

# 1. Update index.html
with open('frontend/index.html', 'r') as f:
    html = f.read()

# Add overlay and id to sidebar
html = html.replace('<aside class="sidebar">', 
    '<!-- Mobile Sidebar Overlay -->\n    <div id="sidebar-overlay" class="mobile-overlay hidden"></div>\n    <aside id="sidebar" class="sidebar">')

# Add close button
header_original = '''      <div class="sidebar-header">
        <h3>Filters</h3>
        <button id="reset-filters" class="btn-ghost text-small">Reset All</button>
      </div>'''
header_new = '''      <div class="sidebar-header">
        <div style="display:flex; align-items:center; gap:8px;">
          <h3>Filters</h3>
          <button id="close-sidebar" class="btn-icon mobile-only" style="width:28px; height:28px;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>
        </div>
        <button id="reset-filters" class="btn-ghost text-small">Reset All</button>
      </div>'''
html = html.replace(header_original, header_new)

# Add Filter button
controls_orig = '<div class="controls-row">'
controls_new = '''<div class="controls-row">
        <button id="mobile-filter-btn" class="btn-outline mobile-only" style="width:100%; justify-content:center; margin-bottom: 8px;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:16px; height:16px;"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon></svg>
          Filters
        </button>'''
html = html.replace(controls_orig, controls_new)

with open('frontend/index.html', 'w') as f:
    f.write(html)


# 2. Update styles.css
with open('frontend/css/styles.css', 'r') as f:
    css = f.read()

# We need to replace the sidebar mobile logic we just added.
old_sidebar_css = '''  .sidebar {
    width: 100%;
    height: auto;
    max-height: 250px; /* Scrollable filter box above results */
    border-right: none;
    border-bottom: 1px solid var(--border-subtle);
    padding: var(--space-md);
  }'''

new_sidebar_css = '''  .mobile-only { display: flex !important; }
  .mobile-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 998;
    backdrop-filter: blur(2px);
  }
  .sidebar {
    position: fixed;
    top: 0; left: -320px;
    width: 300px;
    height: 100vh;
    z-index: 999;
    transition: left 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    border-right: 1px solid var(--border-subtle);
    border-bottom: none;
  }
  .sidebar.open {
    left: 0;
  }'''

css = css.replace(old_sidebar_css, new_sidebar_css)

# Add mobile-only base class
if '.mobile-only' not in css[:2000]:
    css = css.replace("/* ──────────── UTILITY CLASSES ──────────── */", "/* ──────────── UTILITY CLASSES ──────────── */\n.mobile-only { display: none !important; }")

with open('frontend/css/styles.css', 'w') as f:
    f.write(css)

print("HTML and CSS updated.")
