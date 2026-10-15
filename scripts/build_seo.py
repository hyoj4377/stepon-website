#!/usr/bin/env python3
"""Build reviewed static guides and sitemap. No third-party dependency required."""
import argparse
import base64
import hashlib
from difflib import SequenceMatcher
import html
import json
import posixpath
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/seo'
MANIFEST = DATA / 'generated.json'
KINDS = {'province': None, 'district': 'province', 'neighborhood': 'district', 'school': 'neighborhood', 'learning': 'school'}
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'


def read(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


def esc(value):
    return html.escape(str(value), quote=True)


def slug_ok(value):
    return isinstance(value, str) and re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value)


def verified_source(source, school=False):
    try:
        parsed = urlsplit(source['url'])
        checked = date.fromisoformat(source['checked_on'])
        host = parsed.hostname or ''
        official = host == 'schoolinfo.go.kr' or host.endswith('.go.kr') or host.endswith('.ed.kr')
        return parsed.scheme == 'https' and official and source.get('verified') is True and checked <= date.today() and (not school or source.get('type') == 'official_school')
    except (KeyError, TypeError, ValueError):
        return False


def validate_regions(regions):
    ids = {}
    for item in regions:
        if not slug_ok(item.get('id')) or not slug_ok(item.get('slug')) or item.get('kind') not in KINDS:
            raise ValueError('Invalid region ID, slug, or kind')
        if item['id'] in ids:
            raise ValueError('Duplicate region ID: ' + item['id'])
        if item.get('status') not in {'draft', 'published'}:
            raise ValueError('Unknown region publication status')
        ids[item['id']] = item
    for item in regions:
        kind = item['kind']
        if kind == 'province':
            if item.get('parent_id') is not None:
                raise ValueError('Province cannot have a parent')
        else:
            parent = ids.get(item.get('parent_id'))
            if not parent or parent['kind'] != KINDS[kind]:
                raise ValueError('Invalid hierarchy: ' + item['id'])
        if item['status'] == 'published':
            problems = publication_problems(item, ids)
            if problems:
                raise ValueError(item['id'] + ': ' + '; '.join(problems))
    paths = [region_path(item, ids) for item in regions]
    if len(paths) != len(set(paths)):
        raise ValueError('Duplicate region URL')
    return ids


def confirmed_operator_coverage(item):
    confirmation = item.get('service_confirmation', {})
    try:
        checked = date.fromisoformat(confirmation['confirmed_on'])
        return item['kind'] in {'province', 'district'} and confirmation.get('confirmed_by') == 'site_operator' and confirmation.get('region_id') == item['id'] and confirmation.get('coverage_confirmed') is True and bool(confirmation.get('scope')) and checked <= date.today()
    except (KeyError, TypeError, ValueError):
        return False


def publication_problems(item, ids):
    problems = []
    review = item.get('review', {})
    if review.get('approved') is not True or not review.get('reviewed_on'):
        problems.append('Editorial approval and review date required')
    else:
        try:
            if date.fromisoformat(review['reviewed_on']) > date.today():
                problems.append('Review date cannot be in the future')
        except ValueError:
            problems.append('Invalid review date')
    sources = item.get('sources', [])
    if not any(verified_source(s) for s in sources) and not confirmed_operator_coverage(item):
        problems.append('Verified official source or explicit operator-confirmed province/district coverage required')
    sections = item.get('sections', [])
    body = item.get('intro', '') + ''.join(''.join(s.get('paragraphs', [])) for s in sections)
    if len(sections) < 3 or len(body) < 600 or any(not s.get('local_relevance') for s in sections):
        problems.append('At least 3 locally relevant sections and substantive content required')
    if not item.get('title') or not item.get('description') or not item.get('intro'):
        problems.append('Complete metadata and introduction required')
    parent = ids.get(item.get('parent_id'))
    if parent and parent['status'] != 'published':
        problems.append('Parent page must be published first')
    if item['kind'] == 'school':
        school = item.get('school') or {}
        if not school.get('official_name') or not school.get('official_code') or not any(verified_source(s, school=True) for s in sources):
            problems.append('Official school name, code and checked school source required')
        if school.get('non_affiliation_notice') is not True:
            problems.append('School non-affiliation disclosure required')
    if item['kind'] == 'learning' and (item.get('grade') not in {'elementary', 'middle', 'high'} or item.get('subject') not in {'english', 'math', 'korean', 'social', 'science'}):
        problems.append('Explicit supported grade and subject required')
    return problems


def region_path(item, ids):
    parts = [item['slug']]
    while item.get('parent_id'):
        item = ids[item['parent_id']]
        parts.insert(0, item['slug'])
    return 'regions/' + '/'.join(parts) + '/index.html'


