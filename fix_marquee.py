with open('frontend/css/styles.css', 'r') as f:
    css = f.read()

# Fix marquee container
old_marquee = """.marquee-container {
  width: 100%;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-medium);
  overflow: hidden;
  white-space: nowrap;
  padding: 8px 0;
  box-sizing: border-box;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  position: relative;
  z-index: 100;
}"""

new_marquee = """.marquee-container {
  width: 100%;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-medium);
  overflow: hidden;
  white-space: nowrap;
  padding: 8px 0;
  box-sizing: border-box;
  font-family: var(--font-mono);
  font-size: 12px;
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 32px;
  z-index: 101;
}"""
css = css.replace(old_marquee, new_marquee)

# Fix header top
css = css.replace("top: 0; left: 0; right: 0;\n  height: 64px;", "top: 32px; left: 0; right: 0;\n  height: 64px;")

# Fix main container margin
css = css.replace("margin-top: 64px;\n  height: calc(100vh - 64px);", "margin-top: 96px;\n  height: calc(100vh - 96px);")

# Wait, there's also the mobile override we appended at the bottom!
css = css.replace("margin-top: 110px; /* Account for wrapped header */\n    height: calc(100vh - 110px);", "margin-top: 142px; /* Account for wrapped header + marquee */\n    height: calc(100vh - 142px);")

with open('frontend/css/styles.css', 'w') as f:
    f.write(css)

print("Marquee fixed!")
