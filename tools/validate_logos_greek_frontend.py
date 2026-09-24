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
    require(page, "logos-share-art.js?v=1", "curated Catholic illustration script")
    require(page, "logos.js?v=12", "cache-busted unified Logos script")
    require(page, "logos-ot-unified-integration.js?v=6", "cache-busted unified OT recovery script")
    require(page, "logos-greek-integration.css?v=4", "semantic interlinear stylesheet")
    require(page, "complete 73-book Douay-Rheims", "73-book English primary corpus wording")
    require(page, "unified Old Testament workspace", "unified OT workspace wording")
    require(page, "OSHB/WLC Hebrew-Aramaic", "Semitic production wording")
    require(page, "complete 73-book Clementine Latin Vulgate", "Latin production wording")
    require(page, "38 pinned First1K/Swete book scopes", "38-book First1K/Swete wording")
    require(page, "Greek Wikisource Ecclesiastes witness", "explicit Ecclesiastes fallback wording")
    require(page, "First1K has no Greek text blob", "First1K Ecclesiastes gap wording")
    require(page, "Verse-for-verse columns appear only where the source/Douay mapping is verified", "versification safety wording")
    require(page, "Genesis 1:1", "full OT quick-reference example")
    require(page, "Ecclesiastes 1:1", "Ecclesiastes fallback quick-reference example")
    require(page, "Tobit 1:1", "deuterocanonical quick-reference example")
    require(page, "Deuteronomy 6:4", "Hebrew semantic acceptance example")
    require(page, "John 21:19", "Greek semantic acceptance example")
    require(page, "full original-language word study", "semantic interlinear page wording")
    require(script, "renderVersePicker()", "chapter verse picker")
    require(script, "Love in John 21:15–17", "contextual love note")
    require(page, 'data-logos-view="bible"', "Bible-first primary navigation")
    require(page, 'data-logos-view="search"', "Bible search primary navigation")
    require(page, 'data-logos-view="study"', "advanced Study primary navigation")
    require(page, 'data-logos-view="saved"', "Saved primary navigation")
    require(page, 'data-logos-view="more"', "More primary navigation")
    require(page, 'data-testament="OT"', "Old Testament reader selector")
    require(page, 'data-testament="NT"', "New Testament reader selector")
    require(page, 'id="logosBookBrowser"', "book browser")
    require(page, 'id="logosChapterGrid"', "chapter grid")
    require(page, 'id="logosReaderVerses"', "chapter reader")
    require(page, 'id="logosVerseSheet"', "verse action sheet")

    if 'id="logosGreekNtTab"' in page:
        raise SystemExit("Redundant Greek NT tab must not be present; Interlinear is the single entry point")
    if "logos-greek-integration.js" in page:
        raise SystemExit("Legacy Greek NT tab integration script must not be loaded")
    if "logos-ot-greek-integration.js" in page:
        raise SystemExit("Legacy partial-OT Greek integration script must not be loaded after unified OT integration")
    if "Swete Septuagint Greek across the Catholic OT" in page:
        raise SystemExit("Page must not imply that Ecclesiastes is a Swete witness")

    require(script, "/api/logos/greek/catalog", "Greek NT catalog endpoint")
    require(script, "/api/logos/greek/source-rights", "Greek NT source-rights endpoint")
    require(script, "/api/logos/greek/interlinear?reference=", "Greek NT interlinear endpoint")
    require(script, "/api/logos/interlinear?reference=", "legacy OT fallback endpoint")
    require(script, "/api/logos/passage?reference=", "English DRA passage endpoint")
    require(script, "/api/logos/search?q=", "read-only Bible search endpoint")
    require(script, "BOOKMARKS_KEY='logos:bookmarks:v1'", "browser-local bookmark store")
    require(script, "LAST_READING_KEY='logos:last-reading:v1'", "browser-local continue-reading store")
    require(script, "switchLogosView('study')", "verse-to-advanced-study handoff")
    require(script, "openReaderChapter(book", "chapter reader routing")
    require(script, "currentPassage.testament==='NT'", "automatic NT routing")
    require(script, "Primary Catholic Bible layer", "English primary-layer label")
    require(script, "['Greek','Transliteration','Lemma','POS','Morphology']", "five-column Greek NT table")
    require(script, "/api/logos/semantic/word-study?reference=", "73-book semantic word-study endpoint")
    require(script, "Full original-language word study", "semantic word-study heading")
    require(script, "Share word image", "semantic word image action")
    require(script, "Meaning here", "context-sensitive semantic label")
    require(ot_script, "verse mapping unavailable", "readable OT mapping boundary")
    require(script, "Lexical range", "lexical-range disclosure")
    require(script, "contextual sense are kept distinct", "lexical/context distinction")
    require(script, "contextual sense", "contextual semantic wording")
    require(script, "No morphology or semantic attachment is fabricated", "NT annotation-gap and semantic no-fabrication rule")
    require(script, "Pinned Greek source gap", "NT canonical-only Greek source-gap disclosure")
    require(script, "no Greek text or linguistic annotation is fabricated", "NT source-gap no-fabrication rule")
    require(script, "ShareAlike partition preserved", "NT ShareAlike frontend notice")
    require(script, "surface_and_linguistics_remain_separate", "NT licence partition contract gate")

    require(ot_script, "/api/logos/ot-interlinear/catalog", "unified OT catalog endpoint")
    require(ot_script, "/api/logos/ot-interlinear?reference=", "unified OT interlinear endpoint")
    require(ot_script, "/api/logos/semantic/word-study?reference=", "OT semantic word-study endpoint")
    require(ot_script, "window.MercyLogosSemantic", "shared semantic renderer bridge")
    require(ot_script, "Deuteronomy 6:4", "OT semantic verse hint")
    require(ot_script, "Tobit 1:1", "deuterocanonical semantic verse hint")
    require(ot_script, "catalog.production_enabled", "unified OT production gate")
    require(ot_script, "Number(catalog.catholic_ot_book_count)!==46", "46-book Catholic OT scope gate")
    require(ot_script, "lanes.semitic.installed", "Semitic installed gate")
    require(ot_script, "lanes.greek.installed", "Greek installed gate")
    require(ot_script, "lanes.latin.installed", "Latin installed gate")
    require(ot_script, "Number(lanes.greek.protocanonical_book_scope)!==39", "39-book protocanonical Greek gate")
    require(ot_script, "Number(lanes.greek.first1k_swete_book_scope)!==38", "38-book First1K/Swete gate")
    require(ot_script, "Number(lanes.greek.ecclesiastes_fallback_book_scope)!==1", "one-book Ecclesiastes fallback gate")
    require(ot_script, "Hebrew / Aramaic — OSHB/WLC", "Semitic lane label")
    require(ot_script, "Septuagint Greek", "generic Greek lane label")
    require(ot_script, "Clementine Latin Vulgate", "Latin lane label")
    require(ot_script, "mapping-required", "explicit mapping-required state")
    require(ot_script, "Logos does not manufacture a verse equivalence", "no manufactured mapping disclosure")
    require(ot_script, "['Verse','verse']", "verse column in unified table")
    require(ot_script, "['Douay-Rheims 1899','en']", "English unified table column")
    require(ot_script, "['Hebrew / Aramaic','sem']", "Semitic unified table column")
    require(ot_script, "['Septuagint Greek','grc']", "Greek unified table column")
    require(ot_script, "['Clementine Latin','lat']", "Latin unified table column")
    require(ot_script, "grc.label||(witness&&witness.name)||'Septuagint Greek'", "Greek witness-aware rendering")
    require(ot_script, "appendMappingCard('grc','Septuagint Greek'", "generic mapping-required Greek label")
    require(ot_script, "Ecclesiastes is not presented as Swete", "Ecclesiastes provenance disclosure")
    require(ot_script, "data.alignment&&(data.alignment.exact===true||data.alignment.verified_mapping===true)", "exact-or-verified Greek mapping gate")
    require(ot_script, "data.alignment.exact!==true&&data.alignment.verified_mapping!==true", "exact-or-verified Semitic mapping gate")
    require(ot_script, "source.source_osis_id", "Semitic native source deduplication gate")
    require(ot_script, "mapping.exact_verse_alignment===true", "accepted deuterocanonical exact-mapping gate")
    require(ot_script, "separate Rahlfs/lxx-morph linguistic witness", "OT Greek semantic witness boundary")
    require(ot_script, "without relabeling it as this surface witness", "OT Greek no-cross-edition relabeling rule")
    require(ot_script, "No Latin lemma, morphology, gloss or transliteration is fabricated", "Latin derived-layer boundary")

    # Regression gate for the chapter-level failure observed after the full OT corpora
    # were deployed: the old logos.js renderer may briefly write its historical
    # "corpus not installed" message. The unified script must detect that state,
    # reacquire its catalog if necessary, and take ownership of the panel.
    require(ot_script, "LEGACY_OT_WARNING='Original-language Old Testament corpus not installed yet'", "legacy OT warning detector")
    require(ot_script, "function legacyFallbackVisible()", "legacy OT fallback detector")
    require(ot_script, "function requestUnified(reference,force)", "unified OT recovery request")
    require(ot_script, "if(legacyFallbackVisible())showUnifiedLoading()", "legacy warning replacement")
    require(ot_script, "if(metadataInFlight)return metadataInFlight", "catalog retry de-duplication")
    require(ot_script, "window.MercyLogosOT=", "explicit unified OT frontend ownership API")
    require(ot_script, "observer.observe(tabPanel,{childList:true,subtree:true,characterData:true})", "legacy fallback mutation recovery")

    if "appendMappingCard('grc','Septuagint — Swete'" in ot_script:
        raise SystemExit("Mapping-required Greek lane must not mislabel Ecclesiastes as Swete")
    if "['Greek','Transliteration','Lemma','POS','Morphology','Gloss']" in script:
        raise SystemExit("Greek NT production table must not expose an unapproved Gloss column")
    if "['Greek','Transliteration','Lemma','POS','Morphology']" in ot_script:
        raise SystemExit("Unified OT frontend must not imply unavailable Greek linguistic annotations")
    if not style.strip():
        raise SystemExit("Interlinear stylesheet is empty")

    print("Logos unified Interlinear + Greek NT + four-lane OT frontend contract: OK")


if __name__ == "__main__":
    main()
