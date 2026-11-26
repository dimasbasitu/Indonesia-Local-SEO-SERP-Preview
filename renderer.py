import html
import json
from urllib.parse import urlsplit


EXCLUDED_RESULT_KEYS = {
    "ads",
    "aiOverview",
    "shoppingAds",
}


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def safe_url(value) -> str:
    url = str(value or "").strip()
    try:
        parsed = urlsplit(url)
    except ValueError:
        return ""
    return url if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def _filtered_payload(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if key not in EXCLUDED_RESULT_KEYS}


def _sitelink_urls(item: dict) -> list[str]:
    sitelinks = item.get("sitelinks") or []
    if isinstance(sitelinks, dict):
        sitelinks = (sitelinks.get("inline") or []) + (sitelinks.get("expanded") or [])
    return [link.get("link") for link in sitelinks if isinstance(link, dict) and safe_url(link.get("link"))]


def _result_entities(payload: dict) -> list[dict]:
    entities = []

    for index, item in enumerate(payload.get("organic") or []):
        if not isinstance(item, dict):
            continue
        urls = [item.get("link"), *_sitelink_urls(item)]
        entities.append({
            "id": f"organic-{index}",
            "path": ("organic", index),
            "title": item.get("title", ""),
            "urls": [url for url in urls if safe_url(url)],
        })

    for section, prefix in (("places", "place"), ("shopping", "shopping")):
        for index, item in enumerate(payload.get(section) or []):
            if not isinstance(item, dict):
                continue
            urls = [item.get("website"), item.get("link")]
            entities.append({
                "id": f"{prefix}-{index}",
                "path": (section, index),
                "title": item.get("title", ""),
                "urls": [url for url in urls if safe_url(url)],
            })

    for index, item in enumerate(payload.get("peopleAlsoAsk") or []):
        if not isinstance(item, dict):
            continue
        entities.append({
            "id": f"question-{index}",
            "path": ("peopleAlsoAsk", index),
            "title": item.get("question") or item.get("title", ""),
            "urls": [item["link"]] if safe_url(item.get("link")) else [],
        })
    return entities


def _preview_card(entity_id: str, item: dict, kind: str = "result") -> str:
    link = safe_url(item.get("link") or item.get("website"))
    title = item.get("title") or item.get("question") or "Hasil tanpa judul"
    snippet = item.get("snippet") or item.get("description") or item.get("address") or ""
    host = urlsplit(link).netloc.removeprefix("www.") if link else ""
    position = item.get("position")
    position_label = f'<span class="position">{esc(position)}</span>' if position is not None else ""
    title_markup = f'<a href="{esc(link)}" target="_blank" rel="noopener noreferrer">{esc(title)}</a>' if link else esc(title)
    return f"""
      <article class="preview-card {esc(kind)}" data-serp-entity="{esc(entity_id)}" tabindex="0" role="button" aria-label="Sinkronkan {esc(title)} ke raw JSON">
        <div class="result-meta">{position_label}<span>{esc(host or kind)}</span></div>
        <h2>{title_markup}</h2>
        {f'<p>{esc(snippet)}</p>' if snippet else ''}
      </article>
    """


