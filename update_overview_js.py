with open('frontend/js/app.js', 'r') as f:
    app_js = f.read()

# Extract renderMarquee from app.js
import re
match = re.search(r'(async renderMarquee\(\) \{.*?\n  \})', app_js, re.DOTALL)
if match:
    render_marquee_func = match.group(1)
else:
    print("Could not find renderMarquee in app.js")
    exit(1)

with open('frontend/js/overview.js', 'r') as f:
    overview_js = f.read()

# Insert renderMarquee after setupPeriodSelector
overview_js = overview_js.replace('  setupPeriodSelector() {', render_marquee_func + '\n\n  setupPeriodSelector() {')

# Also need to call it in init()!
init_str = """  async init() {
    this.setupTheme();
    this.setupPeriodSelector();"""
    
new_init = """  async init() {
    this.setupTheme();
    this.setupPeriodSelector();
    this.renderMarquee();"""

overview_js = overview_js.replace(init_str, new_init)

# And call it when period changes
period_click_str = """        this.period = btn.dataset.period;
        this.fetchAllData();"""
new_period_click = """        this.period = btn.dataset.period;
        this.fetchAllData();
        this.renderMarquee();"""
        
overview_js = overview_js.replace(period_click_str, new_period_click)

with open('frontend/js/overview.js', 'w') as f:
    f.write(overview_js)

print("overview.js updated with renderMarquee logic")