CSS = '''
:root{--navy:#112c40;--ink:#173043;--muted:#63717a;--gold:#b69a68;--paper:#f7f8f6;--line:#dfe5e6}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Noto Sans KR","Segoe UI",sans-serif;color:var(--ink);line-height:1.9;word-break:keep-all}a{color:inherit;text-decoration:none}a:focus-visible,summary:focus-visible{outline:3px solid var(--gold);outline-offset:4px}h1,h2,h3,p{margin:0}h1,h2,h3{line-height:1.5;letter-spacing:-.04em}.wrap{width:min(1120px,calc(100% - 80px));margin:auto}header{border-bottom:1px solid var(--line);background:white}.header-inner{display:flex;align-items:center;justify-content:space-between;gap:24px;min-height:90px}.brand{display:flex;align-items:center;gap:12px;white-space:nowrap;font-size:21px;font-weight:600}.brand img{width:54px;height:54px;object-fit:contain}nav{display:flex;flex-wrap:wrap;gap:24px;font-size:13px}nav a{display:inline-flex;align-items:center;min-height:44px}.breadcrumb{padding-top:26px;font-size:11px;color:var(--muted);display:flex;flex-wrap:wrap;gap:10px}.eyebrow{font-size:10px;color:#8b754e;letter-spacing:.16em;font-weight:600;margin-bottom:18px}.hero{background:var(--paper);padding:55px 0 65px}.hero-grid{display:grid;grid-template-columns:1.2fr 1fr;gap:64px;align-items:center}.hero h1{font-size:37px;font-weight:600}.intro{margin-top:22px;font-size:15px;color:var(--muted)}.photo{width:100%;height:auto;aspect-ratio:1672/941;object-fit:cover;object-position:center;border-radius:8px;display:block}.button{display:inline-flex;justify-content:space-between;align-items:center;gap:30px;min-height:50px;padding:13px 20px;background:var(--navy);color:white;border-radius:4px;font-size:13px}.hero .button{margin-top:25px}.section{padding:66px 0}.section h2{font-size:28px;font-weight:600;margin-bottom:20px}.lead{color:var(--muted);font-size:14px;max-width:780px;margin-bottom:30px}.content-grid{display:grid;grid-template-columns:minmax(0,1.75fr) minmax(0,1fr);gap:65px}.article-section{padding-bottom:35px;margin-bottom:30px;border-bottom:1px solid var(--line)}.article-section h2{font-size:24px}.article-section p{font-size:14px;color:var(--muted);margin-bottom:16px}.article-section ul{margin:0;padding-left:22px;font-size:14px}.article-section li{margin:7px 0}.aside{align-self:start;padding:28px;background:var(--paper);border:1px solid var(--line);border-radius:8px}.aside h2{font-size:19px}.aside p{font-size:13px;color:var(--muted);margin-bottom:17px}.aside .button{width:100%;font-size:12px;gap:12px}.phone{display:inline-flex;align-items:center;min-height:44px;font-size:13px;margin-top:9px}.note{font-size:11px;color:var(--muted);margin-top:20px}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px}.card{padding:25px;border:1px solid var(--line);border-radius:8px;background:white}.card h3{font-size:19px;font-weight:600;margin-bottom:12px}.card p{font-size:13px;color:var(--muted)}a.card:hover{border-color:var(--gold)}.category{font-size:10px;letter-spacing:.08em;color:#8b754e;display:block;margin-bottom:10px}.card-arrow{display:block;margin-top:18px;font-size:12px}.soft{background:var(--paper)}.region-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.region-card{padding:22px;border:1px solid var(--line);border-radius:8px;background:white}.region-card h3{font-size:19px}.region-card p{font-size:11px;color:var(--muted);margin-top:7px}.region-card .region-state{color:#8b754e;font-size:10px;margin-top:15px}.region-card a{display:inline-flex;align-items:center;min-height:44px;font-size:12px;margin-top:10px}.faq details{border-bottom:1px solid var(--line);padding:18px 0}.faq summary{cursor:pointer;font-size:15px;font-weight:500;min-height:28px}.faq details p{font-size:13px;color:var(--muted);margin:15px 0 0}.cta{background:var(--navy);color:white}.cta h2{color:white}.cta p{color:#b5c5ce;font-size:14px}.cta .button{background:#c7ac79;color:var(--navy);margin:24px 0 12px}.cta .note{color:#b5c5ce}.related h2{font-size:25px}.related .cards{grid-template-columns:repeat(2,minmax(0,1fr))}.related .card{padding:22px}.related .card h3{font-size:16px}.footer{padding:36px 0 90px;background:var(--paper);border-top:1px solid var(--line)}.footer .brand{font-size:18px}.footer .brand img{width:45px;height:45px}.footer-links{display:flex;flex-wrap:wrap;gap:18px;font-size:12px;margin-top:18px}.footer-links a{min-height:44px;display:inline-flex;align-items:center}.copyright{font-size:10px;color:var(--muted);margin-top:18px}.skip{position:fixed;top:-90px;left:15px;background:var(--navy);color:white;padding:10px;z-index:20}.skip:focus{top:10px}.mobile-cta{display:none}.source-list{font-size:12px;overflow-wrap:anywhere}.source-list a{text-decoration:underline}.section ul.checklist{padding-left:22px;font-size:14px;color:var(--muted)}
@media(max-width:900px){.wrap{width:calc(100% - 48px)}.hero-grid{gap:32px}.hero h1{font-size:30px}.content-grid{gap:28px}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.region-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.header-inner{gap:18px}nav{gap:16px}.brand{font-size:18px}.aside{padding:22px}}
@media(max-width:640px){.wrap{width:calc(100% - 40px)}.header-inner{flex-direction:column;align-items:flex-start;padding:16px 0;gap:8px}.brand{font-size:19px}.brand img{width:46px;height:46px}nav{gap:18px;font-size:12px}.hero{padding:35px 0 42px}.hero-grid{grid-template-columns:1fr;gap:30px}.hero h1{font-size:29px}.intro{font-size:14px}.section{padding:45px 0}.section h2{font-size:25px}.content-grid{grid-template-columns:1fr;gap:20px}.cards,.related .cards{grid-template-columns:1fr;gap:14px}.region-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.region-card{padding:18px}.region-card h3{font-size:18px}.aside{padding:24px}.article-section h2{font-size:23px}.mobile-cta{position:fixed;bottom:0;left:0;right:0;z-index:10;display:flex;align-items:center;justify-content:center;min-height:54px;padding:13px 20px calc(13px + env(safe-area-inset-bottom));background:var(--navy);color:white;font-size:14px;gap:24px}.mobile-cta span{color:#d8c291}.footer{padding-bottom:100px}.breadcrumb{font-size:10px}.card{padding:23px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
'''


