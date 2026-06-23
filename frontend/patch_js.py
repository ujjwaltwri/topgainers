with open('js/app.js', 'r') as f:
    js = f.read()

# Replace 'N/A' with '—' in populateModal
js = js.replace("'N/A'", "'—'")

# Add dimming to empty fields
js = js.replace("vsSecEl.className = 'stat-value font-mono ' + (g.vs_sector > 0 ? 'text-gain' : (g.vs_sector < 0 ? 'text-loss' : ''));",
                "vsSecEl.className = 'stat-value font-mono ' + (g.vs_sector > 0 ? 'text-gain' : (g.vs_sector < 0 ? 'text-loss' : '')) + (g.vs_sector ? '' : ' dimmed');")

js = js.replace("vsCtyEl.className = 'stat-value font-mono ' + (g.vs_country > 0 ? 'text-gain' : (g.vs_country < 0 ? 'text-loss' : ''));",
                "vsCtyEl.className = 'stat-value font-mono ' + (g.vs_country > 0 ? 'text-gain' : (g.vs_country < 0 ? 'text-loss' : '')) + (g.vs_country ? '' : ' dimmed');")

# Fix Chart empty state
old_warning = "`<div style='color:orange; padding:20px;'>WARNING: No price history data found for ${data.stock?.ticker} in the database.</div>`"
new_warning = "`<div class='empty-state' style='height:100%; justify-content:center; padding: 20px;'><div class='empty-icon'><svg viewBox='0 0 24 24' width='48' height='48' fill='none' stroke='currentColor' stroke-width='1.5'><path d='M3 3v18h18'></path><path d='M18 9l-5-5-4 4-5-5'></path></svg></div><div class='empty-text'>No Chart Data Available</div><div class='empty-sub'>Price history for ${data.stock?.ticker || 'this stock'} was not found in the database.</div></div>`"
js = js.replace(old_warning, new_warning)

with open('js/app.js', 'w') as f:
    f.write(js)

print("app.js patched.")
