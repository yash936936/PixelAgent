from src.brain.semantic_matcher import SemanticMatcher, _cosine, _ngrams


def test_ngrams_empty_text_returns_empty_counter():
    assert _ngrams("") == {}
    assert _ngrams("   ") == {}


def test_ngrams_normalizes_whitespace_and_case():
    assert _ngrams("Hello   World", n=3) == _ngrams("hello world", n=3)


def test_cosine_identical_vectors_is_one():
    vec = _ngrams("delete this account forever")
    assert _cosine(vec, vec) == 1.0


def test_cosine_empty_vector_is_zero():
    vec = _ngrams("delete this account forever")
    assert _cosine(vec, {}) == 0.0
    assert _cosine({}, vec) == 0.0


def test_cosine_unrelated_text_scores_low():
    a = _ngrams("delete this account forever")
    b = _ngrams("what is the weather today")
    assert _cosine(a, b) < 0.2


def test_semantic_matcher_finds_best_label_for_close_paraphrase():
    matcher = SemanticMatcher(
        exemplars={
            "destructive": ["get rid of this permanently", "erase this completely"],
            "external": ["share this with everyone", "send this to the team"],
        }
    )
    result = matcher.best_match("please get rid of this file permanently")
    assert result.label == "destructive"
    assert result.score > 0.5


def test_semantic_matcher_no_match_returns_none_label():
    matcher = SemanticMatcher(exemplars={})
    result = matcher.best_match("anything at all")
    assert result.label is None
    assert result.score == 0.0


def test_semantic_matcher_empty_query_scores_zero():
    matcher = SemanticMatcher(exemplars={"destructive": ["erase this completely"]})
    result = matcher.best_match("")
    assert result.score == 0.0
