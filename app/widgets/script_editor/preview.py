"""预览组件 — 渲染 markdown 结果、SEO 优化结果"""

import mistune


class PreviewRenderer:
    """Markdown 渲染器"""

    @staticmethod
    def render_markdown(text: str) -> str:
        """将 markdown 渲染为带样式的 HTML"""
        html = mistune.html(text)
        css = """
        <style>
        body { color: #c9d1d9; font-size: 13px; line-height: 1.6; margin: 0; padding: 12px; }
        h1, h2, h3, h4 { color: #e6edf3; font-weight: bold; margin: 12px 0 8px 0; }
        h1 { font-size: 18px; border-bottom: 1px solid #30363d; padding-bottom: 6px; }
        h2 { font-size: 16px; }
        h3 { font-size: 14px; }
        p { margin: 8px 0; }
        code { background: #161b22; color: #ff7b72; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 12px; }
        pre { background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px; overflow-x: auto; }
        pre code { background: none; padding: 0; color: #c9d1d9; }
        blockquote { border-left: 3px solid #ff6b81; margin: 8px 0; padding: 4px 12px; color: #8b949e; }
        ul, ol { margin: 8px 0; padding-left: 24px; }
        li { margin: 4px 0; }
        strong { color: #e6edf3; font-weight: bold; }
        em { color: #c9d1d9; font-style: italic; }
        a { color: #58a6ff; text-decoration: none; }
        table { border-collapse: collapse; width: 100%; margin: 8px 0; }
        th, td { border: 1px solid #30363d; padding: 6px 12px; text-align: left; }
        th { background: #161b22; color: #e6edf3; }
        tr:nth-child(even) { background: #161b22; }
        hr { border: none; border-top: 1px solid #30363d; margin: 12px 0; }
        </style>
        """
        return f"<!DOCTYPE html><html><head>{css}</head><body>{html}</body></html>"
