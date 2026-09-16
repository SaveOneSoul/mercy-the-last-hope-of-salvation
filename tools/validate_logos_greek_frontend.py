from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "logos.html"
SCRIPT = ROOT / "javascript" / "logos.js"
STYLE = ROOT / "css" / "logos-greek-integration.css"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"Missing {label}: {needle}")


def main() -> None:
    page = PAGE.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    style = STYLE.read_text(encoding="utf-8")

    require(page, 'data-logos-tab="interlinear"', "normal Interlinear tab")
    require(page, "logos.js?v=4", "cache-busted unified Logos script")
    require(page, "logos-greek-integration.css?v=1", "Greek interlinear stylesheet")
    require(page, "complete 73-book Douay-Rheims", "73-book English primary corpus wording")
    require(page, "Interlinear tab automatically loads the production Greek NT layer", "automatic NT interlinear wording")
    require(page, "No English word-gloss layer is displayed", "gloss rights boundary")

    if 'id="logosGreekNtTab"' in page:
        raise SystemExit("Redundant Greek NT tab must not be present; Interlinear is the single entry point")
    if "logos-greek-integration.js" in page:
        raise SystemExit("Legacy Greek tab integration script must not be loaded")

    require(script, "/api/logos/greek/catalog", "Greek catalog endpoint")
    require(script, "/api/logos/greek/source-rights", "Greek source-rights endpoint")
    require(script, "/api/logos/greek/interlinear?reference=", "Greek interlinear endpoint")
    require(script, "/api/logos/interlinear?reference=", "legacy/OT interlinear endpoint")
    require(script, "/api/logos/passage?reference=", "English DRA passage endpoint")
    require(script, "currentPassage.testament==='NT'", "automatic NT routing")
    require(script, "Primary Catholic Bible layer", "English primary-layer label")
    require(script, "['Greek','Transliteration','Lemma','POS','Morphology']", "five-column Greek table")
    require(script, "No English word gloss is displayed", "explicit no-gloss frontend rule")
    require(script, "No morphology is fabricated", "annotation-gap rule")
    require(script, "ShareAlike partition preserved", "ShareAlike frontend notice")
    require(script, "Original-language Old Testament corpus not installed yet", "OT fallback explanation")
    require(script, "surface_and_linguistics_remain_separate", "licence partition contract gate")

    if "['Greek','Transliteration','Lemma','POS','Morphology','Gloss']" in script:
        raise SystemExit("Greek production table must not expose an unapproved Gloss column")
    if not style.strip():
        raise SystemExit("Greek interlinear stylesheet is empty")

    print("Logos unified Interlinear + Greek NT frontend contract: OK")


if __name__ == "__main__":
    main()
