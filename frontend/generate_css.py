import re

with open('css/styles.css', 'r') as f:
    css = f.read()

# 1. Update Fonts
css = css.replace("DM Serif Display", "Inter")
css = css.replace("DM Sans", "Inter")
css = css.replace("DM Mono", "JetBrains Mono")
css = css.replace("--font-display: 'Inter', Georgia, serif;", "--font-display: 'Inter', -apple-system, sans-serif;")
css = css.replace("font-family: var(--font-display);", "font-family: var(--font-sans); letter-spacing: -0.02em;")
css = css.replace("font-weight: 400;", "font-weight: 600;") # Make headings bolder

# 2. Update Variables for Coinbridge
variables_old = """  --bg-base:        #f7f5f0;
  --bg-surface:     #ffffff;
  --bg-raised:      #efece4;
  
  --ink-display:    #18160f;
  --ink-primary:    #2e2b22;
  --ink-secondary:  #5a5648;
  --ink-tertiary:   #9c9484;
  --ink-quaternary: #d1ccbf;

  --border-subtle:  rgba(24, 22, 15, 0.08);
  --border-medium:  rgba(24, 22, 15, 0.15);

  /* Brand Accents */
  --accent-gold:    #a07830;
  --accent-gold-bg: #f7f0e2;
  --accent-blue:    #2563eb; 
  --accent-blue-bg: #eff6ff;"""

variables_new = """  /* ── COINBRIDGE LIGHT THEME ── */
  --bg-base:        #f8fafc;
  --bg-surface:     #ffffff;
  --bg-raised:      #f1f5f9;
  
  --ink-display:    #020617;
  --ink-primary:    #0f172a;
  --ink-secondary:  #475569;
  --ink-tertiary:   #94a3b8;
  --ink-quaternary: #cbd5e1;

  --border-subtle:  rgba(15, 23, 42, 0.06);
  --border-medium:  rgba(15, 23, 42, 0.12);

  /* Brand Accents */
  --accent-gold:    #2563eb; /* Reusing var name but mapping to Blue */
  --accent-gold-bg: #eff6ff;
  --accent-blue:    #2563eb; 
  --accent-blue-bg: #eff6ff;"""
css = css.replace(variables_old, variables_new)

dark_vars_old = """  --bg-base:        #0f172a;
  --bg-surface:     #1e293b;
  --bg-raised:      #334155;
  
  --ink-display:    #f8fafc;
  --ink-primary:    #f1f5f9;
  --ink-secondary:  #cbd5e1;
  --ink-tertiary:   #94a3b8;
  --ink-quaternary: #64748b;

  --border-subtle:  rgba(255, 255, 255, 0.08);
  --border-medium:  rgba(255, 255, 255, 0.15);

  --accent-gold:    #c49540;
  --accent-gold-bg: rgba(196, 149, 64, 0.1);
  --accent-blue:    #3b82f6;
  --accent-blue-bg: rgba(59, 130, 246, 0.1);"""

dark_vars_new = """  /* ── COINBRIDGE DARK THEME ── */
  --bg-base:        #020617;
  --bg-surface:     #0f172a;
  --bg-raised:      #1e293b;
  
  --ink-display:    #ffffff;
  --ink-primary:    #f8fafc;
  --ink-secondary:  #94a3b8;
  --ink-tertiary:   #64748b;
  --ink-quaternary: #475569;

  --border-subtle:  rgba(255, 255, 255, 0.05);
  --border-medium:  rgba(255, 255, 255, 0.1);

  --accent-gold:    #3b82f6; /* Glowing Blue */
  --accent-gold-bg: rgba(59, 130, 246, 0.1);
  --accent-blue:    #3b82f6;
  --accent-blue-bg: rgba(59, 130, 246, 0.1);"""
css = css.replace(dark_vars_old, dark_vars_new)

# 3. Non-linear Drop Shadows
shadows_old = """  --shadow-sm:    0 1px 2px 0 rgba(24, 22, 15, 0.05);
  --shadow-md:    0 4px 6px -1px rgba(24, 22, 15, 0.05), 0 2px 4px -2px rgba(24, 22, 15, 0.05);
  --shadow-lg:    0 10px 15px -3px rgba(24, 22, 15, 0.05), 0 4px 6px -4px rgba(24, 22, 15, 0.05);"""
