import html
import json


def export_json(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, default=str)


def export_html(title: str, data: object) -> str:
    body = html.escape(export_json(data))
    return (
        "<!doctype html><html lang='zh-CN'><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title><body><h1>{html.escape(title)}</h1>"
        f"<pre>{body}</pre><p>本导出仅用于可追溯审阅。</p></body></html>"
    )
