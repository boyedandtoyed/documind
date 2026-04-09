from documind.chunker import chunk_text, sliding_window_chunks, clean_text

def test_clean_text():
    assert clean_text("  hello   world  ") == "hello world"
    assert clean_text("line\x00break") == "linebreak"

def test_chunk_text_basic():
    text = " ".join([f"word{i}" for i in range(100)])
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    assert len(chunks) > 1
    assert all(len(c.text.split()) <= 20 for c in chunks)

def test_chunk_overlap():
    text = " ".join([f"w{i}" for i in range(50)])
    chunks = chunk_text(text, chunk_size=10, overlap=3)
    # With overlap, chunks should share some words
    if len(chunks) >= 2:
        words0 = set(chunks[0].text.split())
        words1 = set(chunks[1].text.split())
        assert len(words0 & words1) > 0

def test_empty_text():
    chunks = chunk_text("", chunk_size=100, overlap=10)
    assert chunks == []
