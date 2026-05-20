from utils.parsers import remove_headers_footers


def test_remove_headers_footers_strips_common_footer_lines():
    pages = [
        "Company Header\nPolicy content page one\nConfidential\n",
        "Company Header\nPolicy content page two\nConfidential\n",
        "Company Header\nPolicy content page three\nConfidential\n",
        "Company Header\nPolicy content page four\nConfidential\n",
        "Company Header\nPolicy content page five\nConfidential\n",
    ]

    cleaned_pages, doc_context = remove_headers_footers(pages)

    assert "Company Header" in doc_context
    assert all("Confidential" not in page for page in cleaned_pages)
    assert "Policy content page one" in cleaned_pages[0]
    assert "Policy content page two" in cleaned_pages[1]
    assert "Policy content page three" in cleaned_pages[2]
