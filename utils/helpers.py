import re
import hashlib
import unicodedata

def calculate_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()

def normalize_ligatures(text: str) -> str:
    ligatures = {'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬀ': 'ff', 'ﬃ': 'ffi', 'ﬄ': 'ffl', 'ﬅ': 'ft', 'ﬆ': 'st'}
    for ligature, replacement in ligatures.items():
        text = text.replace(ligature, replacement)
    return text

def rejoin_hyphenated_words(text: str) -> str:
    return re.sub(r'([a-z])-\n([a-z])', r'\1\2', text)

def normalize_whitespace(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

def remove_redundant_newlines(text: str) -> str:
    return re.sub(r'\n\s*\n', '\n', text)

def normalize_unicode(text: str) -> str:
    return unicodedata.normalize('NFKC', text)

def clean_text_pipeline(text: str) -> str:
    text = normalize_ligatures(text)
    text = rejoin_hyphenated_words(text)
    text = normalize_unicode(text)
    text = remove_redundant_newlines(text)
    return text