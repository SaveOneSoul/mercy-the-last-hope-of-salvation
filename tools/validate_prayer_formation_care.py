"""Validate deployed learning data, new local links, and source-book integrity."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGES = ['mary-our-help','rosary-novena-54','healing-sessions','holy-wounds','prayer-protection',
         'prayer-conversion','mariology','psychology','counselling-courses','counselling',
         'counselling-ai','personal-counselling']


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
        assert len(data['units']) == 10 and course['credits'] == 20
        for unit in data['units']:
            assert len(' '.join(unit['paragraphs']).split()) >= 90, unit['title']
            assert unit['sources'] and unit['assignment'] and len(unit['quiz']) == 2
        quizzes = [q for u in data['units'] for q in u['quiz']]
        for kind in ('mid', 'final'):
            assert len(data['assessments'][kind]) == 5
            quizzes += data['assessments'][kind]
        for q in quizzes:
            assert len(q['options']) == 3 and len(set(q['options'])) == 3
            assert q['correct'] in range(3) and q['explanation']
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
    print('Prayer, formation and support validation passed: 12 routes, 40 lessons, source PDFs, safety links and deployment data.')


if __name__ == '__main__':
    main()
