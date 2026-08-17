from app.reference_service import retrieve_references

def test_eucharist_reference_contains_ccc_and_scripture():
    refs = retrieve_references("What does the Catholic Church teach about the Eucharist?")
    assert refs
    top = refs[0]
    assert "1322" in top["ccc"]
    assert any("John 6" in v for v in top["scripture"])

def test_confession_reference():
    refs = retrieve_references("Why confess sins to a priest?")
    assert any(r["id"] == "REF_PENANCE" for r in refs)
