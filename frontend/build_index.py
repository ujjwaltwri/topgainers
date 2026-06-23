import re

with open('index.html', 'r') as f:
    html = f.read()

# 1. Bump Cache busters to break browser cache!
html = html.replace("href='css/styles.css'", "href='css/styles.css?v=10'")
html = html.replace("src=\"js/app.js?v=3\"", "src=\"js/app.js?v=10\"")
html = html.replace("src=\"js/table.js\"", "src=\"js/table.js?v=10\"")

# 2. Add Collapsible Sidebar Logic
html = re.sub(
    r'<div class="filter-group">\s*<label>(.*?)</label>(.*?)</div>',
    r'<details class="filter-group" open><summary class="filter-label">\1</summary><div class="filter-content">\2</div></details>',
    html,
    flags=re.DOTALL
)

html = re.sub(
    r'<div class="filter-group hidden" id="custom-date-group">\s*<label>(.*?)</label>(.*?)</div>',
    r'<details class="filter-group hidden" id="custom-date-group"><summary class="filter-label">\1</summary><div class="filter-content">\2</div></details>',
    html,
    flags=re.DOTALL
)

html = re.sub(
    r'<div class="filter-group quick-filters">\s*<label>(.*?)</label>(.*?)</div>',
    r'<details class="filter-group quick-filters" open><summary class="filter-label">\1</summary><div class="filter-content">\2</div></details>',
    html,
    flags=re.DOTALL
)

with open('index.html', 'w') as f:
    f.write(html)

print("index.html successfully updated")
