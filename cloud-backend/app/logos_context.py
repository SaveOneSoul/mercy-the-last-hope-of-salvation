"""Deterministic study scaffolds for Logos advanced biblical-study layers.

The data in this module is editorial metadata, not a substitute for a critical
commentary. It provides book/testament context and source-policy boundaries that
can be used for every installed passage. Passage-level conclusions remain
source-bounded and must distinguish Catholic doctrine, historical reconstruction,
archaeology, Jewish interpretation, other Christian traditions, and AI synthesis.
"""

from __future__ import annotations

from typing import Any


ADVANCED_AI_THEMES = [
    {"id": "book_background", "label": "Historical & theological background of the book"},
    {"id": "passage_background", "label": "Historical & theological background of this text"},
    {"id": "audience_purpose", "label": "Audience, occasion & purpose"},
    {"id": "secular_history", "label": "Secular history around this text"},
    {"id": "chronology_archives", "label": "Kings, archives & chronology"},
    {"id": "catholic_hermeneutics", "label": "Catholic exegesis & hermeneutics"},
    {"id": "jewish_interpretation", "label": "Jewish interpretive context"},
    {"id": "christian_traditions", "label": "Compare Christian commentary traditions"},
]


TESTAMENT_CONTEXT = {
    "OT": {
        "historical_background": (
            "The Old Testament arose within the history of Israel and Judah and preserves law, narrative, poetry, "
            "wisdom and prophetic traditions shaped across ancient Near Eastern, monarchic, exilic, Persian and "
            "Hellenistic settings. Dates and compositional histories vary by book and are sometimes disputed."
        ),
        "theological_background": (
            "Catholic reading receives the Old Testament as inspired Scripture within the one economy of salvation: "
            "creation, covenant, election, law, kingdom, wisdom, prophecy, exile, restoration and hope prepare for "
            "the fulfillment of God's saving plan in Christ without erasing the text's own historical sense."
        ),
        "audience_note": (
            "Primary audiences differ by book and layer. Israelite and later Jewish communities are the principal "
            "historical hearers/readers; a book-specific profile is returned below."
        ),
    },
    "NT": {
        "historical_background": (
            "The New Testament belongs to the first-century Jewish and Greco-Roman world under Roman rule. Its "
            "writings reflect Second Temple Judaism, the ministry, death and resurrection of Jesus, the apostolic "
            "mission, emerging local churches, synagogue/church relationships, Roman civic life and early Christian "
            "worship and controversy."
        ),
        "theological_background": (
            "Catholic reading receives the New Testament as the inspired witness to the definitive revelation of God "
            "in Jesus Christ, the Paschal Mystery, the gift of the Holy Spirit, the apostolic Church, sacramental life, "
            "mission, holiness and eschatological hope."
        ),
        "audience_note": (
            "Audience and occasion are especially important for the Gospels and letters. Where destination, date or "
            "authorship is debated, Logos reports the uncertainty rather than presenting a hypothesis as settled fact."
        ),
    },
}


