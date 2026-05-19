from services.cache import build_cache_key


def test_cache_key_is_deterministic_and_normalized():
    key1 = build_cache_key(" What is leave policy? ", 3)
    key2 = build_cache_key("what   is leave policy?", 3)
    assert key1 == key2
    assert key1.startswith("ask_cache:dept:3:q:")
