with open('frontend/index.html', 'r') as f:
    index_html = f.read()

with open('frontend/overview.html', 'r') as f:
    overview_html = f.read()

# Extract marquee + header from index.html
start_idx = index_html.find('<!-- GLOBAL INDEX MARQUEE -->')
end_idx = index_html.find('</header>') + len('</header>')
header_block = index_html[start_idx:end_idx]

# Modify header_block for overview.html
# 1. Dashboard shouldn't be active
header_block = header_block.replace('<a href="/" class="nav-link active">Dashboard</a>', '<a href="/" class="nav-link">Dashboard</a>')
# 2. Overview should be active
header_block = header_block.replace('<a href="/overview.html" class="nav-link">\n        <svg', '<a href="/overview.html" class="nav-link active">\n        <svg')

# Remove the search container from the overview header (as there's no table to filter)
import re
search_pattern = re.compile(r'<div class="search-container">.*?</div>', re.DOTALL)
header_block = search_pattern.sub('', header_block)

# Replace the header in overview.html
start_replace = overview_html.find('<!-- HEADER -->')
end_replace = overview_html.find('</header>') + len('</header>')

new_html = overview_html[:start_replace] + header_block + overview_html[end_replace:]

with open('frontend/overview.html', 'w') as f:
    f.write(new_html)

print("overview.html updated with index.html header and marquee")