# Concise book-level profiles. They are intentionally cautious where historical
# questions are debated and are used as context for every passage in that book.
BOOK_PROFILES: dict[str, dict[str, str]] = {
    "GEN": {"genre": "Torah / primeval and patriarchal narrative", "historical_setting": "Primeval and patriarchal traditions presented as the beginning of Israel's sacred history; compositional history is debated.", "audience": "Israel and later Jewish communities receiving the Torah.", "theological_focus": "Creation, fall, covenant, promise, election, blessing and providence."},
    "EXO": {"genre": "Torah / liberation, covenant and sanctuary narrative", "historical_setting": "Israel's deliverance from Egypt, Sinai covenant and wilderness worship; historical chronology and reconstruction are debated.", "audience": "Israel formed as a covenant people.", "theological_focus": "Divine deliverance, covenant, law, worship, presence and holiness."},
    "LEV": {"genre": "Torah / priestly law", "historical_setting": "Cultic and holiness legislation framed at Sinai.", "audience": "Israel, with particular relevance to priests and worshipping communities.", "theological_focus": "Holiness, sacrifice, priesthood, purity, atonement and ordered worship."},
    "NUM": {"genre": "Torah / wilderness narrative and law", "historical_setting": "Wilderness journey traditions between Sinai and the land.", "audience": "Israel remembering rebellion, judgment, preservation and promise.", "theological_focus": "Faithfulness, discipline, priestly order, divine guidance and inheritance."},
    "DEU": {"genre": "Torah / covenant exhortation", "historical_setting": "Moses' covenantal discourses presented before entry into the land; literary development is debated.", "audience": "Israel called to covenant fidelity.", "theological_focus": "One God, covenant love, law, remembrance, worship and choice of life."},
    "JOS": {"genre": "Historical narrative", "historical_setting": "Traditions of Israel's entry and settlement in Canaan; archaeology and chronology are debated site by site.", "audience": "Israel reflecting on land, covenant and obedience.", "theological_focus": "Promise, land, covenant fidelity, judgment and divine presence."},
    "JDG": {"genre": "Historical narrative", "historical_setting": "Pre-monarchic tribal traditions depicting cycles of crisis and deliverance.", "audience": "Israel interpreting disorder before the monarchy.", "theological_focus": "Covenant infidelity, mercy, judgment, charismatic deliverance and need for faithful leadership."},
    "RUT": {"genre": "Narrative / wisdom-like family story", "historical_setting": "Story set in the period of the Judges and oriented toward Davidic genealogy.", "audience": "Israel/Judah reflecting on fidelity, kinship and providence.", "theological_focus": "Hesed, providence, redemption, inclusion and Davidic ancestry."},
    "1SA": {"genre": "Historical narrative", "historical_setting": "Transition from judgeship to monarchy, Samuel, Saul and rise of David in the early Iron Age.", "audience": "Israel/Judah evaluating kingship under covenant.", "theological_focus": "Prophecy, kingship, obedience, divine election and covenant leadership."},
    "2SA": {"genre": "Historical narrative", "historical_setting": "Reign of David and dynastic traditions in the early monarchy.", "audience": "Israel/Judah reflecting on the Davidic kingdom.", "theological_focus": "Davidic covenant, kingship, sin, judgment, mercy and promise."},
    "1KI": {"genre": "Historical narrative", "historical_setting": "Solomon and the divided monarchies through the ninth century BC; several episodes intersect with external royal inscriptions.", "audience": "Judah/Israel interpreting monarchy through covenant fidelity.", "theological_focus": "Temple, kingship, prophetic word, idolatry and covenant judgment."},
    "2KI": {"genre": "Historical narrative", "historical_setting": "Israel and Judah under Assyrian and Babylonian pressure through Samaria's fall and Jerusalem's destruction.", "audience": "Exilic/post-exilic communities interpreting national catastrophe.", "theological_focus": "Prophecy, covenant judgment, reform, exile and enduring promise."},
    "1CH": {"genre": "Post-exilic historical genealogy and narrative", "historical_setting": "Retelling from Adam through David with strong temple and Levitical interests, generally associated with the Persian/post-exilic era.", "audience": "Restored Judah and temple-centered community.", "theological_focus": "Davidic legitimacy, worship, priestly/Levitical order and continuity of Israel."},
    "2CH": {"genre": "Post-exilic historical narrative", "historical_setting": "Solomon and Judah's kings through exile and Cyrus, retold with temple-centered concerns.", "audience": "Post-exilic Judah.", "theological_focus": "Temple, reform, prayer, retribution, repentance and restoration."},
    "EZR": {"genre": "Restoration narrative and documents", "historical_setting": "Persian-period return, temple rebuilding and Ezra's reform; includes Aramaic documentary material.", "audience": "Post-exilic Judean community.", "theological_focus": "Restoration, Torah, holiness, worship and communal identity."},
    "NEH": {"genre": "Restoration memoir/narrative", "historical_setting": "Persian-period rebuilding of Jerusalem's walls and communal reform.", "audience": "Post-exilic Judean community.", "theological_focus": "Restoration, prayer, covenant renewal, leadership and social responsibility."},
    "TOB": {"genre": "Diaspora wisdom narrative", "historical_setting": "Story set in Assyrian-era diaspora; literary form and precise compositional date are debated.", "audience": "Jewish communities reflecting on faithful life in diaspora.", "theological_focus": "Providence, almsgiving, prayer, marriage, angelic ministry, burial of the dead and fidelity."},
    "JDT": {"genre": "Didactic historical narrative", "historical_setting": "A deliberately stylized crisis narrative using mixed historical features; it should not be forced into a single modern chronological reconstruction.", "audience": "Jewish communities encouraged in fidelity under oppression.", "theological_focus": "Courage, prayer, fidelity, deliverance and God's defense of his people."},
    "EST": {"genre": "Diaspora court narrative", "historical_setting": "Persian imperial court setting; Catholic Esther includes Greek additions with explicit prayer and theological expansion.", "audience": "Jewish diaspora communities.", "theological_focus": "Providence, deliverance, identity, courage, fasting and prayer."},
    "1MA": {"genre": "Hellenistic-period historical narrative", "historical_setting": "Hasmonean revolt against Seleucid rule in the second century BC.", "audience": "Jewish communities interpreting the Maccabean struggle and Hasmonean leadership.", "theological_focus": "Zeal for the law, temple purification, covenant identity, martyrdom context and national deliverance."},
    "2MA": {"genre": "Theological history / epitome", "historical_setting": "Second-century BC Seleucid persecution and Maccabean resistance, presented as an epitome of a larger work.", "audience": "Greek-speaking Jews, including diaspora readers, encouraged to fidelity to the temple and law.", "theological_focus": "Resurrection, martyrdom, intercession, prayer for the dead, temple holiness and divine justice."},
    "JOB": {"genre": "Wisdom dialogue and poetry", "historical_setting": "A wisdom drama with a deliberately non-specific patriarchal setting; date and compositional layers are debated.", "audience": "Wisdom communities wrestling with innocent suffering.", "theological_focus": "Suffering, divine wisdom, human limitation, integrity and encounter with God."},
    "PSA": {"genre": "Prayer and hymn anthology", "historical_setting": "Collection spanning royal, temple, individual and communal traditions across long periods of Israel's worship.", "audience": "Israel/Judah and the worshipping community across generations.", "theological_focus": "Praise, lament, kingship, Torah, creation, repentance, trust and messianic hope."},
    "PRO": {"genre": "Wisdom instruction and sayings", "historical_setting": "Israelite wisdom collections associated with court, family and scribal settings; collections developed over time.", "audience": "Learners, households, leaders and wisdom communities.", "theological_focus": "Fear of the Lord, practical wisdom, justice, speech, family and disciplined life."},
    "ECC": {"genre": "Wisdom reflection", "historical_setting": "Qoheleth's reflections in a developed wisdom/scribal setting; exact date is debated.", "audience": "Readers confronting transience, toil and the limits of human mastery.", "theological_focus": "Vanity/transience, mortality, wisdom's limits, enjoyment as gift and fear of God."},
    "SNG": {"genre": "Love poetry", "historical_setting": "Ancient Hebrew love songs collected in Israel's wisdom tradition; literal and spiritual readings have coexisted in Jewish and Christian interpretation.", "audience": "Israel/Jewish readers and later worshipping communities.", "theological_focus": "Human love in the literal sense; in Catholic tradition also typological/spiritual readings concerning God, Christ and the Church."},
    "WIS": {"genre": "Hellenistic Jewish wisdom", "historical_setting": "Greek-speaking Jewish milieu, commonly associated with the Hellenistic diaspora.", "audience": "Greek-speaking Jews facing cultural and religious pressure.", "theological_focus": "Wisdom, righteousness, immortality, divine justice, creation and salvation history."},
    "SIR": {"genre": "Jewish wisdom instruction", "historical_setting": "Early second-century BC Jerusalem wisdom teaching, later translated into Greek by the author's grandson.", "audience": "Jewish students and households seeking faithful wisdom.", "theological_focus": "Torah and wisdom, worship, ethics, family, friendship, speech and Israel's ancestors."},
    "ISA": {"genre": "Prophetic anthology", "historical_setting": "Traditions span the Assyrian crisis, exile and restoration horizons; literary growth across these periods is widely discussed.", "audience": "Judah/Jerusalem and later exilic/post-exilic communities.", "theological_focus": "Holiness of God, judgment, remnant, Zion, servant, consolation, new exodus and messianic hope."},
    "JER": {"genre": "Prophecy and narrative", "historical_setting": "Late seventh to early sixth century BC Judah through Babylonian conquest, with later editorial shaping.", "audience": "Judah before and during catastrophe, and exilic readers.", "theological_focus": "Covenant infidelity, judgment, prophetic suffering, new covenant, restoration and hope."},
    "LAM": {"genre": "Poetic laments", "historical_setting": "Laments over Jerusalem's destruction, conventionally connected with the Babylonian catastrophe of 587/586 BC.", "audience": "Communities mourning Jerusalem and the temple.", "theological_focus": "Grief, judgment, repentance, memory, compassion and hope."},
    "BAR": {"genre": "Deuterocanonical prayer, wisdom and exhortation", "historical_setting": "Text presents an exilic frame while reflecting later Jewish theological and liturgical development.", "audience": "Jewish communities reflecting on exile, repentance and wisdom.", "theological_focus": "Confession, wisdom/Torah, consolation, Jerusalem and restoration."},
    "EZK": {"genre": "Prophecy", "historical_setting": "Babylonian exile in the early sixth century BC, centered among deportees in Babylonia.", "audience": "Exiled Judeans and later restored community.", "theological_focus": "Divine glory, responsibility, judgment, new heart/spirit, restored temple and renewed people."},
    "DAN": {"genre": "Court tales and apocalyptic visions", "historical_setting": "Court narratives are set in Babylonian/Persian contexts; visions address persecution and empire, with compositional history debated.", "audience": "Jewish communities seeking fidelity under imperial pressure.", "theological_focus": "Sovereignty of God, faithful witness, resurrection, judgment, kingdom and hope."},
    "HOS": {"genre": "Prophecy", "historical_setting": "Eighth-century BC northern kingdom before Assyrian conquest.", "audience": "Israel/Ephraim and later readers of the prophetic tradition.", "theological_focus": "Covenant love, infidelity, judgment, mercy and restoration."},
    "JOL": {"genre": "Prophecy", "historical_setting": "Locust crisis and day-of-the-Lord imagery; precise historical date is debated.", "audience": "Judah/Jerusalem called to communal repentance.", "theological_focus": "Repentance, day of the Lord, Spirit, restoration and salvation."},
    "AMO": {"genre": "Prophecy", "historical_setting": "Eighth-century BC prosperity and injustice in Israel under Jeroboam II.", "audience": "Northern kingdom of Israel, with later Judean reception.", "theological_focus": "Justice, judgment, true worship, election and restoration."},
    "OBA": {"genre": "Prophecy", "historical_setting": "Oracle against Edom connected with Jerusalem's catastrophe; exact date is debated.", "audience": "Judah and communities interpreting Edom's hostility.", "theological_focus": "Divine justice, day of the Lord, reversal and Zion."},
    "JON": {"genre": "Prophetic narrative", "historical_setting": "Didactic narrative set against Assyrian Nineveh; composition likely later than the setting.", "audience": "Israel/Judah reflecting on prophecy, mercy and outsiders.", "theological_focus": "Repentance, universal mercy, prophetic vocation and God's freedom."},
    "MIC": {"genre": "Prophecy", "historical_setting": "Eighth-century BC Judah/Israel amid Assyrian expansion.", "audience": "Samaria and Jerusalem/Judah.", "theological_focus": "Judgment, justice, remnant, Bethlehem hope, shepherd-king and covenant mercy."},
    "NAM": {"genre": "Prophecy", "historical_setting": "Oracle celebrating Nineveh's fall in the late seventh century BC.", "audience": "Judah under the shadow of Assyrian power.", "theological_focus": "Judgment on oppression, divine justice and deliverance."},
    "HAB": {"genre": "Prophetic dialogue and hymn", "historical_setting": "Late seventh/early sixth century BC amid Babylonian ascendancy.", "audience": "Judah wrestling with violence and imperial judgment.", "theological_focus": "Faithfulness, divine justice, lament and trust."},
    "ZEP": {"genre": "Prophecy", "historical_setting": "Late seventh-century BC Judah, traditionally in the reign of Josiah.", "audience": "Judah/Jerusalem.", "theological_focus": "Day of the Lord, judgment, humble remnant and restoration."},
    "HAG": {"genre": "Post-exilic prophecy", "historical_setting": "Persian-period Jerusalem in 520 BC during rebuilding of the temple.", "audience": "Returned Judean community and its leaders.", "theological_focus": "Temple rebuilding, covenant priorities, divine presence and future glory."},
    "ZEC": {"genre": "Post-exilic prophecy and apocalyptic vision", "historical_setting": "Early sections belong to Persian-period restoration; later sections have debated dates and settings.", "audience": "Post-exilic Judah and later readers awaiting fuller restoration.", "theological_focus": "Temple, purification, messianic kingship, shepherd imagery, Spirit and eschatological hope."},
    "MAL": {"genre": "Post-exilic prophecy", "historical_setting": "Persian-period Judah after restoration of temple worship.", "audience": "Priests and people confronting religious and social laxity.", "theological_focus": "Covenant fidelity, pure worship, marriage, justice, tithes and coming messenger/day of the Lord."},
    "MAT": {"genre": "Gospel", "historical_setting": "First-century Jewish and Greco-Roman setting; composition is commonly placed after Jesus' ministry and before the end of the first century, with exact date debated.", "audience": "A Christian community deeply engaged with Israel's Scriptures and Jewish tradition; precise location is debated.", "theological_focus": "Jesus as Messiah and Emmanuel, fulfillment, kingdom of heaven, Torah, Church, discipleship and mission."},
    "MRK": {"genre": "Gospel", "historical_setting": "First-century Roman imperial world; commonly regarded as the earliest extant Gospel, though exact date/location are debated.", "audience": "Predominantly Gentile or mixed Christian audience often associated by tradition with Roman/Petrine context.", "theological_focus": "Identity of Jesus, suffering Messiah, discipleship, cross, kingdom and resurrection hope."},
    "LUK": {"genre": "Gospel", "historical_setting": "First-century Jewish and Greco-Roman world, written as an orderly narrative within early Christian historiography.", "audience": "Addressed to Theophilus and intended for a broader Christian readership, likely including Gentiles.", "theological_focus": "Salvation for Israel and the nations, Holy Spirit, prayer, mercy, poor and marginalized, Jerusalem and joy."},
    "JHN": {"genre": "Gospel", "historical_setting": "Late first-century Christian and Jewish context is often proposed; exact community model and date remain debated.", "audience": "Christian readers called to believe that Jesus is the Christ, the Son of God; original local setting is debated.", "theological_focus": "Word made flesh, signs, glory, belief, eternal life, Father-Son relation, Spirit, sacramental symbolism and love."},
    "ACT": {"genre": "Apostolic history", "historical_setting": "Early Church from Jerusalem to Rome within the first-century Roman Empire.", "audience": "Addressed to Theophilus and a wider Christian readership.", "theological_focus": "Holy Spirit, apostolic witness, mission, Church unity, Gentile inclusion, persecution and providence."},
    "ROM": {"genre": "Pauline letter", "historical_setting": "Mid-first-century house churches in Rome, before Paul's planned western mission.", "audience": "Jewish and Gentile Christians in Rome.", "theological_focus": "Gospel, justification, grace, faith, baptism, life in the Spirit, Israel, ethics and unity."},
    "1CO": {"genre": "Pauline letter", "historical_setting": "Mid-first-century Corinth, a Roman colony marked by social diversity and church disputes.", "audience": "The Church of God in Corinth.", "theological_focus": "Church unity, cross, holiness, marriage, Eucharist, charisms, resurrection and love."},
    "2CO": {"genre": "Pauline letter", "historical_setting": "Paul's difficult relationship and reconciliation with Corinth; literary unity and chronology of sections are discussed.", "audience": "Christians in Corinth and Achaia.", "theological_focus": "Apostolic ministry, weakness and power, reconciliation, generosity, new covenant and suffering."},
    "GAL": {"genre": "Pauline letter", "historical_setting": "Conflict over Gentile believers, circumcision and Torah observance; destination/date depend partly on North/South Galatia theories.", "audience": "Churches of Galatia.", "theological_focus": "Gospel freedom, justification by faith, promise, baptismal unity, Spirit and Christian liberty."},
    "EPH": {"genre": "Pauline/circular letter", "historical_setting": "Address and authorship questions are debated; the letter addresses a mature Gentile-Christian setting in Asia Minor tradition.", "audience": "Gentile Christians, traditionally associated with Ephesus and possibly a wider circular readership.", "theological_focus": "Church as Christ's body, unity, grace, new humanity, household life and spiritual warfare."},
    "PHP": {"genre": "Pauline letter", "historical_setting": "Written from imprisonment to a loyal Macedonian church; exact imprisonment location is debated.", "audience": "Christians in Philippi.", "theological_focus": "Joy, partnership, humility of Christ, suffering, perseverance and heavenly citizenship."},
    "COL": {"genre": "Pauline letter", "historical_setting": "Addressed to Colossae amid teaching that threatened the sufficiency/supremacy of Christ; authorship is debated in modern scholarship.", "audience": "Christians in Colossae.", "theological_focus": "Supremacy of Christ, creation and reconciliation, baptism, new life and household discipleship."},
    "1TH": {"genre": "Pauline letter", "historical_setting": "Very early Pauline mission context in Macedonia, commonly dated around AD 50–51.", "audience": "The church of the Thessalonians.", "theological_focus": "Faith, love, hope, holiness, persecution and the coming of the Lord."},
    "2TH": {"genre": "Pauline letter", "historical_setting": "Addresses persecution, eschatological confusion and disorder; authorship/date are debated by some scholars.", "audience": "The church of the Thessalonians.", "theological_focus": "Perseverance, judgment, day of the Lord, tradition and disciplined work."},
    "1TI": {"genre": "Pastoral letter", "historical_setting": "Church order and teaching in Ephesus; Pauline authorship and chronology are debated in modern scholarship.", "audience": "Timothy as apostolic delegate, with implications for the Ephesian church.", "theological_focus": "Sound teaching, prayer, ministry, oversight, holiness and care of the community."},
    "2TI": {"genre": "Pastoral letter", "historical_setting": "Presented as Paul's final imprisonment and exhortation to Timothy; authorship/date are debated in modern scholarship.", "audience": "Timothy and, through him, Christian ministers/readers.", "theological_focus": "Faithfulness, Scripture, endurance, apostolic witness and handing on the deposit."},
    "TIT": {"genre": "Pastoral letter", "historical_setting": "Church organization in Crete; Pauline authorship/date are debated in modern scholarship.", "audience": "Titus as apostolic delegate and Cretan Christian communities.", "theological_focus": "Sound doctrine, good works, leadership, grace and Christian conduct."},
    "PHM": {"genre": "Pauline personal letter", "historical_setting": "Short prison letter concerning Onesimus and Philemon within the realities of Roman slavery.", "audience": "Philemon, Apphia, Archippus and the church meeting in their house.", "theological_focus": "Reconciliation, Christian brotherhood, freedom of charity and transformed social relations."},
    "HEB": {"genre": "Homiletic theological exhortation", "historical_setting": "Early Christian community under pressure; author, destination and exact date are uncertain.", "audience": "Christians tempted to weariness or withdrawal, with strong familiarity with Israel's Scriptures and worship.", "theological_focus": "Christ's priesthood, covenant, sacrifice, heavenly sanctuary, faith, perseverance and worship."},
    "JAS": {"genre": "Catholic epistle / wisdom exhortation", "historical_setting": "Jewish-Christian wisdom and pastoral setting; date and precise authorship identification are debated.", "audience": "The 'twelve tribes in the dispersion,' conventionally understood as Jewish-Christian communities.", "theological_focus": "Trials, wisdom, faith and works, speech, partiality, prayer, anointing and practical holiness."},
    "1PE": {"genre": "Catholic epistle", "historical_setting": "Christians facing social marginalization and suffering in Roman Asia Minor.", "audience": "Elect exiles across Pontus, Galatia, Cappadocia, Asia and Bithynia.", "theological_focus": "New birth, holiness, baptismal identity, suffering, witness, priestly people and hope."},
    "2PE": {"genre": "Catholic epistle", "historical_setting": "Addresses false teaching and delay of the Parousia; authorship/date are among the most debated in the NT.", "audience": "Christians needing perseverance in apostolic teaching.", "theological_focus": "Knowledge of Christ, moral growth, apostolic testimony, judgment and new heavens/new earth."},
    "1JN": {"genre": "Johannine homily/epistle", "historical_setting": "Community conflict over Christology, sin and fellowship in a Johannine Christian setting.", "audience": "Christians associated with the Johannine tradition.", "theological_focus": "Incarnation, fellowship, truth, love, obedience, assurance and discernment."},
    "2JN": {"genre": "Johannine letter", "historical_setting": "Brief letter addressing truth, love and itinerant teachers.", "audience": "The 'elect lady and her children,' likely a local church and its members, though interpretation varies.", "theological_focus": "Truth, love, commandment, Christological confession and boundaries of communion."},
    "3JN": {"genre": "Johannine letter", "historical_setting": "Local church conflict involving hospitality, authority and traveling missionaries.", "audience": "Gaius and the local Christian setting around him.", "theological_focus": "Truth, hospitality, mission, authority and imitation of good."},
    "JUD": {"genre": "Catholic epistle", "historical_setting": "Polemic against intruding teachers, drawing on Jewish scriptural and traditional examples.", "audience": "A Christian community threatened by corrupt teaching and conduct.", "theological_focus": "Contending for the faith, judgment, perseverance, mercy and apostolic tradition."},
    "REV": {"genre": "Apocalypse, prophecy and circular letter", "historical_setting": "Roman Asia Minor under imperial power; often situated late in the first century, though dating is debated.", "audience": "Seven churches of Asia and, through them, the wider Church.", "theological_focus": "Worship of God and Lamb, faithful witness, judgment of idolatrous empire, perseverance, victory and new creation."},
}