REGION_CSS = '''
.city-section:nth-of-type(odd){background:var(--paper)}.city-section h2{font-size:27px}.city-section .lead{max-width:900px;margin-bottom:20px}.city-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin-top:28px}.city-cards h3{font-size:19px}.city-cards .card p{font-size:13px}.district-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:13px;margin-top:28px}.district-card{display:block;min-width:0;padding:22px 18px;border:1px solid var(--line);border-radius:8px;background:#fff}.district-card h3{font-size:17px;font-weight:600}.district-card p{font-size:10px;color:var(--muted);margin-top:9px}.district-card[href]:hover{border-color:var(--gold)}.hero .nationwide-map{object-fit:contain;object-position:50% 50%}
@media(max-width:900px){.city-cards{grid-template-columns:repeat(2,minmax(0,1fr))}.district-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:640px){.city-section h2{font-size:24px}.city-cards{grid-template-columns:1fr;gap:14px}.district-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.district-card{padding:19px 15px}.district-card h3{font-size:16px}}
'''


class Builder:
    def __init__(self):
        self.site = read('site.json')
        self.regions = read('regions.json')['regions']
        self.ids = validate_regions(self.regions)
        self.guides = read('guides.json')['pages']
        self.guide_ids = {p['slug']: p for p in self.guides}
        if len(self.guide_ids) != len(self.guides) or any(not slug_ok(p['slug']) for p in self.guides):
            raise ValueError('Duplicate or invalid guide slug')
        self.base = self.site['base_url']
        if self.base != 'https://hyoj4377.github.io/stepon-website/':
            raise ValueError('Unexpected GitHub Pages base path')
        self.logo = 'data:image/webp;base64,' + base64.b64encode((ROOT / 'assets/seo/logo.webp').read_bytes()).decode()
        self.outputs = {}

    def link(self, current, target):
        if target == 'index.html':
            result = posixpath.relpath(target, posixpath.dirname(current))
        else:
            result = posixpath.relpath(target, posixpath.dirname(current))
        return result.replace('index.html', '') or './'

    def canonical(self, path):
        return self.base + path.removesuffix('index.html')

    def consult(self, key='consultation_url', label='상담 신청하기'):
        return f'<a class="button" href="{esc(self.site[key])}" target="_blank" rel="noopener noreferrer">{esc(label)} <span aria-hidden="true">↗</span></a>'

    def phone(self):
        return f'<a class="phone" href="{esc(self.site["phone_uri"])}">상담문의 {esc(self.site["phone"])}</a>'

    def nav_link(self, current, target, label):
        return f'<a href="{esc(self.link(current, target))}">{esc(label)}</a>'

    def card(self, current, page):
        return f'<a class="card" href="{esc(self.link(current, "guides/" + page["slug"] + "/index.html"))}"><span class="category">{esc(page["category"])}</span><h3>{esc(page["h1"])}</h3><p>{esc(page["description"])}</p><span class="card-arrow">자세히 알아보기 →</span></a>'

    def image(self, name):
        allowed = {'main-study', 'home-tutoring', 'online-tutoring', 'study-management', 'parent-consulting', 'korea-network-map', 'elementary-homework', 'high-homework'}
        if name not in allowed:
            raise ValueError('Unknown photo')
        alts = {'main-study': '책상에서 교재를 펼치고 공부하는 학생', 'home-tutoring': '학생과 여성 코치가 함께 교재를 살펴보는 방문수업', 'online-tutoring': '노트북으로 선생님과 화상수업을 하는 학생', 'study-management': '플래너와 교재, 태블릿으로 학습을 정리하는 학생', 'parent-consulting': '학부모와 교육 컨설턴트의 학습 상담', 'korea-network-map': '대한민국 본토와 제주도에 빛의 연결망을 표현한 전국 지도', 'elementary-homework': '책상에서 교재에 직접 필기하며 숙제를 하는 초등학생', 'high-homework': '교재와 노트북을 활용해 숙제를 하는 고등학생'}
        data = base64.b64encode((ROOT / 'assets/images' / (name + '.webp')).read_bytes()).decode()
        width, height = (1648, 954) if name in {'elementary-homework', 'high-homework'} else (1672, 941)
        position = ' style="object-fit:cover;object-position:50% 45%"' if name in {'elementary-homework', 'high-homework'} else ''
        return f'<img class="photo{" nationwide-map" if name == "korea-network-map" else ""}" src="data:image/webp;base64,{data}" width="{width}" height="{height}" alt="{esc(alts[name])}" decoding="async"{position}>'

    def layout(self, path, title, description, label, content, extra_css=''):
        home = self.link(path, 'index.html')
        hub = self.link(path, 'regions/index.html')
        brand = f'<a class="brand" href="{esc(home)}"><img src="{self.logo}" width="160" height="160" alt="스텝온과외 공식 로고"><span>스텝온과외</span></a>'
        nav = ''.join(self.nav_link(path, target, name) for target, name in [('index.html', '홈'), ('regions/index.html', '전국 안내'), ('guides/visit/index.html', '방문과외'), ('guides/online/index.html', '화상과외')])
        return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="theme-color" content="#112c40"><title>{esc(title)}</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{esc(self.canonical(path))}"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(self.canonical(path))}"><meta property="og:type" content="website"><style>{CSS}{extra_css}{(ROOT / "assets/styles/readability.css").read_text()}</style></head>