def _build_serper_preview(payload: dict) -> str:
    search = payload.get("searchParameters") or {}
    query = search.get("q") or "Hasil pencarian"
    sections = []

    places = payload.get("places") or []
    if places:
        cards = "".join(
            _preview_card(f"place-{index}", item, "lokasi")
            for index, item in enumerate(places)
            if isinstance(item, dict)
        )
        sections.append(f'<section><h1>Hasil lokal</h1><div class="local-list">{cards}</div></section>')

    shopping = payload.get("shopping") or []
    if shopping:
        cards = "".join(
            _preview_card(f"shopping-{index}", item, "belanja")
            for index, item in enumerate(shopping)
            if isinstance(item, dict)
        )
        sections.append(f'<section><h1>Hasil belanja</h1>{cards}</section>')

    organic = payload.get("organic") or []
    if organic:
        cards = "".join(
            _preview_card(f"organic-{index}", item)
            for index, item in enumerate(organic)
            if isinstance(item, dict)
        )
        sections.append(f'<section><h1>Hasil organik</h1>{cards}</section>')

    questions = payload.get("peopleAlsoAsk") or []
    if questions:
        cards = "".join(
            _preview_card(f"question-{index}", item, "pertanyaan")
            for index, item in enumerate(questions)
            if isinstance(item, dict)
        )
        sections.append(f'<section><h1>Pertanyaan terkait</h1>{cards}</section>')

    if not sections:
        sections.append('<p class="empty">Serper tidak mengembalikan hasil untuk pencarian ini. Coba kata kunci atau lokasi lain.</p>')

    return f"""
    <!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      * {{ box-sizing: border-box; }}
      html {{ scroll-behavior: smooth; }}
      body {{ margin: 0; padding: clamp(1rem, 3vw, 2rem); color: #202124; background: #fff; font: 0.95rem/1.55 Arial, sans-serif; }}
      .query {{ margin: 0 0 1.5rem; color: #5f6368; overflow-wrap: anywhere; }}
      section {{ margin: 0 0 2rem; }}
      section > h1 {{ margin: 0 0 .8rem; color: #202124; font-size: 1rem; }}
      .preview-card {{ max-width: 44rem; margin: 0 0 .45rem; padding: .75rem; border: 2px solid transparent; border-radius: .5rem; cursor: pointer; }}
      .preview-card:hover {{ background: #f8f9fa; }}
      .preview-card.selected {{ border-color: #c5221f; background: #fef7f6; }}
      .preview-card:focus-visible {{ outline: 3px solid #1a73e8; outline-offset: 2px; }}
      .result-meta {{ display: flex; gap: .45rem; align-items: center; min-height: 1.4rem; color: #4d5156; font-size: .82rem; overflow-wrap: anywhere; }}
      .position {{ display: inline-grid; place-items: center; min-width: 1.4rem; height: 1.4rem; color: #fff; background: #3c4043; border-radius: .25rem; font-weight: 700; }}
      h2 {{ margin: .15rem 0; font-size: clamp(1.05rem, 2.5vw, 1.25rem); font-weight: 400; line-height: 1.3; overflow-wrap: anywhere; }}
      h2 a {{ color: #1a0dab; text-decoration: none; }}
      h2 a:hover {{ text-decoration: underline; }}
      h2 a:focus-visible {{ outline: 3px solid #1a73e8; outline-offset: 2px; }}
      p {{ margin: .3rem 0 0; overflow-wrap: anywhere; }}
      .empty {{ padding: 1rem; border: 1px solid #bdc1c6; border-radius: .5rem; }}
      @media (max-width: 40rem) {{ body {{ padding: 1rem .6rem; }} .preview-card {{ padding: .7rem .55rem; }} }}
    </style></head><body>
      <p class="query">Preview Serper untuk <strong>{esc(query)}</strong></p>
      {''.join(sections)}
      <script>
        const select = (id, shouldScroll = true) => {{
          document.querySelectorAll('.selected').forEach(node => node.classList.remove('selected'));
          const target = document.querySelector(`[data-serp-entity="${{CSS.escape(id)}}"]`);
          if (!target) return;
          target.classList.add('selected');
          if (shouldScroll) target.scrollIntoView({{behavior: 'smooth', block: 'center'}});
        }};
        document.addEventListener('click', event => {{
          const card = event.target.closest('[data-serp-entity]');
          if (!card) return;
          if (event.target.closest('a[href]')) return;
          select(card.dataset.serpEntity, false);
          parent.postMessage({{type: 'serp-result-selected', id: card.dataset.serpEntity}}, '*');
        }});
        document.addEventListener('keydown', event => {{
          const card = event.target.closest?.('[data-serp-entity]');
          if (!card || event.target !== card || !['Enter', ' '].includes(event.key)) return;
          event.preventDefault();
          select(card.dataset.serpEntity, false);
          parent.postMessage({{type: 'serp-result-selected', id: card.dataset.serpEntity}}, '*');
        }});
        window.addEventListener('message', event => {{
          if (event.data?.type === 'select-serp-result') select(event.data.id);
        }});
      </script>
    </body></html>
    """


def _json_scalar(value) -> str:
    if isinstance(value, str):
        return f'<span class="json-string">{esc(json.dumps(value, ensure_ascii=False))}</span>'
    if value is True or value is False:
        return f'<span class="json-bool">{str(value).lower()}</span>'
    if value is None:
        return '<span class="json-null">null</span>'
    return f'<span class="json-number">{esc(json.dumps(value, ensure_ascii=False))}</span>'


def _json_key(value) -> str:
    return f'<span class="json-key">{esc(json.dumps(str(value), ensure_ascii=False))}</span>: '


def _json_line(indent: int, content: str) -> str:
    return f'<div class="json-line" style="padding-left:{indent * 18}px">{content}</div>'


def _render_json_node(value, path: tuple, path_ids: dict, indent: int = 0, prefix: str = "", comma: bool = False) -> str:
    suffix = "," if comma else ""
    if isinstance(value, dict):
        parts = [_json_line(indent, prefix + "{")]
        items = list(value.items())
        for index, (key, child) in enumerate(items):
            parts.append(_render_json_node(child, path + (key,), path_ids, indent + 1, _json_key(key), index < len(items) - 1))
        parts.append(_json_line(indent, "}" + suffix))
    elif isinstance(value, list):
        parts = [_json_line(indent, prefix + "[")]
        for index, child in enumerate(value):
            parts.append(_render_json_node(child, path + (index,), path_ids, indent + 1, "", index < len(value) - 1))
        parts.append(_json_line(indent, "]" + suffix))
    else:
        parts = [_json_line(indent, prefix + _json_scalar(value) + suffix)]

    content = "".join(parts)
    entity_id = path_ids.get(path)
    if entity_id:
        label = f"Sinkronkan blok JSON {entity_id} ke preview SERP"
        return f'<section class="json-hit" id="json-{esc(entity_id)}" data-serp-entity="{esc(entity_id)}" role="button" tabindex="0" aria-label="{esc(label)}">{content}</section>'
    return content