# External sources requested for reference integration. The host currently marks
# its pages "all rights reserved", so Logos links to them but does not scrape or
# bundle their hosted full text.
RESEARCH_LIBRARIES = [
    {"id": "ec2k-catena", "title": "Catena Aurea by St. Thomas Aquinas", "url": "https://www.ecatholic2000.com/catena/", "tradition": "Catholic / patristic", "coverage": "Four Gospels", "mode": "external-reference", "rights": "hosted-page-all-rights-reserved", "use": "Link and source pointer; do not copy hosted full text without permission or an independently verified reusable edition."},
    {"id": "ec2k-cathopedia", "title": "1913 Catholic Encyclopedia", "url": "https://www.ecatholic2000.com/cathopedia/title.shtml", "tradition": "Catholic reference", "coverage": "Biblical, theological, historical and ecclesial topics", "mode": "external-reference", "rights": "hosted-page-all-rights-reserved", "use": "Use as a research pointer; prefer independently verified public-domain scans/texts for any future local import."},
    {"id": "ec2k-summa", "title": "Summa Theologica of St. Thomas Aquinas", "url": "https://www.ecatholic2000.com/aquinas/", "tradition": "Catholic / scholastic", "coverage": "Systematic theology and biblical-theological synthesis", "mode": "external-reference", "rights": "hosted-page-all-rights-reserved", "use": "Link by topic; local full-text import requires an independently verified reusable edition."},
    {"id": "ec2k-fathers", "title": "Ante-Nicene, Nicene and Post-Nicene Fathers", "url": "https://www.ecatholic2000.com/fathers/untitled.shtml", "tradition": "Patristic", "coverage": "Early Christian writers", "mode": "external-reference", "rights": "hosted-page-all-rights-reserved", "use": "Reference pointer only on this host; future imports must pin author, work, translator/edition, provenance and rights."},
    {"id": "ec2k-library", "title": "Library of Christian Classics", "url": "https://www.ecatholic2000.com/library2/library.shtml", "tradition": "Catholic / Christian classics", "coverage": "Saints, Church history and reference works", "mode": "external-reference", "rights": "source-by-source-review", "use": "Treat each work independently; no blanket copying from the library index."},
    {"id": "ec2k-docs", "title": "Catholic Church Documents", "url": "https://www.ecatholic2000.com/docs/docs.shtml", "tradition": "Catholic", "coverage": "Ecclesial documents", "mode": "external-reference", "rights": "source-by-source-review", "use": "Use as a navigation aid; authoritative text/citation should be checked against official Holy See or bishops' conference sources where available."},
    {"id": "ec2k-home", "title": "e-Catholic 2000", "url": "https://www.ecatholic2000.com/", "tradition": "Catholic resource portal", "coverage": "Index to hosted Catholic resources", "mode": "external-reference", "rights": "hosted-page-all-rights-reserved", "use": "Portal/reference link only."},
    {"id": "ec2k-lapide", "title": "The Great Commentary of Cornelius à Lapide", "url": "https://www.ecatholic2000.com/lapide/", "tradition": "Catholic historical commentary", "coverage": "Selected biblical books/chapters in the hosted English collection", "mode": "external-reference", "rights": "hosted-page-all-rights-reserved", "use": "Link to hosted material; do not reproduce substantial hosted text. Prefer independently verified public-domain editions for future ingestion."},
]


