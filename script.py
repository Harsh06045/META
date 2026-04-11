import os

with open('app/server.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == 'def index():':
        break
    new_lines.append(line)

new_lines.append('def index():\n')
new_lines.append('    html_path = os.path.join(os.path.dirname(__file__), "index.html")\n')
new_lines.append('    with open(html_path, "r", encoding="utf-8") as f:\n')
new_lines.append('        html_content = f.read()\n')
new_lines.append('    return HTMLResponse(content=html_content)\n\n')

new_lines.append('if __name__ == "__main__":\n')
new_lines.append('    port = int(os.getenv("PORT", 7860))\n')
new_lines.append('    uvicorn.run("app.server:app", host="0.0.0.0", port=port, reload=False)\n')

with open('app/server.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Updated app/server.py successfully!')