<body><a class="skip" href="#main">본문으로 바로가기</a><header><div class="wrap header-inner">{brand}<nav aria-label="안내 페이지 탐색">{nav}</nav></div></header>
<div class="wrap breadcrumb"><a href="{esc(home)}">홈</a><span aria-hidden="true">/</span><a href="{esc(hub)}">전국 과외 안내</a><span aria-hidden="true">/</span><span aria-current="page">{esc(label)}</span></div>
<main id="main">{content}</main><footer class="footer"><div class="wrap">{brand}<div class="footer-links">{self.nav_link(path, 'regions/index.html', '전국 과외 안내')}{self.phone()}<a href="{esc(self.site['kakao_url'])}" target="_blank" rel="noopener noreferrer">카카오채널 ↗</a><a href="{esc(self.site['blog_url'])}" target="_blank" rel="noopener noreferrer">블로그 ↗</a></div><p class="copyright">STEP ON · 학생의 성장을 함께 디자인합니다</p></div></footer><a class="mobile-cta" href="{esc(self.site['consultation_url'])}" target="_blank" rel="noopener noreferrer">무료 시강 상담 <span aria-hidden="true">↗</span></a>{self.floating_consult()}</body></html>\n'''

    def floating_consult(self):
        component = (ROOT / 'components/floating-consult.html').read_text(encoding='utf-8')
        for key in ('phone_uri', 'phone', 'kakao_url', 'consultation_url'):
            component = component.replace('{{' + key + '}}', esc(self.site[key]))
        return '<!-- floating-consult:start -->\n' + component + '<!-- floating-consult:end -->'

    def cta(self, key='consultation_url'):
        return f'<section class="section cta"><div class="wrap"><p class="eyebrow">YOUR NEXT STEP</p><h2>학생에게 맞는 다음 한 걸음을 함께 찾습니다.</h2><p>학년·과목·희망 지역과 수업 방식을 알려주세요.</p>{self.consult(key, "무료 시강 및 상담 신청") }<br>{self.phone()}<p class="note">방문 가능 지역, 과목, 일정과 시강 조건은 상담에서 확인합니다. 학생별 학습 과정과 결과에는 차이가 있을 수 있습니다.</p></div></section>'

    def build_guide(self, page):
        path = 'guides/' + page['slug'] + '/index.html'
        for required in ('title', 'description', 'h1', 'intro', 'sections'):
            if not page.get(required):
                raise ValueError('Missing guide content: ' + required)
        articles = []
        for section in page['sections']:
            paragraphs = ''.join('<p>' + esc(p) + '</p>' for p in section['paragraphs'])
            items = '<ul>' + ''.join('<li>' + esc(i) + '</li>' for i in section.get('items', [])) + '</ul>' if section.get('items') else ''
            articles.append(f'<section class="article-section"><h2>{esc(section["heading"])}</h2>{paragraphs}{items}</section>')
        faq = ''.join(f'<details><summary>{esc(item["question"])}</summary><p>{esc(item["answer"])}</p></details>' for item in page['faq'])
        related = ''.join(self.card(path, self.guide_ids[slug]) for slug in page['related'])
        content = f'<section class="hero"><div class="wrap hero-grid"><div><p class="eyebrow">STEP ON / {esc(page["category"])}</p><h1>{esc(page["h1"])}</h1><p class="intro">{esc(page["intro"])}</p>{self.consult(page["cta"], "수업 상담하기")}</div>{self.image(page["photo"])}</div></section><div class="wrap section content-grid"><div>{"".join(articles)}<section class="faq"><h2>자주 묻는 질문</h2>{faq}</section></div><aside class="aside"><h2>상담 전, 이렇게 정리해 보세요.</h2><p>학년과 필요한 과목, 어려운 단원, 현재 사용하는 교재를 알려주세요. 방문 희망 주소나 화상수업 환경도 함께 살펴봅니다.</p>{self.consult(page["cta"], "상담 신청하기")}<br>{self.phone()}<p class="note">수업 가능 여부와 일정은 개별 상담에서 확인합니다.</p></aside></div><section class="section soft related"><div class="wrap"><h2>함께 살펴볼 학습 안내</h2><div class="cards">{related}</div><p class="note">{self.nav_link(path, "regions/index.html", "전국 지역별 과외 안내로 돌아가기 →")}</p></div></section>{self.cta(page["cta"])}'
        self.outputs[path] = self.layout(path, page['title'], page['description'], page['category'], content)

    def build_hub(self):
        path = 'regions/index.html'
        cards = []
        for item in self.regions:
            if item['kind'] != 'province':
                continue
            link = self.nav_link(path, region_path(item, self.ids), '지역 안내 보기 →') if item['status'] == 'published' else '<p class="region-state">개별 지역 안내 준비 중</p>'
            cards.append(f'<article class="region-card" id="region-{esc(item["id"])}"><h3>{esc(item["name"])}</h3><p>{esc(item["official_name"])}</p>{link}</article>')
        groups = [
            ('수업 방식별 안내', [('visit', '방문과외', '익숙한 공간에서 함께 배우기'), ('online', '화상과외', '화면으로 이어지는 맞춤 학습')]),
            ('대상 학년별 안내', [('elementary', '초등학생', '기초 개념과 공부 습관'), ('middle', '중학생', '개념과 학교 학습의 연결'), ('high', '고등학생', '목표와 학습 우선순위')]),
            ('과목별 안내', [('english', '영어과외', '어휘부터 문장 이해까지'), ('math', '수학과외', '개념과 풀이 과정 점검'), ('korean', '국어과외', '독해와 근거 중심의 표현'), ('social', '사회과외', '개념과 자료 분석의 연결'), ('science', '과학과외', '개념 이해와 탐구 자료 분석')]),
            ('학습 관리 안내', [('performance-assessment', '수행평가 관리', '일정과 기준에 맞춰 스스로 준비')]),
        ]
        blocks = []
        for number, (heading, items) in enumerate(groups, 1):
            links = ''.join(f'<a class="guide-choice" href="{esc(self.link(path, "guides/" + slug + "/index.html"))}"><div><h4>{esc(label)}</h4><p>{esc(detail)}</p></div><span aria-hidden="true">→</span></a>' for slug, label, detail in items)
            blocks.append(f'<section class="guide-group"><div class="guide-group-heading"><span aria-hidden="true">0{number}</span><h3>{esc(heading)}</h3></div><div class="guide-choices">{links}</div></section>')
        guides = ''.join(blocks)
        group_css = """
.hero .nationwide-map{object-fit:contain;object-position:50% 50%}
#learning-guides .guide-groups{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:28px}
#learning-guides .guide-group{min-width:0}
#learning-guides .guide-group:last-child{grid-column:1/-1}
#learning-guides .guide-group:last-child .guide-choices{max-width:calc((100% - 56px)/3)}
#learning-guides .guide-group-heading{display:flex;align-items:center;gap:12px;margin-bottom:20px;padding-bottom:16px;border-bottom:1px solid var(--line)}
#learning-guides .guide-group-heading>span{font-size:10px;color:#8b754e;letter-spacing:.08em}
#learning-guides h3{font-size:19px;font-weight:600}
#learning-guides .guide-choices{display:grid;gap:12px}
#learning-guides .guide-choice{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:18px 20px;min-height:90px;border:1px solid var(--line);border-radius:8px;background:var(--paper)}
#learning-guides .guide-choice:hover{border-color:var(--gold);background:white}
#learning-guides h4{margin:0 0 5px;font-size:16px;font-weight:600;line-height:1.5;letter-spacing:-.035em}
#learning-guides .guide-choice p{font-size:11px;color:var(--muted);line-height:1.8}
#learning-guides .guide-choice>span{font-size:16px;color:#8b754e;flex-shrink:0}
@media(max-width:900px){#learning-guides .guide-groups{gap:20px}#learning-guides h3{font-size:17px}#learning-guides .guide-choice{padding:16px;gap:10px}#learning-guides .guide-group-heading{gap:8px}}
@media(max-width:640px){#learning-guides .guide-group:last-child .guide-choices{max-width:none}#learning-guides .guide-groups{grid-template-columns:1fr;gap:32px}#learning-guides .guide-group-heading{margin-bottom:14px;padding-bottom:12px}#learning-guides h3{font-size:19px}#learning-guides .guide-choices{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}#learning-guides .guide-choice{padding:15px 14px;min-height:94px;align-items:flex-start}#learning-guides .guide-choice>span{padding-top:2px}#learning-guides h4{font-size:15px}}
"""
        content = f'<section class="hero"><div class="wrap hero-grid"><div><p class="eyebrow">STEP ON / NATIONWIDE LEARNING</p><h1>전국 지역별 과외, 학생에게 맞는 방향부터.</h1><p class="intro">초등·중등·고등 학생을 위한 방문과외와 화상과외를 안내합니다. 지역명보다 먼저 학생의 학습 상태와 필요한 과목을 살펴보고, 희망 지역·일정에 맞는 수업 방식을 상담하세요.</p>{self.consult("consultation_url", "우리 지역 수업 상담하기")}</div>{self.image("korea-network-map")}</div></section><section class="section"><div class="wrap"><h2>17개 시·도 상담 안내</h2><p class="lead">전국 지역의 상담을 안내합니다. 방문수업은 실제 주소·과목·시간을 확인한 뒤 가능 여부를 안내하며, 화상수업은 기기와 학습 환경을 함께 살펴봅니다. 지역별 안내는 검증된 정보를 충분히 확보한 뒤 차례로 공개합니다.</p><div class="region-grid">{"".join(cards)}</div><p class="note">준비 중인 지역의 별도 안내 페이지는 아직 공개하지 않습니다. 특정 동네나 학교의 전담 강사·수업 실적을 의미하지 않습니다.</p></div></section><section class="section soft"><div class="wrap"><h2>지역 상담에 도움이 되는 정보</h2><ul class="checklist"><li>시·도, 시·군·구, 읍·면·동과 방문 희망 주소</li><li>학생의 학년, 필요한 과목과 현재 사용하는 교재</li><li>어려운 단원, 공부 습관과 희망 학습 목표</li><li>가능한 요일·시간과 방문 또는 화상 희망 방식</li></ul><p class="note">학교별 일정·자료는 공식 안내를 바탕으로 확인합니다. 학교명은 상담 맥락을 이해하기 위한 정보이며 학교와의 제휴나 전담 수업을 뜻하지 않습니다.</p></div></section><section class="section" id="learning-guides"><div class="wrap"><h2>학년·과목·수업 방식별로 살펴보기</h2><p class="lead">현재 필요한 학습 내용을 먼저 확인해 보세요.</p><div class="guide-groups">{guides}</div></div></section>{self.cta()}'
        self.outputs[path] = self.layout(path, '전국 지역별 과외 안내 | 초등 중등 고등 방문·화상과외 · 스텝온과외', '전국 17개 시·도 초등·중등·고등 과외 상담 안내. 학생의 학년과 영어·수학 학습 상황에 맞춰 방문과외·화상과외를 비교하고 지역별 실제 진행 조건을 확인하세요.', '전국 지역별 과외', content, group_css)

    def build_city_guide(self, item):
        path = region_path(item, self.ids)
        sections = []
        for section in item['sections']:
            paragraphs = ''.join('<p class="lead">' + esc(p) + '</p>' for p in section['paragraphs'])
            cards = ''
            if section.get('cards'):
                cards = '<div class="city-cards">' + ''.join('<a class="card" href="' + esc(self.link(path, 'guides/' + card['slug'] + '/index.html')) + '"><h3>' + esc(card['heading']) + '</h3><p>' + esc(card['description']) + '</p><span class="card-arrow">학습 안내 보기 →</span></a>' for card in section['cards']) + '</div>'
            if section['heading'] == '서울 25개 자치구 과외 안내':
                districts = []
                for district in item['districts']:
                    child = self.ids.get(district.get('page_id'))
                    published = child and child['status'] == 'published' and child.get('parent_id') == item['id'] and child['kind'] == 'district'
                    inside = '<h3>' + esc(district['name']) + ' 과외</h3><p>방문과외 · 화상과외</p>'
                    districts.append('<a class="district-card" href="' + esc(self.link(path, region_path(child, self.ids))) + '">' + inside + '</a>' if published else '<article class="district-card">' + inside + '</article>')
                cards = '<div class="district-grid">' + ''.join(districts) + '</div><p class="note">자치구별 상세 페이지는 검증된 안내가 준비된 뒤 연결합니다. 준비된 구별 상세 안내부터 연결하며, 나머지 자치구는 아직 별도 상세 링크가 없습니다.</p>'
            sections.append('<section class="section city-section"><div class="wrap"><h2>' + esc(section['heading']) + '</h2>' + paragraphs + cards + '</div></section>')
        faq = ''.join('<details><summary>' + esc(q['question']) + '</summary><p>' + esc(q['answer']) + '</p></details>' for q in item['faq'])
        content = '<section class="hero"><div class="wrap hero-grid"><div><p class="eyebrow">STEP ON / SEOUL LEARNING</p><h1>' + esc(item['h1']) + '</h1><p class="intro">' + esc(item['intro']) + '</p>' + self.consult('consultation_url', '서울 과외 상담 신청') + '</div>' + self.image(item['photo']) + '</div></section>' + ''.join(sections) + '<section class="section soft"><div class="wrap faq"><h2>서울 과외, 자주 묻는 질문</h2>' + faq + '</div></section><section class="section"><div class="wrap"><h2>전국 지역 안내와 함께 살펴보세요.</h2><p class="lead">서울 외 다른 지역의 안내와 수업 방식·학년·과목별 정보를 전국 안내에서 확인할 수 있습니다.</p><a class="button" href="' + esc(self.link(path, 'regions/index.html')) + '">전국 지역별 과외 안내 →</a><p class="note">서울 전 지역 서비스 범위와 자치구 목록은 운영자가 제공한 정보를 기준으로 안내합니다. 실제 수업 일정과 조건은 상담에서 조율합니다.</p></div></section><section class="section cta"><div class="wrap"><p class="eyebrow">YOUR NEXT STEP / SEOUL</p><h2>우리 동네에서 시작하는 서울 과외 상담</h2><p>학년·과목·자치구와 동네, 희망 수업 방식과 시간을 알려주세요.</p>' + self.consult('consultation_url', '서울 과외 상담 신청') + '<br>' + self.phone() + '<p class="note">시강 일정과 진행 조건은 상담에서 확인합니다. 학생별 학습 과정과 결과에는 차이가 있을 수 있습니다.</p></div></section>'
        css = REGION_CSS
        canonical = self.canonical(path)
        schema = [
            {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': '스텝온과외 홈', 'item': self.base},
                {'@type': 'ListItem', 'position': 2, 'name': '전국 지역별 과외 안내', 'item': self.base + 'regions/'},
                {'@type': 'ListItem', 'position': 3, 'name': '서울 과외', 'item': canonical}]},
            {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
                {'@type': 'Question', 'name': q['question'], 'acceptedAnswer': {'@type': 'Answer', 'text': q['answer']}} for q in item['faq']]},
        ]
        structured = json.dumps(schema, ensure_ascii=False).replace('<', r'\u003c')
        output = self.layout(path, item['title'], item['description'], '서울 과외', content, css)
        self.outputs[path] = output.replace('</head>', '<script type="application/ld+json">' + structured + '</script></head>')

    def build_district_guide(self, item):
        path = region_path(item, self.ids)
        parent = self.ids[item['parent_id']]
        parent_path = region_path(parent, self.ids)
        sections = []
        for section in item['sections']:
            paragraphs = ''.join('<p class="lead">' + esc(p) + '</p>' for p in section['paragraphs'])
            cards = ''
            if section.get('cards'):
                cards = '<div class="city-cards">' + ''.join('<a class="card" href="' + esc(self.link(path, 'guides/' + card['slug'] + '/index.html')) + '"><h3>' + esc(card['heading']) + '</h3><p>' + esc(card['description']) + '</p><span class="card-arrow">학습 안내 보기 →</span></a>' for card in section['cards']) + '</div>'
            if section.get('neighborhood_grid'):
                places = []
                for place in item['neighborhoods']:
                    child = self.ids.get(place.get('page_id'))
                    available = child and child['kind'] == 'neighborhood' and child['parent_id'] == item['id'] and child['status'] == 'published'
                    inside = '<h3>' + esc(place['name']) + ' 과외</h3><p>' + esc(place['focus']) + '</p>'
                    places.append('<a class="district-card" href="' + esc(self.link(path, region_path(child, self.ids))) + '">' + inside + '</a>' if available else '<article class="district-card">' + inside + '</article>')
                cards = '<div class="district-grid neighborhood-grid">' + ''.join(places) + '</div>'
            sections.append('<section class="section city-section"><div class="wrap"><h2>' + esc(section['heading']) + '</h2>' + paragraphs + cards + '</div></section>')
        faq = ''.join('<details><summary>' + esc(q['question']) + '</summary><p>' + esc(q['answer']) + '</p></details>' for q in item['faq'])
        content = '<section class="hero"><div class="wrap hero-grid"><div><p class="eyebrow">STEP ON / ' + esc(item['slug'].upper()) + ' LEARNING</p><h1>' + esc(item['h1']) + '</h1><p class="intro">' + esc(item['intro']) + '</p>' + self.consult('consultation_url', item['name'] + ' 과외 상담 신청') + '</div>' + self.image(item['photo']) + '</div></section>' + ''.join(sections) + '<section class="section soft"><div class="wrap faq"><h2>' + esc(item['name']) + ' 과외, 학부모가 자주 묻는 질문</h2>' + faq + '</div></section><section class="section"><div class="wrap"><h2>서울의 다른 지역도 함께 살펴보세요.</h2><p class="lead">서울 대표 페이지에서 25개 자치구 안내를 확인하고, 전국 안내에서 학년·과목·수업 방식별 정보를 살펴보세요.</p><div class="return-links"><a class="button" href="' + esc(self.link(path, parent_path)) + '">서울 과외 대표 안내 →</a><a class="button" href="' + esc(self.link(path, 'regions/index.html')) + '">전국 지역별 과외 안내 →</a></div><p class="note">' + esc(item['name']) + ' 서비스 범위와 동네 목록은 운영자가 제공한 정보를 기준으로 안내합니다. 지역명은 지점·사무실·학교 전담 강사의 위치를 의미하지 않습니다.</p></div></section><section class="section cta"><div class="wrap"><p class="eyebrow">YOUR NEXT STEP / ' + esc(item['slug'].upper()) + '</p><h2>' + esc(item.get('cta_heading', item['name'] + ' 전 지역, 우리 아이의 다음 공부를 상담하세요.')) + '</h2><p>학년·과목·동네와 희망 수업 방식, 가능한 시간을 알려주세요.</p>' + self.consult('consultation_url', item['name'] + ' 과외 상담 신청') + '<br>' + self.phone() + '<p class="note">' + esc(item.get('cta_note', '구체적인 일정·진행 조건과 시강 방법은 상담에서 확인합니다. 학생별 학습 과정과 결과에는 차이가 있을 수 있습니다.')) + '</p></div></section>'
        css = REGION_CSS + '''
