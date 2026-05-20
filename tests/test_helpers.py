from utils.helpers import clean_text_pipeline, normalize_whitespace


def test_clean_text_pipeline_normalizes_text():
    raw = "office \n\n poli-\ncy and ligature text"
    cleaned = clean_text_pipeline(raw)
    normalized = normalize_whitespace(cleaned)
    assert "policy" in normalized
    assert "ligature text" in normalized


def test_normalize_whitespace_collapses_spaces():
    assert normalize_whitespace("a   b\n\n c") == "a b c"