COMMENTARY_TRADITIONS = [
    {"id": "catholic-magisterial", "label": "Catholic Magisterial & liturgical", "authority": "Normative Catholic doctrinal/liturgical context when an official document actually addresses the text.", "method": "Read literal sense within the unity of Scripture, living Tradition and analogy of faith; distinguish doctrine from private commentary.", "status": "primary-catholic-framework"},
    {"id": "catholic-patristic", "label": "Church Fathers & patristic tradition", "authority": "Ancient Christian reception and theological exegesis; individual Fathers are witnesses, not individually infallible.", "method": "Record author, work, passage and edition/translation; avoid fabricated quotations.", "status": "historical-catholic-witness"},
    {"id": "catholic-scholastic", "label": "Scholastic / Thomistic", "authority": "Major Catholic theological synthesis, especially useful for doctrinal questions.", "method": "Do not treat a scholastic conclusion as the grammatical sense of a verse unless the textual argument supports it.", "status": "catholic-theological-tradition"},
    {"id": "jewish", "label": "Jewish interpretive context", "authority": "Essential historical and interpretive context for the Hebrew Bible/Old Testament; not Catholic magisterial teaching.", "method": "Distinguish ancient Jewish context, rabbinic interpretation, medieval commentators and modern Jewish scholarship; do not retroject later rabbinic views into earlier periods without evidence.", "status": "comparative-context"},
    {"id": "eastern", "label": "Eastern Christian / Orthodox", "authority": "Ancient and continuing Eastern Christian reception; not identical to Roman Catholic doctrinal formulation.", "method": "Identify patristic/liturgical sources and points of convergence or difference without caricature.", "status": "comparative-christian"},
    {"id": "protestant", "label": "Protestant & Evangelical", "authority": "Important historical and modern Christian commentary traditions; not Catholic magisterial teaching.", "method": "Represent positions accurately and name the tradition when doctrinal assumptions differ (for example justification, sacraments, ecclesiology or Marian interpretation).", "status": "comparative-christian"},
    {"id": "ecumenical-critical", "label": "Ecumenical / historical-critical scholarship", "authority": "Academic historical, literary, textual and social-scientific research across confessional boundaries.", "method": "Separate historical hypotheses from theological judgments; report material disagreements and levels of confidence.", "status": "scholarly-comparison"},
]


