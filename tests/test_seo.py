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
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
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
    def setUp(self):
        self.builder = Builder()
        self.builder.build()

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
        self.assertEqual(len(faq['mainEntity']), 6)
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

    def test_grade_and_subject_guide_content_is_not_location_substitution(self):
        bodies = [''.join(''.join(section['paragraphs']) for section in page['sections']) for page in self.builder.guides]
        self.assertEqual(len(bodies), len(set(bodies)))
        self.assertTrue(all(len(body) > 200 for body in bodies))


if __name__ == '__main__':
    unittest.main()
