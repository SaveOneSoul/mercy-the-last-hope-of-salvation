from app.knowledge import retrieve


def test_eucharist_retrieval():
    ids = {x["id"] for x in retrieve("What is transubstantiation in the Eucharist?")}
    assert "CCC_EUCHARIST" in ids


def test_baptism_in_spirit_retrieval():
    ids = {x["id"] for x in retrieve("Is Baptism in the Holy Spirit another sacrament?")}
    assert "CHARIS_BHS" in ids
