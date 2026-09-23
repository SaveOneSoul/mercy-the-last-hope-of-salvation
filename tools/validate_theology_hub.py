from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "theology.html"
INDEX = ROOT / "index.html"
SITEMAP = ROOT / "sitemap.xml"
RELATED = [
    ROOT / "pages" / "logos.html",
    ROOT / "pages" / "charis.html",
    ROOT / "pages" / "eucharistic-miracles.html",
    ROOT / "pages" / "catholic-ai.html",
    ROOT / "pages" / "prayer.html",
]

DISCIPLINES = [
    "foundations",
    "trinity",
    "christology",
    "pneumatology",
    "ecclesiology",
    "mariology",
    "sacraments",
    "moral",
    "spiritual",
    "eschatology",
]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"Missing {label}: {needle}")


def main() -> None:
    page = PAGE.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")

    require(page, "<h1>Catholic Theology</h1>", "Catholic Theology title")
    require(page, "Faith Seeking Understanding", "Faith Seeking Understanding identity")
    require(page, "Church Teaching → Scripture → Fathers & Doctors → Councils & Magisterium → Major Questions → Further Study", "shared study method")

    for discipline in DISCIPLINES:
        require(page, f'id="{discipline}"', f"{discipline} discipline section")

    for link, label in [
        ('href="logos.html"', "Logos cross-link"),
        ('href="charis.html"', "CHARIS cross-link"),
        ('href="eucharistic-miracles.html"', "Eucharist cross-link"),
        ('href="prayer.html"', "Prayer cross-link"),
        ('href="catholic-ai.html"', "Catholic AI cross-link"),
        ('href="sources.html"', "Sources cross-link"),
    ]:
        require(page, link, label)

    require(page, "Dei Verbum", "Revelation source")
    require(page, "Lumen Gentium", "Ecclesiology source")
    require(page, "Sacrosanctum Concilium", "Liturgical source")
    require(page, "Fides et Ratio", "faith and reason source")
    require(page, "Theology Today: Perspectives, Principles and Criteria", "International Theological Commission source")
    require(page, "Levels of certainty matter", "doctrinal-weight boundary")
    require(page, "personal speculation as doctrine", "theological-opinion boundary")

    if "<form" in page.lower():
        raise SystemExit("Theology hub must not introduce a public submission form")

    require(index, 'href="pages/theology.html">Theology</a>', "homepage Theology navigation")
    require(index, 'href="pages/theology.html"', "homepage Theology card")
    require(index, "Faith Seeking Understanding", "homepage Theology tagline")

    for related in RELATED:
        text = related.read_text(encoding="utf-8")
        require(text, 'href="theology.html">Theology</a>', f"Theology navigation in {related.name}")

    require(
        sitemap,
        "https://saveonesoul.github.io/mercy-the-last-hope-of-salvation/pages/theology.html",
        "Theology sitemap entry",
    )

    print(
        "Catholic Theology hub validation passed: "
        "10 disciplines, shared study method, formation cross-links, homepage navigation, and sitemap entry"
    )


if __name__ == "__main__":
    main()
