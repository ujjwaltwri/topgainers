import re

with open('index.html', 'r') as f:
    html = f.read()

# 1. Bump Cache busters to break browser cache!
html = html.replace("href='css/styles.css'", "href='css/styles.css?v=11'")
html = html.replace("src=\"js/app.js\"", "src=\"js/app.js?v=11\"")
html = html.replace("src=\"js/table.js\"", "src=\"js/table.js?v=11\"")

# Handle if they already had versions
html = re.sub(r'href=[\'"]css/styles\.css\?v=\d+[\'"]', "href='css/styles.css?v=11'", html)
html = re.sub(r'src=[\'"]js/app\.js\?v=\d+[\'"]', 'src="js/app.js?v=11"', html)
html = re.sub(r'src=[\'"]js/table\.js\?v=\d+[\'"]', 'src="js/table.js?v=11"', html)

with open('index.html', 'w') as f:
    f.write(html)

print("Cache busters successfully updated in index.html")