shadows_new = """  --shadow-sm:    0 1px 2px rgba(15, 23, 42, 0.04), 0 2px 4px rgba(15, 23, 42, 0.03);
  --shadow-md:    0 4px 6px rgba(15, 23, 42, 0.04), 0 8px 12px rgba(15, 23, 42, 0.03);
  --shadow-lg:    0 10px 15px rgba(15, 23, 42, 0.05), 0 20px 25px rgba(15, 23, 42, 0.03), 0 4px 6px rgba(15, 23, 42, 0.02);
  --shadow-surreal: 0 20px 40px -10px rgba(15, 23, 42, 0.08), 0 10px 20px -5px rgba(15, 23, 42, 0.04), inset 0 1px 0 rgba(255,255,255,0.5);"""
css = css.replace(shadows_old, shadows_new)

dark_shadows_old = """  --shadow-sm:    0 1px 2px 0 rgba(0, 0, 0, 0.3);
  --shadow-md:    0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.3);
  --shadow-lg:    0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -4px rgba(0, 0, 0, 0.3);"""
dark_shadows_new = """  --shadow-sm:    0 1px 2px rgba(0, 0, 0, 0.4), 0 2px 4px rgba(0, 0, 0, 0.3);
  --shadow-md:    0 4px 6px rgba(0, 0, 0, 0.4), 0 8px 12px rgba(0, 0, 0, 0.3);
  --shadow-lg:    0 10px 15px rgba(0, 0, 0, 0.5), 0 20px 25px rgba(0, 0, 0, 0.4), 0 4px 6px rgba(0, 0, 0, 0.2);
  --shadow-surreal: 0 20px 40px -10px rgba(0, 0, 0, 0.6), 0 10px 20px -5px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255,255,255,0.05);"""
css = css.replace(dark_shadows_old, dark_shadows_new)

# 4. Remove Grain
grain_pattern = re.compile(r'/\* Grain texture overlay.*?}', re.DOTALL)
css = grain_pattern.sub('', css)

dark_grain_pattern = re.compile(r'\[data-theme=\'dark\'\] body::after \{.*?\}', re.DOTALL)
css = dark_grain_pattern.sub('', css)

# 5. Fix Glassmorphism in Header
glass_old = """  .header {
    background: rgba(247, 245, 240, 0.85);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
  }
  [data-theme='dark'] .header {
    background: rgba(15, 23, 42, 0.85);
  }"""
glass_new = """  .header {
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(24px) saturate(180%);
    -webkit-backdrop-filter: blur(24px) saturate(180%);
    box-shadow: 0 1px 0 rgba(15, 23, 42, 0.05);
  }
  [data-theme='dark'] .header {
    background: rgba(15, 23, 42, 0.6);
    box-shadow: 0 1px 0 rgba(255, 255, 255, 0.05);
  }"""
css = css.replace(glass_old, glass_new)

# 6. Add Advanced Rendering to body
body_old = """body {
  font-family: var(--font-sans);
  background-color: var(--bg-base);
  color: var(--ink-primary);
  min-height: 100vh;
  overflow-x: hidden;
  transition: background-color var(--transition-smooth), color var(--transition-smooth);
}"""
body_new = """body {
  font-family: var(--font-sans);
  background-color: var(--bg-base);
  color: var(--ink-primary);
  min-height: 100vh;
  overflow-x: hidden;
  transition: background-color var(--transition-smooth), color var(--transition-smooth);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}"""
css = css.replace(body_old, body_new)

# 7. Add Micro-interactions to Table
table_hover_old = "tbody tr:hover { background: var(--bg-raised); }"
table_hover_new = "tbody tr { transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), background 0.3s, box-shadow 0.3s; }\ntbody tr:hover { background: var(--bg-raised); transform: translateY(-1px); box-shadow: var(--shadow-sm); z-index: 2; position: relative; }"
css = css.replace(table_hover_old, table_hover_new)

# 8. Modal Surreal Shadow
modal_old = "box-shadow: -10px 0 30px rgba(0,0,0,0.1);"
modal_new = "box-shadow: var(--shadow-surreal);"
css = css.replace(modal_old, modal_new)

with open('css/styles.css', 'w') as f:
    f.write(css)

print("Styles perfectly adapted to Coinbridge.")
