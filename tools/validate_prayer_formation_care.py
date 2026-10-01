"""Validate deployed learning data, new local links, and source-book integrity."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = ['mary-our-help','rosary-novena-54','healing-sessions','holy-wounds','prayer-protection',
         'prayer-conversion','mariology','psychology','counselling-courses','counselling',
         'counselling-ai','personal-counselling','theology-professional','philosophy',
         'psychology-professional','scripture-course','purgatory']


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.ids = set()
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            self.ids.add(a['id'])
        if tag in ('a', 'link', 'script'):
            self.links.append(a.get('href') or a.get('src') or '')


def main():
    for name in PAGES:
        file = ROOT / 'pages' / (name + '.html')
        parser = Links(); parser.feed(file.read_text())
        for href in parser.links:
            u = urlsplit(href)
            if u.scheme or u.netloc:
                continue
            target = (file.parent / unquote(u.path)).resolve() if u.path else file
            assert target.is_file(), (name, href)
            if u.fragment and target.suffix == '.html' and not target.name in {'logos.html'}:
                other = Links(); other.feed(target.read_text())
                assert unquote(u.fragment) in other.ids, (name, href, 'missing anchor')
    config = json.loads((ROOT / 'data/formation-courses.json').read_text())
    for course in config['courses']:
        if not course.get('contentFile'):
            continue
        data = json.loads((ROOT / 'pages' / course['contentFile']).read_text())
        assert len(data['units']) >= 10 and course['credits'] == len(data['units']) * 2
        for unit in data['units']:
            lesson_parts = list(unit.get('paragraphs', []))
            for section in unit.get('lectureSections', []):
                lesson_parts.extend(section.get('paragraphs', []))
                lesson_parts.extend(section.get('points', []))
            lesson_parts.extend(unit.get('methodNotes', []))
            assert len(' '.join(lesson_parts).split()) >= 90, unit['title']
            assert unit['sources'] and unit['assignment'] and len(unit['quiz']) == 2
        quizzes = [q for u in data['units'] for q in u['quiz']]
        for kind in ('mid', 'final'):
            assert len(data['assessments'][kind]) >= 5
            quizzes += data['assessments'][kind]
        for q in quizzes:
            assert len(q['options']) >= 2 and len(set(q['options'])) == len(q['options'])
            assert q['correct'] in range(len(q['options'])) and q['explanation']
    atlas = json.loads((ROOT / 'data/logos-bible-atlas.json').read_text())
    atlas_chapters = [chapter for part in atlas['parts'] for chapter in part['chapters']]
    atlas_maps = [item for chapter in atlas_chapters for item in chapter['maps']]
    assert len(atlas_chapters) == 21
    assert len(atlas_maps) == 172
    assert len(atlas['book_index']) == 73
    assert atlas['source']['rights_status'] == 'Reuse licence not stated in the uploaded PDF.'
    assert all(chapter['page'] >= 1 and chapter['maps'] for chapter in atlas_chapters)
    assert all(item['page'] >= 1 and item['title'] for item in atlas_maps)
    assert atlas.get('passage_rules')
    genesis_creation = [rule for rule in atlas['passage_rules']
                        if rule['book'] == 'Genesis'
                        and rule['chapter_start'] <= 1 <= rule['chapter_end']]
    assert len(genesis_creation) == 1
    assert any(topic['title'] == 'The Ancient Near East'
               for topic in genesis_creation[0]['topics'])
    assert len(atlas.get('visual_maps', {})) >= 10
    assert atlas.get('chapter_visual_map', {}).get('1') == 'ancient-near-east'
    assert atlas.get('chapter_visual_map', {}).get('2') == 'palestine-overview'
    assert genesis_creation[0].get('visual_map') == 'ancient-near-east'
    ancient_map = atlas['visual_maps']['ancient-near-east']
    assert ancient_map['points'] and ancient_map['regions'] and ancient_map['bounds']
    assert any(point['name'] == 'Ur' for point in ancient_map['points'])
    assert any(point['name'] == 'Jerusalem' for point in ancient_map['points'])
    logos_html = (ROOT / 'pages/logos.html').read_text()
    logos_js = (ROOT / 'javascript/logos.js').read_text()
    assert 'id="logosAtlasPreview"' in logos_html
    assert 'loadAtlasPreview(data)' in logos_js
    assert 'renderAtlasVisualMap' in logos_js
    assert 'data-atlas-fallback="true"' in logos_html
    assert 'Bible lands overview' in logos_html
    assert 'logos-atlas-sticky-bar' in logos_js
    assert 'logos-atlas-map-thumb' in logos_js
    assert 'atlasChapterCard(ch,data)' in logos_js
    assert "atlasPreview.hidden=false" in logos_js
    assert "createElementNS('http://www.w3.org/2000/svg'" in logos_js
    assert "currentTab='atlas'" in logos_js

    manifest = json.loads((ROOT / 'data/prayers/sources.json').read_text())
    for source in manifest['sources']:
        if source['file'].endswith('.pdf'):
            payload = (ROOT / 'pages/prayer-books' / source['file']).read_bytes()
            assert hashlib.sha256(payload).hexdigest() == source['sha256']
    for page in ('counselling-ai', 'personal-counselling'):
        content = (ROOT / 'pages' / (page + '.html')).read_text()
        assert 'mercy.js' not in content and 'live-site.js' not in content
        assert '14416' in content and 'tel:112' in content and 'Privacy before you send' in content
    deploy = (ROOT / '.github/workflows/mercy-pages.yml').read_text()
    assert 'cp -R data/courses data/prayers _site/data/' in deploy
    assert 'cp data/logos-bible-atlas.json _site/data/' in deploy
    print('Prayer, formation and support validation passed: routes, variable-length professional courses, Bible Atlas index, source PDFs, safety links and deployment data.')


if __name__ == '__main__':
    main()
