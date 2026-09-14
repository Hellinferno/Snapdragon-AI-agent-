import pytest

from app.services.lexical_index import BM25Index, tokenize


def _index():
    return BM25Index([
        ("c1", "d1", "CRISP-DM is the Cross Industry Standard Process for Data Mining."),
        ("c2", "d1", "Data data data mining of customer data at scale."),
        ("c3", "d2", "Cross-validation splits a labeled dataset into k folds."),
    ])


def test_tokenize_drops_stopwords_splits_hyphens_and_folds_plurals():
    assert tokenize("What does CRISP-DM stand for?") == ["crisp", "dm", "stand"]
    assert tokenize("folds fold studies class") == ["fold", "fold", "study", "class"]


def test_rare_terms_outrank_frequent_terms():
    results = _index().search("What does CRISP-DM stand for?", limit=3)
    assert results[0][0] == "c1"
    assert all(0.0 <= coverage <= 1.0 for _, _, coverage in results)


def test_plural_query_matches_singular_text_and_document_filter_applies():
    index = _index()
    assert index.search("How many folds?", limit=3)[0][0] == "c3"
    assert index.search("How many folds?", limit=3, document_ids=["d1"]) == []


def test_unrelated_query_has_no_lexical_candidates():
    assert _index().search("recipe for baking chocolate brownies", limit=3) == []


def test_coverage_reflects_share_of_query_matched():
    index = _index()
    full = dict((cid, cov) for cid, _, cov in index.search("cross industry standard process", limit=3))
    partial = dict((cid, cov) for cid, _, cov in index.search("cross industry standard process brownies", limit=3))
    assert partial["c1"] < full["c1"]