ROYAL_ARCHIVE_LENSES = {
    "monarchy": [
        "Israelite/Judahite royal chronology and regnal synchronisms",
        "Assyrian royal inscriptions and eponym chronology where relevant",
        "West Semitic inscriptions and stelae where a passage has a defensible connection",
    ],
    "assyrian": [
        "Assyrian royal annals, campaign inscriptions, eponym lists and tribute records",
        "Archaeological destruction layers must be correlated cautiously with texts rather than assumed to prove them",
    ],
    "babylonian": [
        "Babylonian Chronicles, royal inscriptions and administrative evidence",
        "Exilic chronology should distinguish deportations, Jerusalem's destruction and later memory of those events",
    ],
    "persian": [
        "Achaemenid royal policy, inscriptions, administrative documents and local Yehud evidence",
        "Cyrus traditions should distinguish biblical theological interpretation from what a Persian royal inscription directly says",
    ],
    "hellenistic": [
        "Seleucid/Ptolemaic chronology, coins, inscriptions and Hellenistic historians",
        "Maccabean narratives should be synchronized cautiously with Seleucid regnal dates and independent evidence",
    ],
    "roman": [
        "Roman imperial chronology, provincial administration, inscriptions, papyri, coins and contemporary historians",
        "For the New Testament, Josephus and other ancient writers may supply context but should not be made to say more than they actually attest",
    ],
}


