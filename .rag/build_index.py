
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a lightweight RAG index from Markdown sources.

Outputs (in .rag/):
  - chunks.jsonl     : {"id","path","title","heading","start","end","text"}
  - keywords.jsonl   : {"id","keywords":[...]}
  - neighbors.jsonl  : {"id","neighbors":[[id,score], ...]}  # score ~ similarity
  - toc.json         : [{"path","level","title","anchor"}]

Usage:
  python build_index.py \
    --input-dir book \
    --out-dir .rag \
    --chunk-size 1000 \
    --chunk-overlap 120 \
    --keywords-per-chunk 10 \
    --knn 5
"""

from __future__ import annotations
import argparse
import json
import jsonlines
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Optional deps
_HAVE_SENTENCE_TRANSFORMERS = False
_HAVE_FAISS = False
try:
    from sentence_transformers import SentenceTransformer
    _HAVE_SENTENCE_TRANSFORMERS = True
except Exception:
    pass

try:
    import faiss  # type: ignore
    _HAVE_FAISS = True
except Exception:
    pass

# Required deps
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors


HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*$")
CODE_FENCE_RE = re.compile(r"^```")


def read_markdown(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def strip_front_matter(text: str) -> str:
    # Remove leading YAML front matter if present
    if text.startswith("---"):
        parts = text.split("\n")
        if len(parts) > 2:
            try:
                end = parts[1:].index("---") + 1
                return "\n".join(parts[end + 1 :])
            except ValueError:
                return text
    return text


def split_paragraphs_preserving(text: str) -> List[str]:
    """Split by blank lines, ignoring fenced code blocks."""
    lines = text.splitlines()
    paras: List[str] = []
    buf: List[str] = []
    in_fence = False
    for ln in lines:
        if CODE_FENCE_RE.match(ln.strip()):
            in_fence = not in_fence
            buf.append(ln)
            continue
        if not in_fence and not ln.strip():
            if buf:
                paras.append("\n".join(buf).strip())
                buf = []
        else:
            buf.append(ln)
    if buf:
        paras.append("\n".join(buf).strip())
    return [p for p in paras if p]


def slugify(title: str) -> str:
    s = title.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s


def parse_headings(text: str) -> List[Tuple[int, str]]:
    """Return list of (level, title) as they appear."""
    headings = []
    in_fence = False
    for ln in text.splitlines():
        if CODE_FENCE_RE.match(ln.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(ln)
        if m:
            level = len(m.group("hashes"))
            title = m.group("title").strip()
            headings.append((level, title))
    return headings


def chunk_markdown(path: Path, text: str, chunk_size: int, overlap: int) -> Tuple[List[Dict], List[Dict]]:
    """
    Produce chunks and toc entries.
    Chunking strategy:
      - collect under most recent heading
      - accumulate paragraphs until ~chunk_size chars, then roll with overlap
    """
    stripped = strip_front_matter(text)
    paras = split_paragraphs_preserving(stripped)

    # Track current heading stack for context
    chunks: List[Dict] = []
    toc: List[Dict] = []

    # Build TOC first (simple)
    for level, title in parse_headings(stripped):
        toc.append({
            "path": str(path).replace("\\", "/"),
            "level": level,
            "title": title,
            "anchor": slugify(title),
        })

    # Pre-calculate heading positions for better context assignment
    headings_positions = []
    pos = 0
    lines = stripped.splitlines()
    for ln in lines:
        m = HEADING_RE.match(ln)
        if m:
            headings_positions.append((pos, len(m.group("hashes")), m.group("title").strip()))
        pos += len(ln) + 1

    # Compute paragraph string positions
    par_positions = []
    pos = 0
    for p in paras:
        idx = stripped.find(p, pos)
        if idx == -1:
            idx = pos
        par_positions.append(idx)
        pos = idx + len(p)

    frames = []
    for idx, p in zip(par_positions, paras):
        # find last heading position <= idx
        context_title = ""
        prev = [h for h in headings_positions if h[0] <= idx]
        if prev:
            context_title = prev[-1][2]
        frames.append((context_title, p))

    # Now roll into chunks
    cur_text = ""
    cur_heading = ""
    start_char = 0
    acc_len = 0
    chunk_idx = 0

    def flush_chunk(text_acc: str, heading_acc: str, start: int, end: int):
        nonlocal chunk_idx
        if not text_acc.strip():
            return
        chunk_id = f"{str(path).replace('\\\\', '/')}:chunk-{chunk_idx:04d}"
        chunks.append({
            "id": chunk_id,
            "path": str(path).replace("\\", "/"),
            "title": Path(path).stem,
            "heading": heading_acc or "",
            "start": start,
            "end": end,
            "text": text_acc.strip(),
        })
        chunk_idx += 1

    for ctx_title, para in frames:
        para_text = para.strip()
        if not para_text:
            continue
        if not cur_text:
            cur_heading = ctx_title
            start_char = acc_len
        if len(cur_text) + 2 + len(para_text) <= chunk_size:
            cur_text = (cur_text + "\n\n" + para_text) if cur_text else para_text
        else:
            flush_chunk(cur_text, cur_heading, start_char, start_char + len(cur_text))
            if overlap > 0 and len(cur_text) > overlap:
                tail = cur_text[-overlap:]
                cur_text = tail + "\n\n" + para_text
                start_char = start_char + len(cur_text) - len(tail) - len(para_text) - 2
            else:
                cur_text = para_text
                start_char = start_char + len(cur_text)
            cur_heading = ctx_title
        acc_len += len(para_text) + 2

    flush_chunk(cur_text, cur_heading, start_char, start_char + len(cur_text))
    return chunks, toc


def build_keywords(chunks: List[Dict], topk: int) -> List[Tuple[str, List[str]]]:
    docs = [c["text"] for c in chunks]
    if not docs:
        return []
    vec = TfidfVectorizer(
        strip_accents="unicode",
        lowercase=True,
        stop_words="english",
        max_features=50000,
    )
    X = vec.fit_transform(docs)
    vocab = vec.get_feature_names_out()
    results: List[Tuple[str, List[str]]] = []
    for i in range(X.shape[0]):
        row = X.getrow(i)
        if row.nnz == 0:
            results.append((chunks[i]["id"], []))
            continue
        idxs = row.data.argsort()[::-1][:topk]
        terms = [vocab[row.indices[j]] for j in idxs]
        results.append((chunks[i]["id"], terms))
    return results


def build_neighbors(chunks: List[Dict], k: int) -> Dict[str, List[Tuple[str, float]]]:
    texts = [c["text"] for c in chunks]
    ids = [c["id"] for c in chunks]
    if not texts:
        return {}
    if _HAVE_SENTENCE_TRANSFORMERS:
        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        import numpy as np
        embs = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        dim = embs.shape[1]

        def topk_faiss(vectors: "np.ndarray", kk: int) -> List[List[Tuple[int, float]]]:
            if _HAVE_FAISS:
                index = faiss.IndexFlatIP(dim)
                index.add(vectors)
                D, I = index.search(vectors, kk + 1)
                res = []
                for i in range(vectors.shape[0]):
                    neigh = []
                    for j, score in zip(I[i], D[i]):
                        if j == i or j < 0:
                            continue
                        neigh.append((j, float(score)))
                        if len(neigh) >= kk:
                            break
                    res.append(neigh)
                return res
            else:
                nn = NearestNeighbors(n_neighbors=min(kk + 1, len(texts)), metric="cosine", algorithm="auto")
                nn.fit(embs)
                dists, idxs = nn.kneighbors(embs)
                res = []
                for i in range(len(texts)):
                    neigh = []
                    for j, dist in zip(idxs[i], dists[i]):
                        if j == i:
                            continue
                        score = 1.0 - float(dist)
                        neigh.append((j, score))
                        if len(neigh) >= kk:
                            break
                    res.append(neigh)
                return res

        neigh_idxs = topk_faiss(embs, k)
        out: Dict[str, List[Tuple[str, float]]] = {}
        for i, neigh in enumerate(neigh_idxs):
            out[ids[i]] = [(ids[j], float(score)) for j, score in neigh]
        return out

    # TF-IDF fallback
    vec = TfidfVectorizer(strip_accents="unicode", lowercase=True, stop_words="english")
    X = vec.fit_transform(texts)
    nn = NearestNeighbors(n_neighbors=min(k + 1, len(texts)), metric="cosine", algorithm="auto")
    nn.fit(X)
    dists, idxs = nn.kneighbors(X)
    out: Dict[str, List[Tuple[str, float]]] = {}
    for i, (row_idx, row_dist) in enumerate(zip(idxs, dists)):
        neigh = []
        for j, dist in zip(row_idx, row_dist):
            if j == i:
                continue
            score = 1.0 - float(dist)
            neigh.append((ids[j], score))
            if len(neigh) >= k:
                break
        out[ids[i]] = neigh
    return out


def write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with jsonlines.open(path, mode="w") as w:
        for r in rows:
            w.write(r)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default="book", help="Root directory with Markdown files")
    ap.add_argument("--out-dir", default=".rag", help="Output directory for index files")
    ap.add_argument("--chunk-size", type=int, default=1000, help="Approx. characters per chunk")
    ap.add_argument("--chunk-overlap", type=int, default=120, help="Characters overlap between chunks")
    ap.add_argument("--keywords-per-chunk", type=int, default=10)
    ap.add_argument("--knn", type=int, default=5, help="Neighbors per chunk")
    args = ap.parse_args()

    input_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_files = sorted(input_dir.glob("**/*.md"))
    if not md_files:
        print(f"[build_index] No markdown files found under: {input_dir}", file=sys.stderr)
        sys.exit(0)

    all_chunks: List[Dict] = []
    full_toc: List[Dict] = []
    for p in md_files:
        txt = read_markdown(p)
        chunks, toc = chunk_markdown(p, txt, args.chunk_size, args.chunk_overlap)
        all_chunks.extend(chunks)
        full_toc.extend(toc)

    write_jsonl(out_dir / "chunks.jsonl", all_chunks)
    write_json(out_dir / "toc.json", full_toc)

    kw = build_keywords(all_chunks, args.keywords_per_chunk)
    write_jsonl(out_dir / "keywords.jsonl", [{"id": cid, "keywords": terms} for cid, terms in kw])

    neigh = build_neighbors(all_chunks, args.knn)
    rows = [{"id": cid, "neighbors": neigh.get(cid, [])} for cid in [c["id"] for c in all_chunks]]
    write_jsonl(out_dir / "neighbors.jsonl", rows)

    print(f"[build_index] Done. Wrote {len(all_chunks)} chunks | {len(full_toc)} toc entries")
    print(f"[build_index] Artifacts in: {out_dir}/ (chunks.jsonl, keywords.jsonl, neighbors.jsonl, toc.json)")


if __name__ == "__main__":
    main()
