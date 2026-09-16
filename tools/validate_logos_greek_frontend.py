from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "logos.html"
SCRIPT = ROOT / "javascript" / "logos.js"
OT_SCRIPT = ROOT / "javascript" / "logos-ot-unified-integration.js"
STYLE = ROOT / "css" / "logos-greek-integration.css"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"Missing {label}: {needle}")


def main() -> None:
    page = PAGE.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    ot_script = OT_SCRIPT.read_text(encoding="utf-8")
    style = STYLE.read_text(encoding="utf-8")

    require(page, 'data-logos-tab="interlinear"', "normal Interlinear tab")
    require(page, "logos.js?v=4", "cache-busted unified Logos script")
    require(page, "logos-ot-unified-integration.js?v=1", "unified OT frontend integration script")
    require(page, "logos-greek-integration.css?v=1", "interlinear stylesheet")
    require(page, "complete 73-book Douay-Rheims", "73-book English primary corpus wording")
    require(page, "unified Old Testament workspace", "unified OT workspace wording")
    require(page, "OSHB/WLC Hebrew-Aramaic", "Semitic production wording")
    require(page, "complete 73-book Clementine Latin Vulgate", "Latin production wording")
    require(page, "full protocanonical package", "full Septuagint package wording")
    require(page, "Verse-for-verse columns appear only where the source/Douay mapping is verified", "versification safety wording")
    require(page, "Genesis 1:1", "full OT quick-reference example")
    require(page, "Tobit 1:1", "deuterocanonical quick-reference example")

    if 'id="logosGreekNtTab"' in page:
        raise SystemExit("Redundant Greek NT tab must not be present; Interlinear is the single entry point")
    if "logos-greek-integration.js" in page:
        raise SystemExit("Legacy Greek NT tab integration script must not be loaded")
    if "logos-ot-greek-integration.js" in page:
        raise SystemExit("Legacy partial-OT Greek integration script must not be loaded after unified OT integration")

    require(script, "/api/logos/greek/catalog", "Greek NT catalog endpoint")
    require(script, "/api/logos/greek/source-rights", "Greek NT source-rights endpoint")
    require(script, "/api/logos/greek/interlinear?reference=", "Greek NT interlinear endpoint")
    require(script, "/api/logos/interlinear?reference=", "legacy OT fallback endpoint")
    require(script, "/api/logos/passage?reference=", "English DRA passage endpoint")
    require(script, "currentPassage.testament==='NT'", "automatic NT routing")
    require(script, "Primary Catholic Bible layer", "English primary-layer label")
    require(script, "['Greek','Transliteration','Lemma','POS','Morphology']", "five-column Greek NT table")
    require(script, "No English word gloss is displayed", "explicit NT no-gloss frontend rule")
    require(script, "No morphology is fabricated", "NT annotation-gap rule")
    require(script, "ShareAlike partition preserved", "NT ShareAlike frontend notice")
    require(script, "surface_and_linguistics_remain_separate", "NT licence partition contract gate")

    require(ot_script, "/api/logos/ot-interlinear/catalog", "unified OT catalog endpoint")
    require(ot_script, "/api/logos/ot-interlinear?reference=", "unified OT interlinear endpoint")
    require(ot_script, "catalog.production_enabled", "unified OT production gate")
    require(ot_script, "Number(catalog.catholic_ot_book_count)!==46", "46-book Catholic OT scope gate")
    require(ot_script, "lanes.semitic.installed", "Semitic installed gate")
    require(ot_script, "lanes.greek.installed", "Greek installed gate")
    require(ot_script, "lanes.latin.installed", "Latin installed gate")
    require(ot_script, "Hebrew / Aramaic — OSHB/WLC", "Semitic lane label")
    require(ot_script, "Septuagint — Swete", "Septuagint lane label")
    require(ot_script, "Clementine Latin Vulgate", "Latin lane label")
    require(ot_script, "mapping-required", "explicit mapping-required state")
    require(ot_script, "Logos does not manufacture a verse equivalence", "no manufactured mapping disclosure")
    require(ot_script, "['Verse','verse']", "verse column in unified table")
    require(ot_script, "['Douay-Rheims 1899','en']", "English unified table column")
    require(ot_script, "['Hebrew / Aramaic','sem']", "Semitic unified table column")
    require(ot_script, "['Septuagint Greek','grc']", "Greek unified table column")
    require(ot_script, "['Clementine Latin','lat']", "Latin unified table column")
    require(ot_script, "grc.label||(witness&&witness.name)||'Septuagint — Swete'", "Greek witness-aware rendering")
    require(ot_script, "data.alignment&&data.alignment.exact===true", "verified mapping gate")
    require(ot_script, "mapping.exact_verse_alignment===true", "accepted deuterocanonical exact-mapping gate")
    require(ot_script, "No unavailable Greek linguistic annotation is invented", "OT Greek derived-layer boundary")
    require(ot_script, "No Latin lemma, morphology, gloss or transliteration is fabricated", "Latin derived-layer boundary")

    if "['Greek','Transliteration','Lemma','POS','Morphology','Gloss']" in script:
        raise SystemExit("Greek NT production table must not expose an unapproved Gloss column")
    if "['Greek','Transliteration','Lemma','POS','Morphology']" in ot_script:
        raise SystemExit("Unified OT frontend must not imply unavailable Greek linguistic annotations")
    if not style.strip():
        raise SystemExit("Interlinear stylesheet is empty")

    print("Logos unified Interlinear + Greek NT + four-lane OT frontend contract: OK")


if __name__ == "__main__":
    main()