def _historical_lens(book_id: str, testament: str) -> list[str]:
    if book_id in {"1SA", "2SA", "1KI", "2KI", "1CH", "2CH"}:
        return ROYAL_ARCHIVE_LENSES["monarchy"] + ROYAL_ARCHIVE_LENSES["assyrian"] + ROYAL_ARCHIVE_LENSES["babylonian"]
    if book_id in {"ISA", "HOS", "AMO", "MIC", "NAM", "ZEP"}:
        return ROYAL_ARCHIVE_LENSES["assyrian"]
    if book_id in {"JER", "LAM", "EZK", "HAB", "DAN"}:
        return ROYAL_ARCHIVE_LENSES["babylonian"]
    if book_id in {"EZR", "NEH", "EST", "HAG", "ZEC", "MAL"}:
        return ROYAL_ARCHIVE_LENSES["persian"]
    if book_id in {"1MA", "2MA", "WIS", "SIR"}:
        return ROYAL_ARCHIVE_LENSES["hellenistic"]
    if testament == "NT":
        return ROYAL_ARCHIVE_LENSES["roman"]
    return [
        "Use ancient Near Eastern texts, inscriptions, archaeology and chronology only when they are genuinely relevant to this book and passage.",
        "Distinguish direct attestation, contextual parallel, disputed identification and later reconstruction.",
    ]


