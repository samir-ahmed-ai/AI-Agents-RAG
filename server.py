import http.server
import os
import sys
import urllib.parse

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>__TITLE__ - Premium Documentation Reader</title>
  
  <!-- FontAwesome & Google Fonts -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Outfit:wght@300;400;600;700;800&display=swap" rel="stylesheet">
  
  <!-- Marked.js Markdown Parser -->
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  
  <style>
    :root {
      --bg-main: #060814;
      --bg-card: #0b0e22;
      --bg-sidebar: #04050d;
      --primary: #6366f1;
      --primary-glow: rgba(99, 102, 241, 0.35);
      --accent: #06b6d4;
      --accent-glow: rgba(6, 182, 212, 0.35);
      --secondary: #a855f7;
      --border-color: rgba(255, 255, 255, 0.08);
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Outfit', sans-serif;
      background-color: var(--bg-main);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      background-image: 
        radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
        radial-gradient(at 100% 100%, rgba(6, 182, 212, 0.15) 0px, transparent 50%);
      background-attachment: fixed;
    }

    header {
      background: var(--bg-sidebar);
      border-bottom: 1px solid var(--border-color);
      padding: 1.2rem 5%;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 0.8rem;
    }

    .logo {
      color: var(--accent);
      font-size: 1.5rem;
    }

    .title {
      font-size: 1.2rem;
      font-weight: 700;
      color: #fff;
    }

    .header-right {
      display: flex;
      gap: 1rem;
    }

    .btn {
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 0.5rem 1.2rem;
      border-radius: 8px;
      font-family: inherit;
      font-size: 0.9rem;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.3s ease;
    }

    .btn:hover {
      background: var(--primary);
      border-color: var(--primary);
      box-shadow: 0 0 15px var(--primary-glow);
      color: #fff;
    }

    .btn-primary {
      background: var(--primary);
      border-color: var(--primary);
      color: #fff;
    }

    .btn-primary:hover {
      background: #4f46e5;
      box-shadow: 0 0 20px var(--primary-glow);
    }

    main {
      flex-grow: 1;
      padding: 3rem 5%;
      display: flex;
      justify-content: center;
    }

    .reader-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 20px;
      width: 100%;
      max-width: 900px;
      padding: 3.5rem;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
      position: relative;
      overflow: hidden;
    }

    .reader-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 4px;
      background: linear-gradient(90deg, var(--primary), var(--accent), var(--secondary));
    }

    .markdown-body {
      color: var(--text-main);
      font-size: 1.05rem;
      line-height: 1.8;
    }

    .markdown-body h1, .markdown-body h2, .markdown-body h3, .markdown-body h4 {
      color: #fff;
      font-weight: 700;
      margin-top: 2.2rem;
      margin-bottom: 1.2rem;
    }

    .markdown-body h1 {
      font-size: 2.4rem;
      border-bottom: 1px solid rgba(255,255,255,0.08);
      padding-bottom: 0.8rem;
      margin-top: 0;
    }

    .markdown-body h2 {
      font-size: 1.8rem;
      border-bottom: 1px solid rgba(255,255,255,0.04);
      padding-bottom: 0.4rem;
    }

    .markdown-body h3 {
      font-size: 1.35rem;
    }

    .markdown-body p {
      color: var(--text-muted);
      margin-bottom: 1.4rem;
    }

    .markdown-body ul, .markdown-body ol {
      margin-bottom: 1.4rem;
      padding-left: 2rem;
      color: var(--text-muted);
    }

    .markdown-body li {
      margin-bottom: 0.6rem;
    }

    .markdown-body code {
      font-family: 'JetBrains Mono', monospace;
      background: rgba(255,255,255,0.05);
      padding: 0.2rem 0.4rem;
      border-radius: 4px;
      font-size: 0.9rem;
      color: var(--accent);
    }

    .markdown-body pre {
      background: #030408;
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 1.5rem;
      overflow-x: auto;
      margin: 1.8rem 0;
    }

    .markdown-body pre code {
      background: transparent;
      padding: 0;
      color: #c9d1d9;
      font-size: 0.88rem;
      display: block;
    }

    .markdown-body blockquote {
      border-left: 4px solid var(--primary);
      background: rgba(99, 102, 241, 0.03);
      padding: 1rem 1.5rem;
      margin: 1.8rem 0;
      border-radius: 0 10px 10px 0;
      color: var(--text-muted);
    }

    .markdown-body table {
      width: 100%;
      border-collapse: collapse;
      margin: 1.8rem 0;
    }

    .markdown-body th, .markdown-body td {
      border: 1px solid var(--border-color);
      padding: 0.9rem 1.1rem;
      text-align: left;
      font-size: 0.95rem;
    }

    .markdown-body th {
      background: rgba(255,255,255,0.02);
      color: #fff;
      font-weight: 600;
    }

    .markdown-body tr:nth-child(even) {
      background: rgba(255,255,255,0.01);
    }

    .markdown-body a {
      color: var(--accent);
      text-decoration: none;
      border-bottom: 1px dashed rgba(6, 182, 212, 0.4);
      transition: all 0.3s ease;
    }

    .markdown-body a:hover {
      color: #fff;
      border-bottom-color: #fff;
    }

    .markdown-body hr {
      border: none;
      border-top: 1px solid var(--border-color);
      margin: 2.5rem 0;
    }

    footer {
      border-top: 1px solid var(--border-color);
      background: var(--bg-sidebar);
      padding: 1.8rem;
      text-align: center;
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: auto;
    }
  </style>
