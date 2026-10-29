"""Readiness checks for generated pages, hierarchy, publication gates and links."""
import copy
import hashlib
import html
import re
import json
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_seo import Builder, validate_regions, publication_problems, region_path, verified_source, confirmed_operator_coverage


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = set()
        self.links = []
        self.h1 = 0
        self.alt = []
        self.canonical = []
        self.title = []
        self.in_title = False
        self.description = []
        self.lang = None
        self.viewport = []
        self.robots = []
        self.og = {}
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'html':
            self.lang = attrs.get('lang')
        if tag == 'meta':
            if attrs.get('name') == 'viewport':
                self.viewport.append(attrs.get('content', ''))
            if attrs.get('name') == 'robots':
                self.robots.append(attrs.get('content', ''))
            if attrs.get('property', '').startswith('og:'):
                self.og.setdefault(attrs['property'], []).append(attrs.get('content', ''))
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag == 'a':
            self.links.append(attrs)
        if tag == 'h1':
            self.h1 += 1
        if tag == 'img':
            self.alt.append(attrs.get('alt', ''))
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonical.append(attrs['href'])
        if tag == 'meta' and attrs.get('name') == 'description':
            self.description.append(attrs.get('content', ''))
        if tag == 'title':
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)


class SEOTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline_builder = Builder()
        cls.baseline_builder.build()

    def setUp(self):
        # Keep mutation tests isolated without repeating the same expensive build.
        # The reproducibility test below still performs independent fresh builds.
        self.builder = copy.deepcopy(self.baseline_builder)

    def test_generated_output_is_current_and_reproducible(self):
        self.builder.save(check=True)
        other = Builder()
        other.build()
        self.assertEqual(self.builder.outputs, other.outputs)

    def test_every_published_page_has_unique_metadata_and_accessible_html(self):
        titles, descriptions, canonical = [], [], []
        for path, text in self.builder.outputs.items():
            if not path.endswith('.html'):
                continue
            doc = Document(text)
            self.assertEqual(doc.h1, 1, path)
            self.assertEqual(len(doc.canonical), 1, path)
            self.assertTrue(doc.alt and all(doc.alt), path)
            self.assertEqual(len(doc.description), 1, path)
            self.assertNotIn('noindex', text)
            titles.append(''.join(doc.title))
            descriptions.append(doc.description[0])
            canonical.append(doc.canonical[0])
        for items in (titles, descriptions, canonical):
            self.assertTrue(all(items))
            self.assertEqual(len(items), len(set(items)))

    def test_all_internal_links_and_fragments_resolve(self):
        for path, text in self.builder.outputs.items():
            if not path.endswith('.html'):
                continue
            doc = Document(text)
            for attrs in doc.links:
                parsed = urlsplit(attrs['href'])
                if parsed.scheme:
                    self.assertIn(parsed.scheme, ('http', 'https', 'tel'))
                    if attrs.get('target') == '_blank':
                        self.assertIn('noopener', attrs.get('rel', ''))
                    continue
                destination = (ROOT / path).parent / unquote(parsed.path) if parsed.path else ROOT / path
                if destination.is_dir():
                    destination /= 'index.html'
                resolved = destination.resolve()
                self.assertTrue(resolved.is_relative_to(ROOT), attrs['href'])
                self.assertTrue(resolved.is_file(), f'{path}: {attrs["href"]}')
                if parsed.fragment:
                    target = doc if resolved == ROOT / path else Document(resolved.read_text())
                    self.assertIn(parsed.fragment, target.ids)

    def test_sitemap_exactly_matches_public_pages(self):
        root = ET.fromstring(self.builder.outputs['sitemap.xml'])
        urls = [node.text for node in root.findall('{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
        expected = {self.builder.base} | {self.builder.canonical(path) for path in self.builder.outputs if path.endswith('.html')}
        self.assertEqual(set(urls), expected)
        self.assertEqual(len(urls), len(set(urls)))
        self.assertTrue(all(url.startswith(self.builder.base) for url in urls))

    def test_cheongju_four_boroughs_metadata_geography_and_navigation(self):
        parent = self.builder.ids['chungbuk-cheongju']
        refs = json.loads((ROOT / 'data/seo/cheongju_borough_geography.json').read_text())['boroughs']
        targets = {'sangdang': '상당구', 'seowon': '서원구', 'heungdeok': '흥덕구', 'cheongwon': '청원구'}
        self.assertEqual({x['slug']: x['name'] for x in parent['boroughs']}, targets)
        self.assertEqual(sum(len(x['administrative_areas']) for x in refs), 43)
        topics = set()
        parent_text = self.builder.outputs[region_path(parent, self.builder.ids)]
        for slug, name in targets.items():
            item = self.builder.ids['chungbuk-cheongju-' + slug]
            path = 'regions/chungbuk/cheongju/' + slug + '/index.html'
            self.assertEqual(region_path(item, self.builder.ids), path)
            text = self.builder.outputs[path]
            doc = Document(text)
            self.assertEqual(doc.canonical, [self.builder.canonical(path)])
            self.assertEqual(doc.og['og:url'], doc.canonical)
            self.assertEqual(doc.h1, 1)
            self.assertIn('href="' + slug + '/"', parent_text)
            self.assertIn('href="../"', text)
            self.assertIn('href="../../"', text)
            self.assertIn('충청북도 과외 대표 안내', text)
            for sibling in targets:
                if sibling != slug:
                    self.assertIn('href="../' + sibling + '/"', text)
            self.assertNotIn('1:1', json.dumps(item, ensure_ascii=False))
            self.assertNotIn('경기도', text)
            self.assertEqual([x['name'] for x in item['neighborhoods']], next(x['administrative_areas'] for x in refs if x['page_id'] == item['id']))
            breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
            self.assertEqual([x['position'] for x in breadcrumb['itemListElement']], [1, 2, 3, 4, 5])
            self.assertEqual(service['areaServed']['name'], '충청북도 청주시 ' + name)
            self.assertEqual(service['areaServed']['containedInPlace']['name'], '충청북도 청주시')
            self.assertEqual(service['areaServed']['containedInPlace']['containedInPlace']['name'], '충청북도')
            self.assertEqual([(q['name'], q['acceptedAnswer']['text']) for q in faq['mainEntity']], [(q['question'], q['answer']) for q in item['faq']])
            topics.add(item['sections'][2]['heading'])
        self.assertEqual(len(topics), 4)
        invalid = copy.deepcopy(self.builder.regions)
        next(x for x in invalid if x['id'] == 'chungbuk-cheongju-sangdang')['parent_id'] = 'chungbuk-chungju'
        with self.assertRaises(ValueError):
            validate_regions(invalid)

    def test_chungbuk_11_city_county_guides(self):
        hub = self.builder.ids['chungbuk']
        self.assertEqual(hub['official_name'], '충청북도')
        children = [r for r in self.builder.regions if r.get('parent_id') == 'chungbuk']
        self.assertEqual(len(children), 11)
        self.assertEqual(sum(r['name'].endswith('시') for r in children), 3)
        self.assertEqual(sum(r['name'].endswith('군') for r in children), 8)
        refs = json.loads((ROOT / 'data/seo/chungbuk_geography.json').read_text())['regions']
        self.assertEqual(sum(len(names) for r in refs for names in r['groups'].values()), 153)
        for item in children:
            path = region_path(item, self.builder.ids)
            text = self.builder.outputs[path]
            self.assertIn(self.builder.canonical(path), text)
            self.assertIn(item['title'], text)
            self.assertIn(item['h1'], text)
            ref = next(r for r in refs if r['page_id'] == item['id'])
            names = [(g.removeprefix('청주시') + ' ' + n if item['name'] == '청주시' else n) for g, ns in ref['groups'].items() for n in ns]
            self.assertEqual([x['name'] for x in item['neighborhoods']], names)
            self.assertNotIn('춘천', text)
            self.assertNotIn('강원특별자치도', text)
        for key in ['title', 'description', 'h1']:
            self.assertEqual(len({r[key] for r in children}), 11)
        cheongju = next(r for r in children if r['name'] == '청주시')
        self.assertEqual({x['name'].split()[0] for x in cheongju['neighborhoods']}, {'상당구', '서원구', '흥덕구', '청원구'})

    def test_gangwon_18_city_county_guides(self):
        hub = self.builder.ids['gangwon']
        self.assertEqual(hub['official_name'], '강원특별자치도')
        children = [r for r in self.builder.regions if r.get('parent_id') == 'gangwon']
        self.assertEqual(len(children), 18)
        self.assertEqual(sum(r['name'].endswith('시') for r in children), 7)
        self.assertEqual(sum(r['name'].endswith('군') for r in children), 11)
        refs = json.loads((ROOT / 'data/seo/gangwon_geography.json').read_text())['regions']
        self.assertEqual(sum(len(r['administrative_areas']) for r in refs), 188)
        for item in children:
            path = region_path(item, self.builder.ids)
            text = self.builder.outputs[path]
            self.assertIn(self.builder.canonical(path), text)
            self.assertIn(item['title'], text)
            self.assertIn(item['h1'], text)
            self.assertEqual([x['name'] for x in item['neighborhoods']], next(r['administrative_areas'] for r in refs if r['page_id'] == item['id']))
            self.assertNotIn('가평', text)
            self.assertNotIn('경기도', text)
        for key in ['title', 'description', 'h1']:
            self.assertEqual(len({r[key] for r in children}), 18)

    def test_all_17_unreviewed_provinces_remain_unpublished(self):
        provinces = [r for r in self.builder.regions if r['kind'] == 'province']
        self.assertEqual(len(provinces), 17)
        for item in [r for r in self.builder.regions if r['status'] == 'draft']:
            path = region_path(item, self.builder.ids)
            self.assertNotIn(path, self.builder.outputs)
            self.assertFalse((ROOT / path).exists())
            self.assertTrue(publication_problems(item, self.builder.ids))
        attempted = copy.deepcopy(self.builder.regions)
        unreviewed = attempted[0]
        unreviewed.update(status='published', review={'approved': False}, sources=[])
        with self.assertRaises(ValueError):
            validate_regions(attempted)

    def test_invalid_school_and_hierarchy_are_rejected(self):
        school = {'id': 'unverified-school', 'slug': 'unverified-school', 'kind': 'school', 'name': '검증용 학교', 'official_name': '검증용 학교', 'parent_id': 'seoul', 'status': 'draft'}
        with self.assertRaises(ValueError):
            validate_regions(self.builder.regions + [school])
        school.update(parent_id=None, status='published', school={'official_name': '검증용 학교'})
        self.assertTrue(any('school' in problem.lower() for problem in publication_problems(school, {})))
        self.assertFalse(verified_source({'url': 'https://example.com/school', 'verified': True, 'checked_on': '2026-10-12', 'type': 'official_school'}, school=True))

    def test_draft_previews_cannot_be_written_into_public_checkout(self):
        with self.assertRaises(ValueError):
            self.builder.preview_drafts(ROOT / 'draft-previews')

    def test_valid_hierarchy_produces_nested_school_grade_subject_url(self):
        records = copy.deepcopy(self.builder.regions)
        parent = 'daegu'
        for kind, identifier, name in [('district', 'donggu', '동구'), ('neighborhood', 'bangchon', '방촌동'), ('school', 'verified-school', '검증용 학교'), ('learning', 'middle-math', '중학생 수학')]:
            records.append({'id': identifier, 'slug': identifier, 'kind': kind, 'name': name, 'official_name': name, 'parent_id': parent, 'status': 'draft'})
            parent = identifier
        ids = validate_regions(records)
        self.assertEqual(region_path(ids['middle-math'], ids), 'regions/daegu/donggu/bangchon/verified-school/middle-math/index.html')
        self.assertNotIn(region_path(ids['middle-math'], ids), self.builder.outputs)

    def test_region_name_only_duplicates_are_rejected(self):
        records = copy.deepcopy(self.builder.regions[:2])
        for record in records:
            record.update(status='published', intro=record['name'] + ' 지역 상담 안내', sources=[{'url': 'https://www.moe.go.kr/', 'checked_on': '2026-10-12', 'verified': True, 'label': '테스트용 출처'}], review={'approved': True, 'reviewed_on': '2026-10-12'})
            record['sections'] = [{'heading': '테스트용 학습 안내', 'paragraphs': [('동일한 내용을 지역명만 변경해 공개하지 않는지 점검하는 테스트 데이터입니다. ' * 10)], 'local_relevance': '중복 차단 테스트'} for _ in range(3)]
        self.builder.regions = records
        self.builder.ids = validate_regions(records)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.builder.build()

    def test_seoul_metadata_districts_faq_and_breadcrumb_match_visible_content(self):
        item = self.builder.ids['seoul']
        text = self.builder.outputs['regions/seoul/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/'])
        self.assertEqual(len(item['districts']), 25)
        self.assertEqual(len({d['name'] for d in item['districts']}), 25)
        self.assertEqual(text.count('class="district-card"'), 25)
        self.assertTrue('href="gangnam/"' in text)
        structured = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        breadcrumb, faq = structured
        self.assertEqual(breadcrumb['@type'], 'BreadcrumbList')
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(len(breadcrumb['itemListElement']), 3)
        self.assertEqual(faq['@type'], 'FAQPage')
        self.assertEqual(len(faq['mainEntity']), 5)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)
            self.assertIn('<p>' + html.escape(shown['answer'], quote=True) + '</p>', text)

    def test_operator_confirmation_cannot_bypass_school_or_wrong_region_gates(self):
        item = copy.deepcopy(self.builder.ids['seoul'])
        self.assertTrue(confirmed_operator_coverage(item))
        item['id'] = 'different-region'
        self.assertFalse(confirmed_operator_coverage(item))
        item['id'] = 'seoul'
        item['kind'] = 'school'
        self.assertFalse(confirmed_operator_coverage(item))
        item['school'] = {'official_name': '검증용 학교', 'official_code': 'TEST', 'non_affiliation_notice': True}
        self.assertTrue(publication_problems(item, {}))

    def test_gangnam_metadata_schema_neighborhoods_and_parent_links(self):
        item = self.builder.ids['seoul-gangnam']
        path = 'regions/seoul/gangnam/index.html'
        text = self.builder.outputs[path]
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/gangnam/'])
        self.assertTrue(item['title'].startswith('강남구 1:1과외'))
        self.assertTrue(item['h1'].startswith('강남구 1:1과외'))
        self.assertEqual(len(item['neighborhoods']), 12)
        self.assertEqual(text.count('class="district-card"'), 12)
        self.assertFalse(any('/daechi/' in a['href'] for a in doc.links))
        self.assertTrue(any(a['href'] == '../' for a in doc.links))
        schemas = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        breadcrumb, service, faq = schemas
        self.assertEqual(len(breadcrumb['itemListElement']), 4)
        self.assertEqual(breadcrumb['itemListElement'][-2]['item'], self.builder.base + 'regions/seoul/')
        self.assertEqual(service['@type'], 'Service')
        self.assertEqual(service['areaServed']['name'], '서울특별시 강남구')
        self.assertEqual(service['provider']['telephone'], '010-4377-6964')
        self.assertFalse(any(k in service for k in ('offers', 'aggregateRating', 'review', 'address')))
        self.assertEqual(len(faq['mainEntity']), 5)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertTrue('<summary>' + html.escape(shown['question'], quote=True) + '</summary>' in text)

    def test_gangdong_content_metadata_schema_and_seoul_entry(self):
        item = self.builder.ids['seoul-gangdong']
        text = self.builder.outputs['regions/seoul/gangdong/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/gangdong/'])
        self.assertEqual(len(item['neighborhoods']), 8)
        self.assertEqual(text.count('class="district-card"'), 8)
        self.assertFalse('강남구' in text)
        self.assertFalse(any('/godeok/' in a['href'] for a in doc.links))
        self.assertTrue('href="gangdong/"' in self.builder.outputs['regions/seoul/index.html'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['name'], '강동구 과외')
        self.assertEqual(service['areaServed']['name'], '서울특별시 강동구')
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertTrue('<summary>' + html.escape(shown['question'], quote=True) + '</summary>' in text)

    def test_gangbuk_metadata_neighborhoods_schema_and_parent_entry(self):
        item = self.builder.ids['seoul-gangbuk']
        text = self.builder.outputs['regions/seoul/gangbuk/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/gangbuk/'])
        self.assertEqual([n['name'] for n in item['neighborhoods']], ['미아동', '수유동', '번동', '우이동'])
        self.assertEqual(text.count('class="district-card"'), 4)
        self.assertFalse(any('/mia/' in a['href'] for a in doc.links))
        self.assertTrue('href="gangbuk/"' in self.builder.outputs['regions/seoul/index.html'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['name'], '강북구 과외')
        self.assertEqual(service['areaServed']['name'], '서울특별시 강북구')
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertTrue('<summary>' + html.escape(shown['question'], quote=True) + '</summary>' in text)

    def test_gangseo_metadata_visible_faq_service_and_seoul_entry(self):
        item = self.builder.ids['seoul-gangseo']
        text = self.builder.outputs['regions/seoul/gangseo/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/gangseo/'])
        self.assertEqual(len(item['neighborhoods']), 8)
        self.assertFalse(any('/hwagok/' in a['href'] for a in doc.links))
        self.assertTrue('href="gangseo/"' in self.builder.outputs['regions/seoul/index.html'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['name'], '강서구 과외')
        self.assertEqual(service['areaServed']['name'], '서울특별시 강서구')
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertTrue('<summary>' + html.escape(shown['question'], quote=True) + '</summary>' in text)

    def test_gwanak_metadata_living_areas_faq_and_service(self):
        item = self.builder.ids['seoul-gwanak']
        text = self.builder.outputs['regions/seoul/gwanak/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/gwanak/'])
        self.assertEqual(len(item['neighborhoods']), 5)
        self.assertFalse(any('/bongcheon/' in a['href'] for a in doc.links))
        self.assertTrue('href="gwanak/"' in self.builder.outputs['regions/seoul/index.html'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['name'], '관악구 과외')
        self.assertEqual(service['areaServed']['name'], '서울특별시 관악구')
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertTrue('<summary>' + html.escape(shown['question'], quote=True) + '</summary>' in text)

    def test_gwangjin_metadata_localities_schema_and_seoul_entry(self):
        item = self.builder.ids['seoul-gwangjin']
        text = self.builder.outputs['regions/seoul/gwangjin/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/gwangjin/'])
        self.assertEqual([n['name'] for n in item['neighborhoods']], ['광장동', '자양동', '구의동', '중곡동', '능동', '화양동', '군자동'])
        self.assertFalse(any('/gwangjang/' in a['href'] for a in doc.links))
        self.assertTrue('href="gwangjin/"' in self.builder.outputs['regions/seoul/index.html'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['name'], '광진구 과외')
        self.assertEqual(service['areaServed']['name'], '서울특별시 광진구')
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertTrue('<summary>' + html.escape(shown['question'], quote=True) + '</summary>' in text)

    def test_guro_metadata_faq_and_counseling_only_service(self):
        item = self.builder.ids['seoul-guro']
        text = self.builder.outputs['regions/seoul/guro/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/guro/'])
        self.assertEqual(len(item['neighborhoods']), 10)
        self.assertFalse(any('/gaebong/' in a['href'] for a in doc.links))
        self.assertTrue('href="guro/"' in self.builder.outputs['regions/seoul/index.html'])
        self.assertTrue(item['cta_heading'] in text)
        self.assertTrue(item['cta_note'] in text)
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['name'], '구로구 과외')
        self.assertEqual(service['areaServed']['name'], '서울특별시 구로구')
        self.assertIn('상담', service['serviceType'])
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertTrue('<summary>' + html.escape(shown['question'], quote=True) + '</summary>' in text)

    def test_geumcheon_publication_links_faq_and_conditional_coverage(self):
        item = self.builder.ids['seoul-geumcheon']
        path = 'regions/seoul/geumcheon/index.html'
        text = self.builder.outputs[path]
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/geumcheon/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['독산동', '시흥동', '가산동'])
        self.assertTrue(all(p['page_id'] is None for p in item['neighborhoods']))
        self.assertIn('href="geumcheon/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn('href="../"', text)
        self.assertIn(self.builder.base + 'regions/seoul/geumcheon/', self.builder.outputs['sitemap.xml'])
        self.assertIn('배정 가능 여부', item['intro'])
        self.assertIn('선행에 앞서', text)
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 금천구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)
        self.assertIn('class="stepon-floating"', text)
        self.assertIn('https://www.instagram.com/stepon_seona/', text)

    def test_nowon_publication_links_faq_and_conditional_coverage(self):
        item = self.builder.ids['seoul-nowon']
        path = 'regions/seoul/nowon/index.html'
        text = self.builder.outputs[path]
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/nowon/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['중계동', '상계동', '하계동', '공릉동', '월계동'])
        self.assertTrue(all(p['page_id'] is None for p in item['neighborhoods']))
        self.assertIn('href="nowon/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn('href="../"', text)
        self.assertIn(self.builder.base + 'regions/seoul/nowon/', self.builder.outputs['sitemap.xml'])
        self.assertIn('배정 가능 여부', item['intro'])
        self.assertIn('학원 수업과 과외를 병행', text)
        self.assertIn('도움 없는 풀이', text)
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 노원구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)
        self.assertIn('class="stepon-floating"', text)
        self.assertIn('https://www.instagram.com/stepon_seona/', text)

    def test_dobong_transition_guidance_and_publication(self):
        item = self.builder.ids['seoul-dobong']
        text = self.builder.outputs['regions/seoul/dobong/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/dobong/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['창동', '쌍문동', '방학동', '도봉동'])
        self.assertTrue(all(p['page_id'] is None for p in item['neighborhoods']))
        self.assertIn('예비중', text)
        self.assertIn('예비고', text)
        self.assertIn('href="dobong/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 도봉구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)

    def test_dongdaemun_transition_content_and_publication(self):
        item = self.builder.ids['seoul-dongdaemun']
        text = self.builder.outputs['regions/seoul/dongdaemun/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/dongdaemun/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['장안동', '답십리동', '전농동', '휘경동', '이문동', '청량리동', '제기동', '용두동', '신설동', '회기동'])
        self.assertTrue(all(p['page_id'] is None for p in item['neighborhoods']))
        self.assertIn('이해·적용·재점검', text)
        self.assertIn('guides/performance-assessment/', text)
        self.assertIn('href="dongdaemun/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 동대문구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)

    def test_dongjak_neighborhood_names_learning_habits_and_publication(self):
        item = self.builder.ids['seoul-dongjak']
        text = self.builder.outputs['regions/seoul/dongjak/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/dongjak/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['상도동', '상도1동', '사당동', '노량진동', '흑석동', '대방동', '신대방동', '본동', '동작동'])
        self.assertEqual(len({p['slug'] for p in item['neighborhoods']}), 9)
        self.assertTrue(all(p['page_id'] is None for p in item['neighborhoods']))
        self.assertIn('시간이 지난 뒤', text)
        self.assertIn('조건 해석', text)
        self.assertIn('href="dongjak/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 동작구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)

    def test_mapo_living_areas_assessment_planning_and_publication(self):
        item = self.builder.ids['seoul-mapo']
        text = self.builder.outputs['regions/seoul/mapo/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/mapo/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['공덕·아현 생활권', '대흥·신수 생활권', '서교·합정 생활권', '망원·성산 생활권', '상암 생활권'])
        self.assertTrue(all(p['page_id'] is None for p in item['neighborhoods']))
        for name in ['공덕동', '아현동', '신공덕동', '도화동', '염리동', '대흥동', '신수동', '용강동', '노고산동', '서교동', '합정동', '연남동', '상수동', '창전동', '동교동', '망원동', '성산동', '중동', '상암동', '토정동', '마포동', '현석동', '구수동', '하중동', '신정동', '당인동']:
            self.assertIn(name, text)
        self.assertIn('중학생 수행평가와 지필평가를 함께 준비하는 학습 계획', text)
        self.assertIn('guides/performance-assessment/', text)
        self.assertIn('href="mapo/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 마포구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)

    def test_seodaemun_living_areas_concept_application_and_publication(self):
        item = self.builder.ids['seoul-seodaemun']
        text = self.builder.outputs['regions/seoul/seodaemun/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/seodaemun/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['남가좌·북가좌 생활권', '홍제·홍은 생활권', '연희·신촌 생활권', '북아현·충현 생활권', '천연 생활권'])
        self.assertTrue(all(p['page_id'] is None for p in item['neighborhoods']))
        for name in ['남가좌동', '북가좌동', '홍제동', '홍은동', '연희동', '신촌동', '창천동', '대현동', '북아현동', '충정로2가', '충정로3가', '합동', '미근동', '천연동', '냉천동', '영천동', '현저동']:
            self.assertIn(name, text)
        self.assertIn('영어·수학 성적이 정체될 때 확인해야 할 기초학습 점검 방법', text)
        self.assertIn('문장 구조', text)
        self.assertIn('개념을 예와 함께 설명', text)
        self.assertIn('href="seodaemun/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 서대문구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)

    def test_seocho_living_areas_study_priorities_and_publication(self):
        item = self.builder.ids['seoul-seocho']
        text = self.builder.outputs['regions/seoul/seocho/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/seocho/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['서초 생활권', '반포·잠원 생활권', '방배 생활권', '양재·우면 생활권', '내곡 생활권'])
        self.assertTrue(all(p['page_id'] is None for p in item['neighborhoods']))
        for name in ['서초동', '반포동', '잠원동', '방배동', '양재동', '우면동', '내곡동', '신원동', '염곡동', '원지동']:
            self.assertIn(name, text)
        self.assertIn('내신과 수능 공부를 병행할 때 학습 우선순위를 정하는 방법', text)
        self.assertIn('학교 시험과 모의고사의 오답', text)
        self.assertIn('무리한 선행보다 개념 이해', text)
        self.assertIn('href="seocho/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 서초구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)

    def test_seongdong_living_areas_independent_study_and_publication(self):
        item = self.builder.ids['seoul-seongdong']
        text = self.builder.outputs['regions/seoul/seongdong/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/seongdong/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['왕십리·행당 생활권', '금호·옥수 생활권', '성수 생활권', '응봉·마장·사근 생활권', '송정·용답 생활권'])
        self.assertTrue(all(p['page_id'] is None for p in item['neighborhoods']))
        for name in ['상왕십리동', '하왕십리동', '홍익동', '도선동', '행당동', '금호동1가', '금호동2가', '금호동3가', '금호동4가', '옥수동', '성수동1가', '성수동2가', '응봉동', '마장동', '사근동', '송정동', '용답동']:
            self.assertIn(name, text)
        self.assertIn('초등에서 중등으로 넘어갈 때 달라지는 공부 습관과 내신 준비 방법', text)
        self.assertIn('학생이 직접 한 주에 할 공부', text)
        self.assertIn('시험 후에는 틀린 문제', text)
        self.assertIn('href="seongdong/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 성동구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)

    def test_seongbuk_areas_exam_review_and_publication(self):
        item = self.builder.ids['seoul-seongbuk']
        text = self.builder.outputs['regions/seoul/seongbuk/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/seongbuk/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['길음·돈암 생활권', '정릉 생활권', '종암·월곡 생활권', '장위·석관 생활권', '성북·삼선·동선 생활권', '안암·보문 생활권'])
        self.assertTrue(all(p['page_id'] is None for p in item['neighborhoods']))
        for name in ['길음동', '돈암동', '정릉동', '종암동', '하월곡동', '상월곡동', '장위동', '석관동', '성북동', '삼선동', '동선동', '동소문동', '안암동', '보문동']:
            self.assertIn(name, text)
        self.assertIn('시험이 끝난 뒤 성적표와 오답을 활용해 다음 학기 공부 계획 세우는 방법', text)
        self.assertIn('어떤 조건을 놓쳤니?', text)
        self.assertIn('방학에는 모든 단원을 같은 분량으로', text)
        self.assertIn('href="seongbuk/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 성북구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)

    def test_songpa_living_areas_wirye_and_study_planning(self):
        item = self.builder.ids['seoul-songpa']
        text = self.builder.outputs['regions/seoul/songpa/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/songpa/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['잠실·신천 생활권', '석촌·삼전·송파 생활권', '가락·문정 생활권', '방이·오금 생활권', '풍납 생활권', '거여·마천 생활권', '장지·위례 생활권'])
        self.assertTrue(all(p['page_id'] is None for p in item['neighborhoods']))
        for name in ['잠실동', '신천동', '석촌동', '삼전동', '송파동', '가락동', '문정동', '방이동', '오금동', '풍납동', '거여동', '마천동', '장지동']:
            self.assertIn(name, text)
        self.assertIn('위례동은 법정동이 아닌 행정동 명칭', text)
        self.assertIn('인접 지자체까지 송파구로 분류하지 않습니다', text)
        self.assertIn('중·고등학생이 내신과 수능을 함께 준비할 때 학습 계획을 세우는 방법', text)
        self.assertIn('중학생의 고등학교 진학 준비는 수능 문제를 많이 푸는 일과 동일하지 않습니다', text)
        self.assertIn('href="songpa/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 송파구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)

    def test_yangcheon_legal_and_administrative_dongs_and_planning(self):
        item = self.builder.ids['seoul-yangcheon']
        text = self.builder.outputs['regions/seoul/yangcheon/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/yangcheon/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['목동 생활권', '신정동 생활권', '신월동 생활권'])
        expected = [[f'목{i}동' for i in range(1, 6)], [f'신정{i}동' for i in [1, 2, 3, 4, 6, 7]], [f'신월{i}동' for i in range(1, 8)]]
        for place, names in zip(item['neighborhoods'], expected):
            self.assertIsNone(place['page_id'])
            self.assertEqual(place['administrative_dongs'], names)
            self.assertIn('<p>행정동: ' + html.escape(' · '.join(names), quote=True) + '</p>', text)
        self.assertNotIn('신정5동', text)
        self.assertIn('목동·신정동 중고등학생, 내신과 수능을 함께 준비하는 학습 계획', text)
        self.assertIn('공통수학', text)
        self.assertIn('영어 서술형 오답', text)
        self.assertIn('href="yangcheon/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 양천구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)

    def test_yeongdeungpo_administrative_dongs_time_planning_and_publication(self):
        item = self.builder.ids['seoul-yeongdeungpo']
        text = self.builder.outputs['regions/seoul/yeongdeungpo/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/yeongdeungpo/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['여의도 생활권', '당산·양평 생활권', '문래·도림 생활권', '영등포 생활권', '신길 생활권', '대림 생활권'])
        expected = [['여의동'], ['당산1동', '당산2동', '양평1동', '양평2동'], ['문래동', '도림동'], ['영등포동', '영등포본동'], [f'신길{i}동' for i in [1, 3, 4, 5, 6, 7]], [f'대림{i}동' for i in [1, 2, 3]]]
        self.assertEqual(sum(len(names) for names in expected), 18)
        for place, names in zip(item['neighborhoods'], expected):
            self.assertIsNone(place['page_id'])
            self.assertEqual(place['administrative_dongs'], names)
            self.assertIn('<p>행정동: ' + html.escape(' · '.join(names), quote=True) + '</p>', text)
        self.assertNotIn('신길2동', text)
        self.assertIn('법정동: 여의도동', text)
        self.assertIn('중·고등학생의 부족한 공부 시간을 효율적으로 관리하는 방법', text)
        self.assertIn('실제 사용한 시간을 구분', text)
        self.assertIn('href="yeongdeungpo/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 영등포구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)

    def test_yongsan_administrative_dongs_linked_learning_and_publication(self):
        item = self.builder.ids['seoul-yongsan']
        text = self.builder.outputs['regions/seoul/yongsan/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/yongsan/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['이촌·서빙고 생활권', '한남·보광·이태원 생활권', '후암·용산 생활권', '청파·원효 생활권', '효창·용문 생활권', '한강로 생활권'])
        expected = [['이촌1동', '이촌2동', '서빙고동'], ['한남동', '보광동', '이태원1동', '이태원2동'], ['후암동', '용산2가동', '남영동'], ['청파동', '원효로1동', '원효로2동'], ['효창동', '용문동'], ['한강로동']]
        self.assertEqual(sum(len(names) for names in expected), 16)
        for place, names in zip(item['neighborhoods'], expected):
            self.assertIsNone(place['page_id'])
            self.assertEqual(place['administrative_dongs'], names)
            self.assertIn('<p>행정동: ' + html.escape(' · '.join(names), quote=True) + '</p>', text)
        self.assertNotIn('한남1동', text)
        self.assertNotIn('한남2동', text)
        self.assertIn('초등학교부터 고등학교까지 학습 격차를 줄이는 공부 계획', text)
        self.assertIn('이번 복습이 다음 단원에 어떻게 이어질까?', text)
        self.assertIn('href="yongsan/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 용산구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)

    def test_eunpyeong_administrative_dongs_transition_checklist_and_publication(self):
        item = self.builder.ids['seoul-eunpyeong']
        text = self.builder.outputs['regions/seoul/eunpyeong/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/eunpyeong/'])
        self.assertEqual([p['name'] for p in item['neighborhoods']], ['진관·은평뉴타운 생활권', '불광 생활권', '갈현·대조 생활권', '녹번·응암 생활권', '역촌·구산 생활권', '신사·증산·수색 생활권'])
        expected = [['진관동'], ['불광1동', '불광2동'], ['갈현1동', '갈현2동', '대조동'], ['녹번동', '응암1동', '응암2동', '응암3동'], ['역촌동', '구산동'], ['신사1동', '신사2동', '증산동', '수색동']]
        self.assertEqual(sum(len(names) for names in expected), 16)
        for place, names in zip(item['neighborhoods'], expected):
            self.assertIsNone(place['page_id'])
            self.assertEqual(place['administrative_dongs'], names)
            self.assertIn('<p>행정동: ' + html.escape(' · '.join(names), quote=True) + '</p>', text)
        for nonexistent in ['진관1동', '진관2동', '녹번1동', '녹번2동']:
            self.assertNotIn(nonexistent, text)
        self.assertIn('은평뉴타운은 생활권 명칭', text)
        self.assertIn('예비중·예비고 학생이 진학 전 반드시 점검해야 할 영어·수학 학습', text)
        checklist = next(section['checklist'] for section in item['sections'] if section.get('checklist'))
        self.assertEqual(len(checklist), 6)
        for question in checklist:
            self.assertIn('<li>' + html.escape(question, quote=True) + '</li>', text)
        self.assertIn('href="eunpyeong/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(service['areaServed']['name'], '서울특별시 은평구')
        self.assertIn('배정 가능 여부', service['description'])
        self.assertFalse(any(k in service for k in ['offers', 'aggregateRating', 'review', 'address']))
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn('<summary>' + html.escape(shown['question'], quote=True) + '</summary>', text)

    def test_jongno_administrative_coverage_and_matching_structured_content(self):
        item = self.builder.ids['seoul-jongno']
        text = self.builder.outputs['regions/seoul/jongno/index.html']
        doc = Document(text)
        expected = {'청운효자동', '사직동', '삼청동', '부암동', '평창동', '무악동', '교남동', '가회동', '종로1·2·3·4가동', '종로5·6가동', '이화동', '혜화동', '창신1동', '창신2동', '창신3동', '숭인1동', '숭인2동'}
        actual = [dong for area in item['neighborhoods'] for dong in area['administrative_dongs']]
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), 17)
        self.assertEqual(len(item['neighborhoods']), 7)
        self.assertTrue(all(area['page_id'] is None for area in item['neighborhoods']))
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/jongno/'])
        self.assertIn('명륜4가는 이화동', text)
        self.assertIn('href="jongno/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn('학년이 바뀌기 전 꼭 확인해야 할 영어·수학 학습 점검 방법', text)
        self.assertEqual(len(item['faq']), 6)
        schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual([s['@type'] for s in schema], ['BreadcrumbList', 'Service', 'FAQPage'])
        self.assertEqual(schema[0]['itemListElement'][-1]['item'], doc.canonical[0])
        for visible, structured in zip(item['faq'], schema[2]['mainEntity']):
            self.assertEqual(visible['question'], structured['name'])
            self.assertEqual(visible['answer'], structured['acceptedAnswer']['text'])
            self.assertIn(html.escape(visible['answer']), text)
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])

    def test_seoul_jung_coverage_and_structured_data_match(self):
        item = self.builder.ids['seoul-jung']
        text = self.builder.outputs['regions/seoul/jung/index.html']
        doc = Document(text)
        expected = {'신당동', '신당5동', '황학동', '약수동', '다산동', '청구동', '동화동', '장충동', '광희동', '필동', '명동', '소공동', '회현동', '을지로동', '중림동'}
        actual = [dong for area in item['neighborhoods'] for dong in area['administrative_dongs']]
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), 15)
        self.assertEqual(len(item['neighborhoods']), 7)
        self.assertTrue(all(area['page_id'] is None for area in item['neighborhoods']))
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/jung/'])
        self.assertTrue(item['h1'].startswith('서울 중구'))
        self.assertIn('서울특별시 중구', item['intro'])
        self.assertIn('href="jung/"', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn('중학생 내신 성적 분석부터 예비고1 영어·수학 준비까지', text)
        self.assertEqual(len(item['faq']), 7)
        schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual([s['@type'] for s in schema], ['BreadcrumbList', 'Service', 'FAQPage'])
        self.assertEqual(schema[0]['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(schema[1]['areaServed']['name'], '서울특별시 중구')
        self.assertFalse(any(k in schema[1] for k in ['address', 'review', 'offers', 'aggregateRating']))
        self.assertEqual(len(schema[2]['mainEntity']), 7)
        for visible, structured in zip(item['faq'], schema[2]['mainEntity']):
            self.assertEqual(visible['question'], structured['name'])
            self.assertEqual(visible['answer'], structured['acceptedAnswer']['text'])
            self.assertIn(html.escape(visible['answer']), text)
        self.assertIn(doc.canonical[0], self.builder.outputs['sitemap.xml'])

    def test_jungnang_and_all_25_seoul_districts_are_published(self):
        seoul = self.builder.ids['seoul']
        expected_names = {'강남구', '강동구', '강북구', '강서구', '관악구', '광진구', '구로구', '금천구', '노원구', '도봉구', '동대문구', '동작구', '마포구', '서대문구', '서초구', '성동구', '성북구', '송파구', '양천구', '영등포구', '용산구', '은평구', '종로구', '중구', '중랑구'}
        self.assertEqual({d['name'] for d in seoul['districts']}, expected_names)
        self.assertEqual(len({d['page_id'] for d in seoul['districts']}), 25)
        for district in seoul['districts']:
            item = self.builder.ids[district['page_id']]
            self.assertEqual(item['parent_id'], 'seoul')
            self.assertEqual(item['status'], 'published')
            path = region_path(item, self.builder.ids)
            self.assertIn(path, self.builder.outputs)
            self.assertIn('href="' + district['slug'] + '/"', self.builder.outputs['regions/seoul/index.html'])
            self.assertIn(self.builder.canonical(path), self.builder.outputs['sitemap.xml'])
            doc = Document(self.builder.outputs[path])
            self.assertTrue(any(link.get('href') == '../' for link in doc.links))
            self.assertTrue(any(link.get('href') == 'tel:01043776964' for link in doc.links))
        item = self.builder.ids['seoul-jungnang']
        actual = [d for area in item['neighborhoods'] for d in area['administrative_dongs']]
        expected = {'면목본동', '면목2동', '면목3·8동', '면목4동', '면목5동', '면목7동', '상봉1동', '상봉2동', '중화1동', '중화2동', '묵1동', '묵2동', '망우본동', '망우3동', '신내1동', '신내2동'}
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), 16)
        self.assertEqual(len(item['neighborhoods']), 7)
        self.assertTrue(all(area['page_id'] is None for area in item['neighborhoods']))
        text = self.builder.outputs['regions/seoul/jungnang/index.html']
        doc = Document(text)
        self.assertEqual(''.join(doc.title), item['title'])
        self.assertEqual(doc.description, [item['description']])
        self.assertEqual(doc.canonical, [self.builder.base + 'regions/seoul/jungnang/'])
        self.assertIn('중학생 내신 오답 분석부터 예비고1 영어·수학 준비까지', text)
        schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(schema[1]['areaServed']['name'], '서울특별시 중랑구')
        self.assertEqual(schema[0]['itemListElement'][-1]['item'], doc.canonical[0])
        self.assertEqual(len(schema[2]['mainEntity']), 7)
        for visible, structured in zip(item['faq'], schema[2]['mainEntity']):
            self.assertEqual(visible['question'], structured['name'])
            self.assertEqual(visible['answer'], structured['acceptedAnswer']['text'])
            self.assertIn(html.escape(visible['answer']), text)

    def test_all_seoul_district_social_metadata_and_schemas_match_visible_content(self):
        for district in self.builder.ids['seoul']['districts']:
            item = self.builder.ids[district['page_id']]
            path = region_path(item, self.builder.ids)
            text = self.builder.outputs[path]
            doc = Document(text)
            self.assertEqual(doc.lang, 'ko', path)
            self.assertEqual(doc.viewport, ['width=device-width, initial-scale=1'], path)
            self.assertFalse(any('noindex' in r.lower() or 'nofollow' in r.lower() for r in doc.robots), path)
            self.assertEqual(doc.og.get('og:title'), [item['title']], path)
            self.assertEqual(doc.og.get('og:description'), [item['description']], path)
            self.assertEqual(doc.og.get('og:url'), [self.builder.canonical(path)], path)
            schema = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
            breadcrumb, service, faq = schema
            self.assertEqual(breadcrumb['itemListElement'][-1]['item'], self.builder.canonical(path), path)
            self.assertEqual(service['url'], self.builder.canonical(path), path)
            self.assertEqual(service['areaServed']['name'], item['official_name'], path)
            self.assertFalse(any(k in service for k in ['address', 'review', 'aggregateRating', 'offers']), path)
            self.assertEqual(len(faq['mainEntity']), len(item['faq']), path)
            for shown, structured in zip(item['faq'], faq['mainEntity']):
                self.assertEqual(structured['name'], shown['question'], path)
                self.assertEqual(structured['acceptedAnswer']['text'], shown['answer'], path)
                self.assertIn('<summary>' + html.escape(shown['question']) + '</summary>', text, path)
                self.assertIn('<p>' + html.escape(shown['answer']) + '</p>', text, path)

    def test_seoul_publication_notice_tracks_available_districts(self):
        path = 'regions/seoul/index.html'
        complete = self.builder.outputs[path]
        self.assertIn('서울 25개 자치구 상세 안내가 모두 연결되어 있습니다.', complete)
        self.assertNotIn('나머지 자치구는 아직 별도 상세 링크가 없습니다.', complete)
        self.builder.ids['seoul-gangnam']['status'] = 'draft'
        self.builder.build_city_guide(self.builder.ids['seoul'])
        partial = self.builder.outputs[path]
        self.assertNotIn('25개 자치구 상세 안내가 모두 연결', partial)
        self.assertIn('나머지 자치구는 아직 별도 상세 링크가 없습니다.', partial)
        self.assertNotIn('href="gangnam/"', partial)

    def test_busan_hub_and_16_districts_use_their_own_parent_and_content(self):
        city = self.builder.ids['busan']
        expected = {'중구', '서구', '동구', '영도구', '부산진구', '동래구', '남구', '북구', '해운대구', '사하구', '금정구', '강서구', '연제구', '수영구', '사상구', '기장군'}
        self.assertEqual(city['status'], 'published')
        self.assertEqual({d['name'] for d in city['districts']}, expected)
        self.assertEqual(len(city['districts']), 16)
        hub = self.builder.outputs['regions/busan/index.html']
        self.assertIn('부산 16개 구·군 상세 안내가 모두 연결', hub)
        self.assertIn('href="busan/"', self.builder.outputs['regions/index.html'])
        topics = set()
        for card in city['districts']:
            item = self.builder.ids[card['page_id']]
            path = region_path(item, self.builder.ids)
            text = self.builder.outputs[path]
            self.assertEqual(item['parent_id'], 'busan')
            self.assertEqual(item['status'], 'published')
            self.assertIn('href="' + item['slug'] + '/"', hub)
            self.assertIn('부산 과외 대표 안내', text)
            self.assertNotIn('서울 대표 페이지', text)
            self.assertIn(self.builder.canonical(path), self.builder.outputs['sitemap.xml'])
            info = next(s for s in item['sections'] if s.get('checklist'))
            topics.add(info['heading'])
            self.assertGreaterEqual(len(info['paragraphs']), 3)
            self.assertTrue(all(n['page_id'] is None for n in item['neighborhoods']))
            breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
            self.assertEqual(breadcrumb['itemListElement'][2]['name'], '부산 과외')
            self.assertEqual(breadcrumb['itemListElement'][2]['item'], self.builder.base + 'regions/busan/')
            self.assertEqual(service['areaServed']['containedInPlace']['name'], '부산광역시')
            self.assertEqual(service['areaServed']['name'], '부산광역시 ' + card['name'])
            self.assertEqual(len(faq['mainEntity']), 5)
            for shown, structured in zip(item['faq'], faq['mainEntity']):
                self.assertEqual(shown['answer'], structured['acceptedAnswer']['text'])
                self.assertIn(html.escape(shown['question']), text)
        self.assertEqual(len(topics), 16)
        self.assertIn('일광읍', self.builder.outputs['regions/busan/gijang/index.html'])
        self.assertIn('기장군은 자치구가 아닌', self.builder.outputs['regions/busan/gijang/index.html'])

    def test_daegu_hub_and_nine_districts_include_gunwi_and_correct_parent(self):
        city = self.builder.ids['daegu']
        self.assertEqual(city['status'], 'published')
        self.assertEqual({d['name'] for d in city['districts']}, {'중구', '동구', '서구', '남구', '북구', '수성구', '달서구', '달성군', '군위군'})
        self.assertEqual(len(city['districts']), 9)
        hub = self.builder.outputs['regions/daegu/index.html']
        self.assertIn('대구 9개 구·군 상세 안내가 모두 연결', hub)
        self.assertIn('7개 자치구', hub)
        self.assertIn('href="daegu/"', self.builder.outputs['regions/index.html'])
        topics = set()
        for card in city['districts']:
            item = self.builder.ids[card['page_id']]
            text = self.builder.outputs[region_path(item, self.builder.ids)]
            self.assertIn('href="' + card['slug'] + '/"', hub)
            self.assertIn('대구 과외 대표 안내', text)
            self.assertNotIn('서울 대표 페이지', text)
            self.assertNotIn('부산 대표 페이지', text)
            info = next(s for s in item['sections'] if s.get('checklist'))
            topics.add(info['heading'])
            self.assertGreaterEqual(len(info['paragraphs']), 3)
            breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
            self.assertEqual(breadcrumb['itemListElement'][2]['name'], '대구 과외')
            self.assertEqual(breadcrumb['itemListElement'][2]['item'], self.builder.base + 'regions/daegu/')
            self.assertEqual(service['areaServed']['containedInPlace']['name'], '대구광역시')
            self.assertEqual(service['areaServed']['name'], '대구광역시 ' + card['name'])
            self.assertEqual(len(faq['mainEntity']), 5)
            for shown, structured in zip(item['faq'], faq['mainEntity']):
                self.assertEqual(shown['question'], structured['name'])
                self.assertEqual(shown['answer'], structured['acceptedAnswer']['text'])
            self.assertIn(service['url'], self.builder.outputs['sitemap.xml'])
        self.assertEqual(len(topics), 9)
        self.assertIn('삼국유사면', self.builder.outputs['regions/daegu/gunwi/index.html'])
        self.assertIn('대구광역시에 속하는 군', self.builder.outputs['regions/daegu/gunwi/index.html'])

    def test_gyeonggi_17_boroughs_hierarchy_sources_links_schema_and_guards(self):
        expected = {
            'suwon': {'yeongtong': '영통구', 'jangan': '장안구', 'gwonseon': '권선구', 'paldal': '팔달구'},
            'yongin': {'suji': '수지구', 'giheung': '기흥구', 'cheoin': '처인구'},
            'seongnam': {'bundang': '분당구', 'sujeong': '수정구', 'jungwon': '중원구'},
            'goyang': {'ilsandong': '일산동구', 'ilsanseo': '일산서구', 'deogyang': '덕양구'},
            'anyang': {'dongan': '동안구', 'manan': '만안구'},
            'ansan': {'danwon': '단원구', 'sangnok': '상록구'},
        }
        source = json.loads((ROOT / 'data/seo/gyeonggi_borough_geography.json').read_text())
        refs = {r['page_id']: r for r in source['boroughs']}
        self.assertEqual(len(refs), 17)
        self.assertEqual(source['source']['version'], '20261001')
        boroughs = [r for r in self.builder.regions if r['kind'] == 'borough' and r['parent_id'].startswith('gyeonggi-')]
        self.assertEqual(len(boroughs), 17)
        topics = set()
        sitemap_urls = [r.text for r in ET.fromstring(self.builder.outputs['sitemap.xml']).iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
        self.assertEqual(len(sitemap_urls), 181)
        self.assertEqual(len(set(sitemap_urls)), 181)
        for city_slug, targets in expected.items():
            parent = self.builder.ids['gyeonggi-' + city_slug]
            parent_path = region_path(parent, self.builder.ids)
            parent_text = self.builder.outputs[parent_path]
            self.assertEqual({x['slug']: x['name'] for x in parent['boroughs']}, targets)
            for slug, name in targets.items():
                item = self.builder.ids[parent['id'] + '-' + slug]
                path = region_path(item, self.builder.ids)
                self.assertEqual(path, 'regions/gyeonggi/' + city_slug + '/' + slug + '/index.html')
                text = self.builder.outputs[path]
                self.assertEqual(item['parent_id'], parent['id'])
                self.assertEqual(item['official_name'], parent['official_name'] + ' ' + name)
                self.assertIn('href="' + slug + '/"', parent_text)
                self.assertIn('href="../"', text)
                self.assertIn('href="../../"', text)
                self.assertIn('tel:01043776964', text)
                self.assertNotIn('1:1', json.dumps(item, ensure_ascii=False))
                self.assertTrue(confirmed_operator_coverage(item))
                actual_dongs = {d for p in item['neighborhoods'] for d in p['administrative_dongs']}
                self.assertEqual(actual_dongs, {d['name'] for d in refs[item['id']]['administrative_dongs']})
                topics.add(next(s['heading'] for s in item['sections'] if s.get('checklist')))
                doc = Document(text)
                canonical = self.builder.base + path.removesuffix('index.html')
                self.assertEqual(doc.canonical, [canonical])
                self.assertEqual(doc.og['og:url'], [canonical])
                self.assertIn(canonical, sitemap_urls)
                breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
                trail = breadcrumb['itemListElement']
                self.assertEqual(len(trail), 5)
                self.assertEqual(trail[2]['item'], self.builder.base + 'regions/gyeonggi/')
                self.assertEqual(trail[3]['item'], self.builder.canonical(parent_path))
                self.assertEqual(trail[4]['item'], canonical)
                self.assertEqual(service['areaServed']['name'], item['official_name'])
                self.assertEqual(service['areaServed']['containedInPlace']['name'], parent['official_name'])
                self.assertEqual(service['areaServed']['containedInPlace']['containedInPlace']['name'], '경기도')
                self.assertFalse(any(k in service for k in ('offers', 'aggregateRating', 'review', 'address')))
                self.assertEqual(len(faq['mainEntity']), 5)
                for shown, structured in zip(item['faq'], faq['mainEntity']):
                    self.assertEqual(shown['question'], structured['name'])
                    self.assertEqual(shown['answer'], structured['acceptedAnswer']['text'])
        self.assertEqual(len(topics), 17)
        invalid = copy.deepcopy(self.builder.regions)
        next(r for r in invalid if r['kind'] == 'borough')['parent_id'] = 'gyeonggi'
        with self.assertRaises(ValueError):
            validate_regions(invalid)
        invalid = copy.deepcopy(self.builder.regions)
        next(r for r in invalid if r['kind'] == 'borough')['parent_id'] = 'gyeonggi-gapyeong'
        with self.assertRaises(ValueError):
            validate_regions(invalid)

    def test_gyeonggi_hub_and_31_cities_counties_have_correct_hierarchy_and_unique_content(self):
        city = self.builder.ids['gyeonggi']
        expected = {'수원시', '성남시', '의정부시', '안양시', '부천시', '광명시', '평택시', '동두천시', '안산시', '고양시', '과천시', '구리시', '남양주시', '오산시', '시흥시', '군포시', '의왕시', '하남시', '용인시', '파주시', '이천시', '안성시', '김포시', '화성시', '광주시', '양주시', '포천시', '여주시', '연천군', '가평군', '양평군'}
        self.assertEqual(city['status'], 'published')
        self.assertEqual(city['official_name'], '경기도')
        self.assertEqual(city['district_label'], '시·군')
        self.assertEqual(len(city['districts']), 31)
        self.assertEqual({r['name'] for r in city['districts']}, expected)
        self.assertEqual(sum(r['name'].endswith('군') for r in city['districts']), 3)
        hub = self.builder.outputs['regions/gyeonggi/index.html']
        self.assertIn('경기도 31개 시·군 상세 안내가 모두 연결', hub)
        self.assertIn('href="gyeonggi/"', self.builder.outputs['regions/index.html'])
        topics = set()
        for card in city['districts']:
            item = self.builder.ids[card['page_id']]
            path = region_path(item, self.builder.ids)
            text = self.builder.outputs[path]
            self.assertEqual(item['parent_id'], 'gyeonggi')
            self.assertEqual(item['official_name'], '경기도 ' + item['name'])
            self.assertIn('href="' + card['slug'] + '/"', hub)
            self.assertIn('경기도 과외 대표 안내', text)
            self.assertIn('tel:01043776964', text)
            self.assertTrue(all(r['kind'] == 'borough' for r in self.builder.regions if r.get('parent_id') == item['id']))
            info = next(r for r in item['sections'] if r.get('checklist'))
            self.assertGreaterEqual(len(info['paragraphs']), 3)
            topics.add(info['heading'])
            doc = Document(text)
            self.assertEqual(doc.canonical, [self.builder.base + path.removesuffix('index.html')])
            breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
            self.assertEqual(breadcrumb['itemListElement'][2]['name'], '경기도 과외')
            self.assertEqual(service['areaServed']['containedInPlace']['name'], '경기도')
            self.assertEqual(service['areaServed']['name'], item['official_name'])
            self.assertEqual(len(faq['mainEntity']), 5)
            for shown, entry in zip(item['faq'], faq['mainEntity']):
                self.assertEqual(entry['name'], shown['question'])
                self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
            self.assertIn(service['url'], self.builder.outputs['sitemap.xml'])
        self.assertEqual(len(topics), 31)
        self.assertIn('광주광역시와 다른 지역', self.builder.outputs['regions/gyeonggi/gwangju/index.html'])
        self.assertEqual(self.builder.ids['gwangju']['official_name'], '광주광역시')

    def test_sejong_single_tier_page_has_area_cards_without_fake_districts(self):
        item = self.builder.ids['sejong']
        self.assertEqual(item['kind'], 'province')
        self.assertEqual(item['status'], 'published')
        self.assertEqual(item['official_name'], '세종특별자치시')
        self.assertFalse(any(r.get('parent_id') == 'sejong' for r in self.builder.regions))
        self.assertNotIn('districts', item)
        text = self.builder.outputs['regions/sejong/index.html']
        doc = Document(text)
        canonical = self.builder.base + 'regions/sejong/'
        self.assertEqual(doc.canonical, [canonical])
        self.assertEqual(doc.og['og:url'], [canonical])
        self.assertEqual(doc.h1, 1)
        self.assertIn('세종 과외', ''.join(doc.title))
        self.assertIn('href="sejong/"', self.builder.outputs['regions/index.html'])
        self.assertIn('자치구가 없는', text)
        self.assertNotIn('0개 자치구', text)
        self.assertNotIn('자치구별 상세 페이지는', text)
        self.assertEqual(text.count('<article class="district-card">'), 6)
        for section in item['sections']:
            for card in section.get('area_cards', []):
                self.assertIn(html.escape(card['heading']), text)
                self.assertIn(html.escape(card['description']), text)
            for question in section.get('checklist', []):
                self.assertIn('<li>' + html.escape(question) + '</li>', text)
        self.assertIn('거주 읍·면·동, 희망 수업 방식', text)
        breadcrumb, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['item'], canonical)
        self.assertEqual(len(faq['mainEntity']), 6)
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
        self.assertIn(canonical, self.builder.outputs['sitemap.xml'])

    def test_ulsan_hub_and_five_districts_use_metropolitan_parent_and_unique_topics(self):
        city = self.builder.ids['ulsan']
        self.assertEqual(city['status'], 'published')
        self.assertEqual({d['name'] for d in city['districts']}, {'중구', '남구', '동구', '북구', '울주군'})
        self.assertEqual(len(city['districts']), 5)
        hub = self.builder.outputs['regions/ulsan/index.html']
        self.assertIn('울산 5개 구·군 상세 안내가 모두 연결', hub)
        self.assertIn('href="ulsan/"', self.builder.outputs['regions/index.html'])
        topics = set()
        for card in city['districts']:
            item = self.builder.ids[card['page_id']]
            text = self.builder.outputs[region_path(item, self.builder.ids)]
            self.assertIn('href="' + card['slug'] + '/"', hub)
            self.assertIn('울산 과외 대표 안내', text)
            self.assertNotIn('서울 대표 페이지', text)
            self.assertNotIn('부산 대표 페이지', text)
            info = next(s for s in item['sections'] if s.get('checklist'))
            topics.add(info['heading'])
            self.assertGreaterEqual(len(info['paragraphs']), 3)
            breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
            self.assertEqual(breadcrumb['itemListElement'][2]['name'], '울산 과외')
            self.assertEqual(breadcrumb['itemListElement'][2]['item'], self.builder.base + 'regions/ulsan/')
            self.assertEqual(service['areaServed']['containedInPlace']['name'], '울산광역시')
            self.assertEqual(service['areaServed']['name'], '울산광역시 ' + card['name'])
            self.assertEqual(len(faq['mainEntity']), 5)
            for shown, structured in zip(item['faq'], faq['mainEntity']):
                self.assertEqual(shown['question'], structured['name'])
                self.assertEqual(shown['answer'], structured['acceptedAnswer']['text'])
            self.assertIn(service['url'], self.builder.outputs['sitemap.xml'])
        self.assertEqual(len(topics), 5)
        self.assertIn('울산광역시', hub)
        ulju = self.builder.ids['ulsan-ulju']
        self.assertEqual({n['name'] for n in ulju['neighborhoods']}, {'범서읍', '언양읍', '온산읍', '온양읍', '청량읍', '삼남읍', '두동면', '두서면', '상북면', '삼동면', '웅촌면', '서생면'})
        self.assertIn('울산광역시에 속하는 군', self.builder.outputs['regions/ulsan/ulju/index.html'])

    def test_daejeon_hub_and_five_districts_use_metropolitan_parent_and_unique_topics(self):
        city = self.builder.ids['daejeon']
        self.assertEqual(city['status'], 'published')
        self.assertEqual({d['name'] for d in city['districts']}, {'동구', '중구', '서구', '유성구', '대덕구'})
        self.assertEqual(len(city['districts']), 5)
        hub = self.builder.outputs['regions/daejeon/index.html']
        self.assertIn('대전 5개 자치구 상세 안내가 모두 연결', hub)
        self.assertIn('href="daejeon/"', self.builder.outputs['regions/index.html'])
        topics = set()
        for card in city['districts']:
            item = self.builder.ids[card['page_id']]
            text = self.builder.outputs[region_path(item, self.builder.ids)]
            self.assertIn('href="' + card['slug'] + '/"', hub)
            self.assertIn('대전 과외 대표 안내', text)
            self.assertNotIn('서울 대표 페이지', text)
            self.assertNotIn('부산 대표 페이지', text)
            info = next(s for s in item['sections'] if s.get('checklist'))
            topics.add(info['heading'])
            self.assertGreaterEqual(len(info['paragraphs']), 3)
            breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
            self.assertEqual(breadcrumb['itemListElement'][2]['name'], '대전 과외')
            self.assertEqual(breadcrumb['itemListElement'][2]['item'], self.builder.base + 'regions/daejeon/')
            self.assertEqual(service['areaServed']['containedInPlace']['name'], '대전광역시')
            self.assertEqual(service['areaServed']['name'], '대전광역시 ' + card['name'])
            self.assertEqual(len(faq['mainEntity']), 5)
            for shown, structured in zip(item['faq'], faq['mainEntity']):
                self.assertEqual(shown['question'], structured['name'])
                self.assertEqual(shown['answer'], structured['acceptedAnswer']['text'])
            self.assertIn(service['url'], self.builder.outputs['sitemap.xml'])
        self.assertEqual(len(topics), 5)
        self.assertIn('대전광역시', hub)

    def test_gwangju_hub_and_five_districts_use_metropolitan_parent_and_unique_topics(self):
        city = self.builder.ids['gwangju']
        self.assertEqual(city['status'], 'published')
        self.assertEqual({d['name'] for d in city['districts']}, {'동구', '서구', '남구', '북구', '광산구'})
        self.assertEqual(len(city['districts']), 5)
        hub = self.builder.outputs['regions/gwangju/index.html']
        self.assertIn('광주 5개 자치구 상세 안내가 모두 연결', hub)
        self.assertIn('href="gwangju/"', self.builder.outputs['regions/index.html'])
        topics = set()
        for card in city['districts']:
            item = self.builder.ids[card['page_id']]
            text = self.builder.outputs[region_path(item, self.builder.ids)]
            self.assertIn('href="' + card['slug'] + '/"', hub)
            self.assertIn('광주 과외 대표 안내', text)
            self.assertNotIn('서울 대표 페이지', text)
            self.assertNotIn('부산 대표 페이지', text)
            info = next(s for s in item['sections'] if s.get('checklist'))
            topics.add(info['heading'])
            self.assertGreaterEqual(len(info['paragraphs']), 3)
            breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
            self.assertEqual(breadcrumb['itemListElement'][2]['name'], '광주 과외')
            self.assertEqual(breadcrumb['itemListElement'][2]['item'], self.builder.base + 'regions/gwangju/')
            self.assertEqual(service['areaServed']['containedInPlace']['name'], '광주광역시')
            self.assertEqual(service['areaServed']['name'], '광주광역시 ' + card['name'])
            self.assertEqual(len(faq['mainEntity']), 5)
            for shown, structured in zip(item['faq'], faq['mainEntity']):
                self.assertEqual(shown['question'], structured['name'])
                self.assertEqual(shown['answer'], structured['acceptedAnswer']['text'])
            self.assertIn(service['url'], self.builder.outputs['sitemap.xml'])
        self.assertEqual(len(topics), 5)
        self.assertIn('경기도 광주시와 구분', hub)

    def test_incheon_reorganized_hub_and_eleven_districts_match_parent_and_faq(self):
        city = self.builder.ids['incheon']
        self.assertEqual(city['status'], 'published')
        self.assertEqual({d['name'] for d in city['districts']}, {'제물포구', '영종구', '미추홀구', '연수구', '남동구', '부평구', '계양구', '서해구', '검단구', '강화군', '옹진군'})
        self.assertEqual(len(city['districts']), 11)
        hub = self.builder.outputs['regions/incheon/index.html']
        self.assertIn('인천 11개 구·군 상세 안내가 모두 연결', hub)
        self.assertIn('9개 구', hub)
        self.assertIn('href="incheon/"', self.builder.outputs['regions/index.html'])
        topics = set()
        for card in city['districts']:
            item = self.builder.ids[card['page_id']]
            text = self.builder.outputs[region_path(item, self.builder.ids)]
            self.assertIn('href="' + card['slug'] + '/"', hub)
            self.assertIn('인천 과외 대표 안내', text)
            self.assertNotIn('서울 대표 페이지', text)
            self.assertNotIn('부산 대표 페이지', text)
            info = next(s for s in item['sections'] if s.get('checklist'))
            topics.add(info['heading'])
            self.assertGreaterEqual(len(info['paragraphs']), 3)
            breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
            self.assertEqual(breadcrumb['itemListElement'][2]['name'], '인천 과외')
            self.assertEqual(breadcrumb['itemListElement'][2]['item'], self.builder.base + 'regions/incheon/')
            self.assertEqual(service['areaServed']['containedInPlace']['name'], '인천광역시')
            self.assertEqual(service['areaServed']['name'], '인천광역시 ' + card['name'])
            self.assertEqual(len(faq['mainEntity']), 5)
            for shown, structured in zip(item['faq'], faq['mainEntity']):
                self.assertEqual(shown['question'], structured['name'])
                self.assertEqual(shown['answer'], structured['acceptedAnswer']['text'])
            self.assertIn(service['url'], self.builder.outputs['sitemap.xml'])
        self.assertEqual(len(topics), 11)
        self.assertNotIn('incheon-jung', self.builder.ids)
        self.assertNotIn('incheon-dong', self.builder.ids)

    def test_incheon_seohae_name_preserves_seo_url_and_district_scope(self):
        item = self.builder.ids['incheon-seo']
        self.assertEqual(item['name'], '서해구')
        self.assertEqual(item['official_name'], '인천광역시 서해구')
        self.assertEqual(item['slug'], 'seo')
        path = region_path(item, self.builder.ids)
        self.assertEqual(path, 'regions/incheon/seo/index.html')
        text = self.builder.outputs[path]
        doc = Document(text)
        canonical = self.builder.base + 'regions/incheon/seo/'
        self.assertEqual(doc.canonical, [canonical])
        self.assertEqual(doc.og['og:url'], [canonical])
        self.assertIn('인천 서해구', ''.join(doc.title))
        self.assertIn('인천 서해구', item['h1'])
        self.assertIn('인천 서해구', doc.description[0])
        self.assertIn('인천 서해구 과외', text)
        self.assertIn('2026년 7월 1일', text)
        breadcrumb, service, faq = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)[1])
        self.assertEqual(breadcrumb['itemListElement'][-1]['name'], '서해구 과외')
        self.assertEqual(service['areaServed']['name'], '인천광역시 서해구')
        self.assertEqual(service['url'], canonical)
        self.assertEqual(len(faq['mainEntity']), len(item['faq']))
        for shown, entry in zip(item['faq'], faq['mainEntity']):
            self.assertEqual(entry['name'], shown['question'])
            self.assertEqual(entry['acceptedAnswer']['text'], shown['answer'])
        own = {n['name'] for n in item['neighborhoods']}
        other = {n['name'] for n in self.builder.ids['incheon-geomdan']['neighborhoods']}
        self.assertFalse(own & other)
        self.assertEqual(len(own), 10)
        hub = self.builder.outputs['regions/incheon/index.html']
        self.assertIn('href="seo/"', hub)
        self.assertIn('서해구 과외', hub)
        self.assertIn(canonical, self.builder.outputs['sitemap.xml'])
        self.assertEqual(self.builder.ids['busan-seo']['name'], '서구')
        self.assertEqual(self.builder.ids['daegu-seo']['name'], '서구')

    def test_confirmed_individual_lessons_render_in_relevant_guides(self):
        confirmation = self.builder.site['lesson_format']
        self.assertEqual(confirmation['students_per_lesson'], 1)
        self.assertEqual(set(confirmation['modes']), {'visit', 'online'})
        self.assertEqual(confirmation['confirmed_by'], 'site_operator')
        expected = {'visit': '1:1 방문과외', 'online': '1:1 화상과외', 'elementary': '초등학생 1:1 과외', 'middle': '중학생 1:1 과외', 'high': '고등학생 1:1 과외', 'english': '1:1 영어과외', 'math': '1:1 수학과외', 'korean': '1:1 국어과외'}
        for slug, keyword in expected.items():
            text = self.builder.outputs[f'guides/{slug}/index.html']
            self.assertIn(keyword, text)
            self.assertIn(keyword, self.builder.guide_ids[slug]['intro'])
        self.assertIn('일대일 과외', self.builder.outputs['guides/social/index.html'])
        self.assertIn('서울 1:1 과외', self.builder.outputs['regions/seoul/index.html'])
        self.assertIn('은평구 1:1 과외', self.builder.outputs['regions/seoul/eunpyeong/index.html'])

    def test_grade_and_subject_guide_content_is_not_location_substitution(self):
        bodies = [''.join(''.join(section['paragraphs']) for section in page['sections']) for page in self.builder.guides]
        self.assertEqual(len(bodies), len(set(bodies)))
        self.assertTrue(all(len(body) > 200 for body in bodies))


if __name__ == '__main__':
    unittest.main()