.neighborhood-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.neighborhood-grid .district-card p{font-size:12px;line-height:1.9}.return-links{display:flex;flex-wrap:wrap;gap:14px}@media(max-width:640px){.neighborhood-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.neighborhood-grid .district-card p{font-size:11px}.return-links{flex-direction:column}.return-links .button{align-self:flex-start}}
'''
        columns = item.get('neighborhood_columns', 3)
        if columns not in {2, 3, 4}:
            raise ValueError('Unsupported neighborhood grid column count')
        if columns != 3:
            css += f'@media(min-width:641px){{.neighborhood-grid{{grid-template-columns:repeat({columns},minmax(0,1fr))}}}}'
        canonical = self.canonical(path)
        schemas = [
            {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': '스텝온과외 홈', 'item': self.base},
                {'@type': 'ListItem', 'position': 2, 'name': '전국 지역별 과외 안내', 'item': self.base + 'regions/'},
                {'@type': 'ListItem', 'position': 3, 'name': '서울 과외', 'item': self.canonical(parent_path)},
                {'@type': 'ListItem', 'position': 4, 'name': item['name'] + ' 과외', 'item': canonical}]},
            {'@context': 'https://schema.org', '@type': 'Service', '@id': canonical + '#service', 'url': canonical, 'name': item.get('service_name', self.site['brand'] + ' ' + item['name'] + ' 방문과외·화상과외'), 'description': item.get('service_description', item['description']), 'serviceType': item.get('service_type', '초등·중등·고등 영어·수학·국어·사회·과학 방문과외 및 화상과외'), 'provider': {'@type': 'Organization', 'name': self.site['brand'], 'url': self.base, 'telephone': self.site['phone']}, 'areaServed': {'@type': 'AdministrativeArea', 'name': item['official_name'], 'containedInPlace': {'@type': 'AdministrativeArea', 'name': '서울특별시'}}, 'audience': {'@type': 'Audience', 'audienceType': '초등학생·중학생·고등학생'}},
            {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q['question'], 'acceptedAnswer': {'@type': 'Answer', 'text': q['answer']}} for q in item['faq']]},
        ]
        structured = json.dumps(schemas, ensure_ascii=False).replace('<', r'\u003c')
        output = self.layout(path, item['title'], item['description'], item['name'] + ' 과외', content, css)
        output = output.replace('<span aria-current="page">' + esc(item['name']) + ' 과외</span>', '<a href="' + esc(self.link(path, parent_path)) + '">서울 과외</a><span aria-hidden="true">/</span><span aria-current="page">' + esc(item['name']) + ' 과외</span>')
        self.outputs[path] = output.replace('</head>', '<script type="application/ld+json">' + structured + '</script></head>')

    def build_region(self, item):
        if item.get('layout') == 'district-guide':
            self.build_district_guide(item)
            return
        if item.get('layout') == 'city-guide':
            self.build_city_guide(item)
            return
        path = region_path(item, self.ids)
        parent = self.ids.get(item.get('parent_id'))
        parent_link = self.nav_link(path, region_path(parent, self.ids), parent['name'] + ' 안내로 돌아가기') if parent else self.nav_link(path, 'regions/index.html', '전국 지역별 안내로 돌아가기')
        sections = ''.join('<section class="article-section"><h2>' + esc(section['heading']) + '</h2>' + ''.join('<p>' + esc(p) + '</p>' for p in section['paragraphs']) + '</section>' for section in item['sections'])
        children = [child for child in self.regions if child.get('parent_id') == item['id'] and child['status'] == 'published']
        links = ''.join(self.nav_link(path, region_path(child, self.ids), child['name'] + ' 안내 →') + '<br>' for child in children)
        sources = ''.join('<li><a href="' + esc(source['url']) + '" target="_blank" rel="noopener noreferrer">' + esc(source.get('label', '공식 정보 출처')) + '</a> · 확인일 ' + esc(source['checked_on']) + '</li>' for source in item['sources'] if verified_source(source))
        notice = '<p class="note">이 페이지는 해당 학교의 공식 페이지가 아니며, 학교와의 제휴·전담 강사·실제 수업 실적을 뜻하지 않습니다.</p>' if item['kind'] in {'school', 'learning'} else ''
        content = f'<section class="hero"><div class="wrap"><p class="eyebrow">STEP ON / LOCAL LEARNING</p><h1>{esc(item.get("h1", item["name"] + " 과외 학습 안내"))}</h1><p class="intro">{esc(item["intro"])}</p>{notice}</div></section><section class="section"><div class="wrap">{sections}<h2>함께 확인할 지역 안내</h2><p>{parent_link}</p>{links}<h2>공식 정보 확인 출처</h2><ul class="source-list">{sources}</ul><p class="note">방문 가능 여부와 일정은 개별 상담에서 확인합니다.</p></div></section>{self.cta()}'
        self.outputs[path] = self.layout(path, item['title'], item['description'], item['name'], content)

    def build(self):
        self.outputs = {}
        for page in self.guides:
            self.build_guide(page)
        self.build_hub()
        published_regions = [r for r in self.regions if r['status'] == 'published']
        # Near-duplicates after removing location names are not publishable.
        fingerprints = set()
        for item in published_regions:
            normalized = item['intro'] + ''.join(''.join(s['paragraphs']) for s in item['sections'])
            for region in self.regions:
                normalized = normalized.replace(region['official_name'], '').replace(region['name'], '')
            normalized = re.sub(r'\s+', '', normalized)
            if any(SequenceMatcher(None, normalized, previous, autojunk=False).ratio() > 0.85 for previous in fingerprints):
                raise ValueError('Region-name-only duplicate content: ' + item['id'])
            fingerprints.add(normalized)
            self.build_region(item)
        urls = [self.base] + [self.canonical(path) for path in sorted(self.outputs)]
        if len(urls) != len(set(urls)):
            raise ValueError('Duplicate canonical URL')
        ET.register_namespace('', NS)
        root = ET.Element('{' + NS + '}urlset')
        for url in urls:
            node = ET.SubElement(root, '{' + NS + '}url')
            ET.SubElement(node, '{' + NS + '}loc').text = url
        ET.indent(root, space='  ')
        self.outputs['sitemap.xml'] = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode') + '\n'
        old = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {'files': {}}
        for path, checksum in old.get('files', {}).items():
            if path not in {'sitemap.xml', 'regions/index.html'} and not re.fullmatch(r'(?:guides|regions)/(?:[a-z0-9]+(?:-[a-z0-9]+)*/)+index\.html', path):
                raise ValueError('Unsafe generated manifest path: ' + path)
            full = ROOT / path
            if path not in self.outputs and full.exists():
                if hashlib.sha256(full.read_bytes()).hexdigest() != checksum:
                    raise ValueError('Refusing to remove edited generated file: ' + path)
        return old

    def preview_drafts(self, directory):
        directory = Path(directory).resolve()
        if directory == ROOT or directory.is_relative_to(ROOT):
            raise ValueError('Draft previews must be outside the GitHub Pages checkout')
        directory.mkdir(parents=True, exist_ok=True)
        count = 0
        for item in self.regions:
            if item['status'] != 'draft':
                continue
            path = region_path(item, self.ids)
            body = '<div class="wrap section"><p class="eyebrow">검토용 초안 · 공개 대상 아님</p><h1>' + esc(item.get('h1', item['name'])) + '</h1><p class="intro">' + esc(item['intro']) + '</p>'
            body += ''.join('<section class="section"><h2>' + esc(section['heading']) + '</h2>' + ''.join('<p>' + esc(p) + '</p>' for p in section['paragraphs']) + '</section>' for section in item['sections'])
            body += '<h2>게시 전 보완사항</h2><ul>' + ''.join('<li>' + esc(p) + '</li>' for p in item['missing']) + '</ul></div>'
            text = '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>' + esc(item['title']) + ' · 검토용</title><style>' + CSS + '</style></head><body>' + body + '</body></html>'
            output = directory / path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding='utf-8')
            count += 1
        print(f'Wrote {count} private review previews outside checkout: {directory}')

    def save(self, check=False):
        old = self.build()
        # Only the marked common style is synchronized; homepage content stays authored by hand.
        homepage = ROOT / 'index.html'
        original_home = homepage.read_text(encoding='utf-8')
        common_style = '<style id="readability">\n' + (ROOT / 'assets/styles/readability.css').read_text() + '</style>'
        home, count = re.subn(r'<style id="readability">.*?</style>', lambda _: common_style, original_home, flags=re.S)
        if count != 1:
            raise ValueError('Expected exactly one homepage readability style block')
        floating = self.floating_consult()
        if '<!-- floating-consult:start -->' in home:
            home, count = re.subn(r'<!-- floating-consult:start -->.*?<!-- floating-consult:end -->', lambda _: floating, home, flags=re.S)
            if count != 1:
                raise ValueError('Expected exactly one floating consultation component')
        else:
            home = home.replace('</body>', floating + '</body>')
        if check and home != original_home:
            raise ValueError('Regenerate homepage shared components: python3 scripts/build_seo.py')
        files = {path: hashlib.sha256(content.encode()).hexdigest() for path, content in self.outputs.items()}
        manifest = json.dumps({'schema_version': 1, 'files': files}, ensure_ascii=False, indent=2) + '\n'
        if check:
            wrong = [path for path, content in self.outputs.items() if not (ROOT / path).exists() or (ROOT / path).read_text() != content]
            wrong += [path for path in old.get('files', {}) if path not in self.outputs and (ROOT / path).exists()]
            if not MANIFEST.exists() or MANIFEST.read_text() != manifest:
                wrong.append(str(MANIFEST.relative_to(ROOT)))
            if wrong:
                raise ValueError('Regenerate SEO outputs: ' + ', '.join(wrong))
        else:
            # Check every target before making any filesystem change.
            for path, content in self.outputs.items():
                full = ROOT / path
                if not full.exists():
                    continue
                previous = old.get('files', {}).get(path)
                if previous is None and path != 'sitemap.xml':
                    raise ValueError('Refusing to overwrite unowned file: ' + path)
                if previous and hashlib.sha256(full.read_bytes()).hexdigest() != previous and full.read_text() != content:
                    raise ValueError('Refusing to overwrite manually edited generated file: ' + path)
            for path in old.get('files', {}):
                if path not in self.outputs and (ROOT / path).exists():
                    (ROOT / path).unlink()
            for path, content in self.outputs.items():
                full = ROOT / path
                if full.exists() and path not in old.get('files', {}) and path != 'sitemap.xml':
                    raise ValueError('Refusing to overwrite unowned file: ' + path)
                full.parent.mkdir(parents=True, exist_ok=True)
                full.write_text(content, encoding='utf-8')
            MANIFEST.write_text(manifest, encoding='utf-8')
            if home != original_home:
                homepage.write_text(home, encoding='utf-8')
        print(('Checked' if check else 'Generated') + f' {len(self.outputs)-1} published pages; sitemap {len(self.outputs)} URLs; {len([r for r in self.regions if r["status"] == "draft"])} region drafts excluded.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Fail if committed output is stale')
    parser.add_argument('--preview-drafts', metavar='DIRECTORY', help='Write review-only drafts outside checkout; never to sitemap')
    args = parser.parse_args()
    builder = Builder()
    if args.preview_drafts:
        builder.preview_drafts(args.preview_drafts)
    else:
        builder.save(args.check)
