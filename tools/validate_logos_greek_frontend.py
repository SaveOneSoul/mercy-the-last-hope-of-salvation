from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "logos.html"
SCRIPT = ROOT / "javascript" / "logos.js"
OT_SCRIPT = ROOT / "javascript" / "logos-ot-greek-integration.js"
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
    require(page, "logos-ot-greek-integration.js?v=1", "OT Greek frontend integration script")
    require(page, "logos-greek-integration.css?v=1", "Greek interlinear stylesheet")
    require(page, "complete 73-book Douay-Rheims", "73-book English primary corpus wording")
    require(page, "production Greek NT layer for all 27 New Testament books", "automatic NT interlinear wording")
    require(page, "accepted Catholic OT Greek production scope", "OT Greek production-scope wording")
    require(page, "Tobit 1:1", "OT Greek quick-reference example")
    require(page, "no OT gloss, lemma, morphology or transliteration is displayed", "OT derived-layer boundary wording")

    if 'id="logosGreekNtTab"' in page:
        raise SystemExit("Redundant Greek NT tab must not be present; Interlinear is the single entry point")
    if "logos-greek-integration.js" in page:
        raise SystemExit("Legacy Greek NT tab integration script must not be loaded")

    require(script, "/api/logos/greek/catalog", "Greek NT catalog endpoint")
    require(script, "/api/logos/greek/source-rights", "Greek NT source-rights endpoint")
    require(script, "/api/logos/greek/interlinear?reference=", "Greek NT interlinear endpoint")
    require(script, "/api/logos/interlinear?reference=", "legacy/unsupported-OT interlinear endpoint")
    require(script, "/api/logos/passage?reference=", "English DRA passage endpoint")
    require(script, "currentPassage.testament==='NT'", "automatic NT routing")
    require(script, "Primary Catholic Bible layer", "English primary-layer label")
    require(script, "['Greek','Transliteration','Lemma','POS','Morphology']", "five-column Greek NT table")
    require(script, "No English word gloss is displayed", "explicit NT no-gloss frontend rule")
    require(script, "No morphology is fabricated", "NT annotation-gap rule")
    require(script, "ShareAlike partition preserved", "NT ShareAlike frontend notice")
    require(script, "Original-language Old Testament corpus not installed yet", "unsupported OT fallback explanation")
    require(script, "surface_and_linguistics_remain_separate", "NT licence partition contract gate")

    require(ot_script, "/api/logos/ot-greek/catalog", "OT Greek catalog endpoint")
    require(ot_script, "/api/logos/ot-greek/source-rights", "OT Greek source-rights endpoint")
    require(ot_script, "/api/logos/ot-greek/interlinear?reference=", "OT Greek interlinear endpoint")
    require(ot_script, "grc_ot_catholic_swete", "accepted OT Greek corpus id")
    require(ot_script, "Number(catalog.witness_count)!==15", "accepted OT witness-count gate")
    require(ot_script, "Number(catalog.source_verse_record_count)!==5337", "accepted OT source-record gate")
    require(ot_script, "rights.partition.license!=='CC BY-SA 4.0'", "OT Greek licence gate")
    require(ot_script, "rights.partition.share_alike!==true", "OT ShareAlike gate")
    require(ot_script, "rights.partition.isolation_required!==true", "OT isolation gate")
    require(ot_script, "layers.glosses!==false", "OT gloss absence gate")
    require(ot_script, "layers.lemmata!==false", "OT lemma absence gate")
    require(ot_script, "layers.morphology!==false", "OT morphology absence gate")
    require(ot_script, "layers.transliteration!==false", "OT transliteration absence gate")
    require(ot_script, "['Source reference','Greek source surface']", "OT source-surface table")
    require(ot_script, "Component-range mapping · source boundaries preserved", "OT component-range disclosure")
    require(ot_script, "parallel witness is preserved", "OT parallel-witness disclosure")
    require(ot_script, "does not replace the primary Douay-Rheims English text", "English primary-layer boundary")

    if "['Greek','Transliteration','Lemma','POS','Morphology','Gloss']" in script:
        raise SystemExit("Greek NT production table must not expose an unapproved Gloss column")
    if "['Greek','Transliteration','Lemma','POS','Morphology']" in ot_script:
        raise SystemExit("OT Greek frontend must not imply unavailable linguistic annotations")
    if not style.strip():
        raise SystemExit("Greek interlinear stylesheet is empty")

    print("Logos unified Interlinear + Greek NT + accepted OT Greek frontend contract: OK")


if __name__ == "__main__":
    main()
