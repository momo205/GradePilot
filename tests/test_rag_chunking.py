from __future__ import annotations

from app.services.rag.chunking import chunk_text


def test_chunk_text_deterministic() -> None:
    text = "Para1 line1\n\nPara2 line1\n\nPara3 line1"
    a = chunk_text(raw_text=text, max_chars=250, overlap_chars=50)
    b = chunk_text(raw_text=text, max_chars=250, overlap_chars=50)
    assert [c.text for c in a] == [c.text for c in b]


def test_chunk_text_overlap_nonempty() -> None:
    text = "A" * 300 + "\n\n" + "B" * 300 + "\n\n" + "C" * 300
    chunks = chunk_text(raw_text=text, max_chars=400, overlap_chars=50)
    assert len(chunks) >= 2
    # Ensure overlap is present at chunk boundaries (best-effort check).
    assert chunks[0].text[-20:] in chunks[1].text