</head>
<body>
  <header>
    <div class="header-left">
      <i class="fa-solid fa-cube logo"></i>
      <div class="title">Workspace Document Reader</div>
    </div>
    <div class="header-right">
      <a href="/" class="btn"><i class="fa-solid fa-house"></i> Dashboard Hub</a>
      <button class="btn btn-primary" onclick="copyFilePath()"><i class="fa-regular fa-copy"></i> Copy Path</button>
    </div>
  </header>

  <main>
    <div class="reader-card">
      <div id="content" class="markdown-body">
        <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
          <i class="fa-solid fa-circle-notch fa-spin fa-2x" style="color: var(--accent); margin-bottom: 1rem;"></i>
          <p>Compiling high-fidelity document layout...</p>
        </div>
      </div>
    </div>
  </main>

  <footer>
    <p>Local AI Monorepo Workspace Observation Console • Absolutely Private & Secure</p>
  </footer>

  <script>
    const markdownText = `__MARKDOWN_TEXT__`;
    
    document.addEventListener("DOMContentLoaded", () => {
      const content = document.getElementById("content");
      if (typeof marked !== 'undefined') {
        content.innerHTML = marked.parse(markdownText);
      } else {
        content.innerHTML = `<pre style="white-space: pre-wrap; font-family: monospace;">` + markdownText + `</pre>`;
      }
    });

    function copyFilePath() {
      const fullPath = window.location.pathname;
      navigator.clipboard.writeText(fullPath).then(() => {
        alert("Path copied to clipboard: " + fullPath);
      });
    }
  </script>
</body>
</html>
"""

class PremiumHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        clean_path = parsed_path.path
        
        # intercept markdown files
        if clean_path.endswith('.md'):
            local_path = self.translate_path(clean_path)
            if os.path.exists(local_path) and os.path.isfile(local_path):
                try:
                    with open(local_path, 'r', encoding='utf-8') as f:
                        md_content = f.read()
                    
                    # Serve beautifully rendered html
                    html_content = self.render_markdown_page(clean_path, md_content)
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                    self.send_header('Pragma', 'no-cache')
                    self.send_header('Expires', '0')
                    
                    encoded_html = html_content.encode('utf-8')
                    self.send_header('Content-Length', str(len(encoded_html)))
                    self.end_headers()
                    self.wfile.write(encoded_html)
                    return
                except Exception as e:
                    pass
        
        return super().do_GET()

    def render_markdown_page(self, filename, markdown_content):
        # Escape markdown characters for JS string literal safety
        safe_md = (
            markdown_content
            .replace('\\', '\\\\')
            .replace('`', '\\`')
            .replace('$', '\\$')
        )
        title = os.path.basename(filename)
        return HTML_TEMPLATE.replace('__TITLE__', title).replace('__MARKDOWN_TEXT__', safe_md)

if __name__ == '__main__':
    port = 3000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, PremiumHTTPRequestHandler)
    print(f"Starting Premium HTTP server on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        sys.exit(0)
