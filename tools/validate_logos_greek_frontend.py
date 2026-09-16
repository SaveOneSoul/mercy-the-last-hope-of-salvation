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
    require(page, "logos.js?v=4", "cache-busted main Logos script")
    require(page, "logos-ot-unified-integration.js?v=1", "unified OT frontend controller")
    require(page, "logos-greek-integration.css?v=1", "interlinear stylesheet")
    require(page, "complete 73-book Douay-Rheims", "73-book English primary corpus wording")
    require(page, "WLC/OSHB Hebrew-Aramaic", "OT Semitic wording")
    require(page, "Swete Septuagint Greek", "Septuagint wording")
    require(page, "Clementine Latin Vulgate", "Vulgate wording")
    require(page, "Genesis 1", "Genesis quick-reference example")
    require(page, "Isaiah 53", "Isaiah quick-reference example")
    require(page, "No missing gloss, transliteration, lemma or morphology layer is fabricated", "derived-layer boundary wording")

    if 'id="logosGreekNtTab"' in page:
        raise SystemExit("Redundant Greek NT tab must not be present")
    if "logos-greek-integration.js" in page:
        raise SystemExit("Legacy Greek NT tab integration script must not be loaded")
    if "logos-ot-greek-integration.js" in page:
        raise SystemExit("Legacy OT-Greek-only frontend script must not be loaded")

    # Existing normal Interlinear keeps the complete production Greek NT path.
    require(script, "/api/logos/greek/catalog", "Greek NT catalog endpoint")
    require(script, "/api/logos/greek/source-rights", "Greek NT source-rights endpoint")
    require(script, "/api/logos/greek/interlinear?reference=", "Greek NT interlinear endpoint")
    require(script, "/api/logos/passage?reference=", "English DRA passage endpoint")
    require(script, "currentPassage.testament==='NT'", "automatic NT routing")
    require(script, "Primary Catholic Bible layer", "English primary-layer label")
    require(script, "['Greek','Transliteration','Lemma','POS','Morphology']", "five-column Greek NT table")
    require(script, "No morphology is fabricated", "NT annotation-gap rule")
    require(script, "ShareAlike partition preserved", "NT ShareAlike notice")

    # Unified OT controller must independently gate every source corpus.
    require(ot_script, "/api/logos/ot-semitic/catalog", "OT Semitic catalog")
    require(ot_script, "/api/logos/ot-semitic/source-rights", "OT Semitic source rights")
    require(ot_script, "/api/logos/ot-semitic/interlinear?reference=", "OT Semitic interlinear")
    require(ot_script, "heb_arc_oshb_wlc", "OT Semitic corpus id")
    require(ot_script, "Number(sc.data.book_count)===39", "39-book Semitic gate")
    require(ot_script, "WLC surface · Public Domain; OSHB linguistic annotations · CC BY 4.0", "Semitic rights disclosure")
    require(ot_script, "['Verse','Hebrew / Aramaic','Lemma','Morphology','Language']", "Semitic table contract")
    if "Transliteration" in ot_script.split("function renderSemitic", 1)[1].split("function renderSeptuagintWitness", 1)[0]:
        raise SystemExit("Semitic table must not expose an unapproved transliteration column")
    if "Gloss" in ot_script.split("function renderSemitic", 1)[1].split("function renderSeptuagintWitness", 1)[0]:
        raise SystemExit("Semitic table must not expose an unapproved gloss column")

    require(ot_script, "/api/logos/ot-septuagint/catalog", "full Septuagint catalog")
    require(ot_script, "/api/logos/ot-septuagint/source-rights", "full Septuagint source rights")
    require(ot_script, "/api/logos/ot-septuagint/interlinear?reference=", "full Septuagint interlinear")
    require(ot_script, "grc_ot_swete_protocanonical", "protocanonical Septuagint corpus id")
    require(ot_script, "Number(gc.data.book_count)===37", "37-book Septuagint complement gate")
    require(ot_script, "gr.data.partition.license==='CC BY-SA 4.0'", "Septuagint ShareAlike license gate")

    require(ot_script, "/api/logos/ot-greek/catalog", "accepted deuterocanonical Greek catalog")
    require(ot_script, "/api/logos/ot-greek/interlinear?reference=", "accepted deuterocanonical Greek interlinear")
    require(ot_script, "grc_ot_catholic_swete", "accepted OT Greek corpus id")
    require(ot_script, "Number(dc.data.witness_count)===15", "accepted OT Greek witness gate")
    require(ot_script, "parallel witness", "Daniel/parallel witness disclosure")

    require(ot_script, "/api/logos/vulgate/catalog", "Vulgate catalog")
    require(ot_script, "/api/logos/vulgate/source-rights", "Vulgate source rights")
    require(ot_script, "/api/logos/vulgate/interlinear?reference=", "Vulgate interlinear")
    require(ot_script, "lat_clementine_vulgate", "Vulgate corpus id")
    require(ot_script, "Number(vc.data.book_count)===73", "73-book Vulgate gate")
    require(ot_script, "vr.data.source.rights==='Public Domain'", "Vulgate public-domain gate")
    require(ot_script, "['Verse','Latin source surface']", "Latin table contract")

    require(ot_script, "mapping_required", "versification mapping disclosure")
    require(ot_script, "blocked rather than silently renumbered", "no silent renumbering wording")
    require(ot_script, "Douay-Rheims remains the primary Catholic Bible text", "primary English boundary")

    if "['Greek','Transliteration','Lemma','POS','Morphology','Gloss']" in script:
        raise SystemExit("Greek NT production table must not expose an unapproved Gloss column")
    if not style.strip():
        raise SystemExit("Interlinear stylesheet is empty")

    print("Logos unified Interlinear: English + NT Greek + OT Hebrew/Aramaic + Septuagint + Vulgate contract: OK")


if __name__ == "__main__":
    main()