def build_serp_viewer(payload: dict) -> str:
    display_payload = _filtered_payload(payload)
    entities = _result_entities(display_payload)
    path_ids = {item["path"]: item["id"] for item in entities}
    preview_html = _build_serper_preview(display_payload)
    preview_json = json.dumps(preview_html, ensure_ascii=True).replace("</", "<\\/")
    json_markup = _render_json_node(display_payload, (), path_ids)

    return f"""
    <!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>
      * {{ box-sizing: border-box; }}
      html, body {{ margin: 0; background: transparent; font-family: Arial, sans-serif; }}
      .viewer {{ height: 1020px; display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 1px; overflow: hidden; border: 1px solid #3f4147; border-radius: 13px; background: #3f4147; }}
      .panel {{ min-width: 0; min-height: 0; overflow: hidden; background: #fff; }}
      .panel:last-child {{ background: #20211d; }}
      .panel-head {{ min-height: 44px; padding: .55rem .9rem; display: flex; gap: .5rem; align-items: center; justify-content: space-between; border-bottom: 1px solid #dfe1e5; background: #fff; color: #3c4043; font-size: .75rem; font-weight: 700; }}
      .panel-head small {{ color: #5f6368; font-size: .68rem; font-weight: 500; text-align: right; }}
      .json-head {{ color: #f3f4f6; border-color: #383a34; background: #292b27; }}
      .json-head small {{ color: #d5d8d0; }}
      #preview-frame {{ display: block; width: 100%; height: calc(100% - 44px); border: 0; background: #fff; }}
      .json-scroll {{ height: calc(100% - 44px); overflow: auto; padding: 10px 0 28px; color: #f8f8f2; background: #20211d; font: .75rem/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; scrollbar-color: #8b8b86 #292b27; }}
      .json-line {{ min-height: 18px; padding-right: 14px; white-space: pre-wrap; overflow-wrap: anywhere; }}
      .json-key {{ color: #ff4f88; font-weight: 600; }} .json-string {{ color: #a7ef3a; }} .json-number {{ color: #7dd3fc; }} .json-bool {{ color: #fbbf24; }} .json-null {{ color: #c4a7ff; }}
      .json-hit {{ display: block; border: 2px solid transparent; transition: border-color .15s, background-color .15s; cursor: pointer; }}
      .json-hit.selected {{ border-color: #ff5263; background: rgba(255,82,99,.08); }}
      .json-hit:focus-visible {{ outline: 3px solid #8ab4f8; outline-offset: -3px; }}
      @media (max-width: 70rem) {{ .panel-head {{ align-items: flex-start; flex-direction: column; }} .panel-head small {{ text-align: left; }} #preview-frame, .json-scroll {{ height: calc(100% - 58px); }} }}
      @media (max-width: 50rem) {{ .viewer {{ height: 1500px; grid-template-columns: 1fr; grid-template-rows: minmax(0, 1fr) minmax(0, 1fr); }} }}
    </style></head><body>
      <main class="viewer">
        <section class="panel"><header class="panel-head"><span>Preview SERP</span><small>Data Serper, bukan salinan HTML Google</small></header><iframe id="preview-frame" title="Preview hasil pencarian" sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox" referrerpolicy="no-referrer"></iframe></section>
        <section class="panel"><header class="panel-head json-head"><span>Raw JSON</span><small>AI Overview dan sponsor dikecualikan</small></header><div class="json-scroll" id="json-scroll">{json_markup}</div></section>
      </main>
      <script>
        const previewFrame = document.getElementById('preview-frame');
        previewFrame.srcdoc = {preview_json};
        const selectResult = (id, notifyPreview = false) => {{
          document.querySelectorAll('.json-hit.selected').forEach(node => node.classList.remove('selected'));
          const target = document.getElementById(`json-${{CSS.escape(id)}}`);
          if (target) {{ target.classList.add('selected'); target.scrollIntoView({{behavior: 'smooth', block: 'center'}}); }}
          if (notifyPreview) previewFrame.contentWindow.postMessage({{type: 'select-serp-result', id}}, '*');
        }};
        window.addEventListener('message', event => {{
          if (event.source !== previewFrame.contentWindow || event.data?.type !== 'serp-result-selected') return;
          selectResult(event.data.id);
        }});
        document.getElementById('json-scroll').addEventListener('click', event => {{
          const hit = event.target.closest('.json-hit'); if (hit) selectResult(hit.dataset.serpEntity, true);
        }});
        document.getElementById('json-scroll').addEventListener('keydown', event => {{
          const hit = event.target.closest('.json-hit');
          if (!hit || !['Enter', ' '].includes(event.key)) return;
          event.preventDefault(); selectResult(hit.dataset.serpEntity, true);
        }});
      </script>
    </body></html>
    """
