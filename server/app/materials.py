"""Text extraction and grounded retrieval; reuse pypdf, jieba and rank-bm25."""
import re
from bisect import bisect_right
from pathlib import Path
import jieba
from pypdf import PdfReader
from rank_bm25 import BM25Okapi
from .domain import AppError

jieba.setLogLevel(40)


def parse_pdf(path: Path, document_id: str):
    try:
        reader = PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(""):
            raise AppError("这份 PDF 需要密码，请先解锁后上传", "PDF_ENCRYPTED")
        if len(reader.pages) > 600:
            raise AppError("首版支持最多 600 页的 PDF，请拆分后导入", "PDF_TOO_LARGE")
        outline = []

        def walk(items, depth=0):
            for item in items:
                if isinstance(item, list):
                    walk(item, depth + 1)
                else:
                    try:
                        page = reader.get_destination_page_number(item)
                        if page is not None and 0 <= page < len(reader.pages):
                            outline.append({"title": str(item.title).strip(), "page": page, "depth": depth})
                    except (ValueError, TypeError, KeyError, AttributeError):
                        continue

        walk(reader.outline)
        outline.sort(key=lambda x: x["page"])
        chunks, missing, warnings = [], [], []
        starts = [h["page"] for h in outline]
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
                warnings.append(f"文件第 {i + 1} 页提取失败")
            text = text.replace("\x00", "").strip()
            if len(text) < 30:
                missing.append(i + 1)
                continue
            index = bisect_right(starts, i) - 1
            title = outline[index]["title"] if index >= 0 else f"第 {i + 1} 页"
            # Keep each chunk within a physical page: exact page citations remain stable.
            for j, start in enumerate(range(0, len(text), 1000)):
                snippet = text[start:start + 1000]
                if snippet.strip():
                    chunks.append({"id": f"{document_id}_p{i}_c{j}", "page": i, "title": title, "text": snippet})
        if not chunks:
            raise AppError("未提取到可读文本。这可能是扫描版 PDF，首版尚未接入 OCR。", "NO_TEXT")
        title = str(reader.metadata.title or path.stem) if reader.metadata else path.stem
        return {"title": title, "pages": len(reader.pages), "outline": outline, "missing_pages": missing, "warnings": warnings}, chunks
    except AppError:
        raise
    except Exception as exc:
        raise AppError("无法解析这份 PDF，请检查文件是否完整", "PDF_INVALID") from exc


def build_units(document, chunks, course_id):
    headings = [h for h in document["outline"] if h["depth"] <= 1]
    if not headings:
        # A navigable fallback, labelled as page groups rather than fabricated chapter titles.
        headings = [{"title": f"第 {p + 1}–{min(p + 4, document['pages'])} 页", "page": p, "depth": 0} for p in range(0, document["pages"], 4)]
    units, chapter, chapter_title = [], 0, "开始学习"
    for i, heading in enumerate(headings):
        if heading["depth"] == 0:
            chapter += 1
            chapter_title = heading["title"]
        start = heading["page"]
        end = headings[i + 1]["page"] if i + 1 < len(headings) else document["pages"]
        if end == start and heading["depth"] == 0:
            continue
        source_ids = [c["id"] for c in chunks if start <= c["page"] < max(start + 1, end)]
        if not source_ids:
            continue
        units.append({"id": f"{course_id}_u{len(units)}", "title": heading["title"], "chapter": max(chapter, 1),
                      "chapter_title": chapter_title, "source_ids": source_ids, "page_start": start + 1,
                      "page_end": max(start + 1, end), "minutes": 10})
    return units


def tokenize(text):
    return [t.lower() for t in jieba.lcut(text) if re.search(r"[\w\u4e00-\u9fff]", t)]


def retrieve(chunks, query, preferred_ids=(), limit=6):
    if not chunks:
        return []
    tokens = [tokenize(c["text"]) or ["_"] for c in chunks]
    scores = BM25Okapi(tokens).get_scores(tokenize(query) or ["_"])
    preferred = set(preferred_ids)
    ranked = sorted(range(len(chunks)), key=lambda i: float(scores[i]) + (1.5 if chunks[i]["id"] in preferred else 0), reverse=True)
    return [chunks[i] for i in ranked[:limit]]
