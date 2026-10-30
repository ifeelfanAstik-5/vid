import os
from pypdf import PdfReader
from docx import Document
import chardet
from app.pipeline.state import PipelineState


def run(state: PipelineState) -> dict:
    """Parse input file into raw_text. Supports PDF, DOCX, TXT."""
    path = state["input_file_path"]
    fmt = state.get("input_format", "").lower()

    if not fmt:
        fmt = path.rsplit(".", 1)[-1].lower()

    print(f"[DocumentIngestor] Parsing {fmt.upper()} file from {path}...")

    if fmt == "pdf":
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif fmt == "docx":
        doc = Document(path)
        text = "\n".join(p.text for p in doc.paragraphs)
    else:  # txt fallback
        with open(path, "rb") as f:
            raw = f.read()
        detected = chardet.detect(raw)
        enc = detected.get("encoding") or "utf-8"
        text = raw.decode(enc, errors="replace")

    cleaned = text.strip()
    print(f"[DocumentIngestor] Ingested {len(cleaned)} characters of text.")
    return {"raw_text": cleaned}