def advanced_ai_themes(seed_themes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    combined: list[dict[str, Any]] = []
    for row in list(seed_themes or []) + ADVANCED_AI_THEMES:
        theme_id = str(row.get("id") or "")
        if theme_id and theme_id not in seen:
            combined.append(dict(row))
            seen.add(theme_id)
    return combined


def build_background(item: dict[str, Any]) -> dict[str, Any]:
    book_id = str(item.get("book_id") or "")
    testament = str(item.get("testament") or "")
    profile = BOOK_PROFILES.get(book_id, {})
    testament_context = TESTAMENT_CONTEXT.get(testament, {})
    return {
        "reference": item.get("reference"),
        "book": item.get("book"),
        "book_id": book_id,
        "testament": testament,
        "testament_background": testament_context,
        "book_profile": profile,
        "passage_method": {
            "scope": "This endpoint supplies deterministic book/testament context. Passage-specific historical and theological conclusions require text-sensitive analysis and cited sources.",
            "historical_questions": ["What event, social setting, institution, genre or controversy is actually in view?", "Which claims are directly attested and which are reconstruction?", "What is the confidence level and what alternatives exist?"],
            "theological_questions": ["What is the literal sense in context?", "How does the passage function in the book and canon?", "How is it received in Catholic Tradition and, where relevant, liturgy and doctrine?"],
            "audience_questions": ["Who were the probable first hearers/readers?", "What occasion or pastoral problem is visible?", "Which audience claims are certain, probable or disputed?"],
        },
    }


def build_chronology(item: dict[str, Any]) -> dict[str, Any]:
    book_id = str(item.get("book_id") or "")
    testament = str(item.get("testament") or "")
    return {
        "reference": item.get("reference"),
        "book": item.get("book"),
        "testament": testament,
        "archive_lenses": _historical_lens(book_id, testament),
        "evidence_classes": [
            {"id": "direct", "label": "Direct external attestation", "rule": "A named person, ruler, place or event is independently attested in a source that can be cited."},
            {"id": "synchronism", "label": "Chronological synchronism", "rule": "Biblical and external regnal/era data can be compared, with calendar and accession-year assumptions stated."},
            {"id": "contextual", "label": "Contextual evidence", "rule": "Material culture or texts illuminate the period without directly attesting the biblical event."},
            {"id": "disputed", "label": "Disputed identification", "rule": "Scholarly disagreement over a person, site, inscription or date must be shown explicitly."},
            {"id": "reconstruction", "label": "Historical reconstruction", "rule": "A proposed synthesis is not presented as an archive fact."},
        ],
        "chronology_rule": "Never use royal annals, inscriptions, coins, archaeological layers or secular historians as automatic proof of a theological claim. State what the evidence directly says and what is inferred.",
    }


def build_traditions(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "reference": item.get("reference"),
        "book": item.get("book"),
        "testament": item.get("testament"),
        "traditions": COMMENTARY_TRADITIONS,
        "research_libraries": RESEARCH_LIBRARIES,
        "comparison_rule": "Catholic doctrine and authoritative Catholic interpretation must be identified as such. Jewish, Orthodox, Protestant/Evangelical and academic interpretations are presented fairly as comparative context, not silently merged into Catholic teaching.",
        "copyright_rule": "The listed e-Catholic 2000 pages are linked as external references because the host displays an all-rights-reserved notice. Logos does not scrape or bundle their hosted full text unless a separately verified reusable edition or permission is obtained.",
    }
