(() => {
  'use strict';
  const config = window.STEPON_CONFIG;
  const escape = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const text = (selector, value) => document.querySelectorAll(selector).forEach((element) => { element.textContent = value; });
  const safeUrl = (value) => {
    try { const url = new URL(value); return url.protocol === 'https:' ? url.href : null; } catch { return null; }
  };
  text('[data-brand]', config.brand);
  text('[data-slogan]', config.slogan);
  text('#hero-title', config.hero.title);
  text('#hero-description', config.hero.description);
  text('#about-title', config.introduction.title);
  text('#about-description', config.introduction.description);
  text('#trial-description', config.trial.description);
  text('#trial-note', config.trial.note);
  text('#year', new Date().getFullYear());
  document.querySelector('#level-cards').innerHTML = config.levels.map((level, index) => `<article class="level-card"><div class="level-top"><span class="eyebrow">${escape(level.label)}</span><span class="level-index">0${index + 1}</span></div><h3>${escape(level.title)}<span>학습</span></h3><h4>${escape(level.subtitle)}</h4><p>${escape(level.description)}</p><div class="tags">${level.tags.map((tag) => `<span>${escape(tag)}</span>`).join('')}</div></article>`).join('');
  document.querySelector('#management-list').innerHTML = config.management.map((item, index) => `<article class="care-item"><span>0${index + 1}</span><div><h3>${escape(item.title)}</h3><p>${escape(item.description)}</p></div><span class="care-plus" aria-hidden="true">+</span></article>`).join('');
  document.querySelector('#review-cards').innerHTML = config.reviews.length ? config.reviews.map((review) => `<article class="review-card"><span class="quote" aria-hidden="true">“</span><blockquote>${escape(review.text)}</blockquote><div class="review-author"><strong>${escape(review.author)}</strong><span>${escape(review.detail)}</span></div></article>`).join('') : [1, 2, 3].map((number) => `<article class="review-card placeholder"><span class="quote" aria-hidden="true">“</span><p class="review-ready">다음 배움의 이야기를<br>기다리고 있습니다.</p><div class="review-author"><span>실제 후기 준비 중</span><span>0${number}</span></div></article>`).join('');
  const consultation = safeUrl(config.consultationUrl);
  document.querySelectorAll('[data-consult]').forEach((link) => {
    link.href = consultation || '#contact';
    if (!consultation) link.addEventListener('click', () => text('#contact-status', '상담 신청 링크를 준비 중입니다. 아래 등록된 연락처가 있다면 해당 연락처로 문의해 주세요.'));
  });
  if (!consultation) text('#contact-status', '온라인 상담 신청 링크를 준비 중입니다.');
  [['#kakao-link', config.kakaoUrl], ['#blog-link', config.blogUrl]].forEach(([selector, value]) => {
    const link = document.querySelector(selector);
    const url = safeUrl(value);
    if (url) { link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer'; }
    else { link.removeAttribute('href'); link.setAttribute('aria-disabled', 'true'); link.querySelector('.social-status').textContent = '채널 연결 준비 중'; }
  });
  const details = [];
  if (config.phone) details.push(`<a href="tel:${escape(config.phone.replace(/[^+\d]/g, ''))}">전화 ${escape(config.phone)}</a>`);
  if (config.email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(config.email)) details.push(`<a href="mailto:${escape(config.email)}">이메일 ${escape(config.email)}</a>`);
  if (config.business.representative) details.push(`<span>대표 ${escape(config.business.representative)}</span>`);
  if (config.business.registrationNumber) details.push(`<span>사업자등록번호 ${escape(config.business.registrationNumber)}</span>`);
  if (config.business.address) details.push(`<span>${escape(config.business.address)}</span>`);
  document.querySelector('#footer-details').innerHTML = details.join('');
  const toggle = document.querySelector('.menu-toggle');
  const nav = document.querySelector('#navigation');
  const closeMenu = () => { toggle.setAttribute('aria-expanded', 'false'); toggle.setAttribute('aria-label', '메뉴 열기'); nav.classList.remove('open'); };
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(open)); toggle.setAttribute('aria-label', open ? '메뉴 닫기' : '메뉴 열기'); nav.classList.toggle('open', open);
  });
  nav.querySelectorAll('a').forEach((link) => link.addEventListener('click', closeMenu));
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') { closeMenu(); toggle.focus(); } });
  window.matchMedia('(min-width: 901px)').addEventListener('change', (event) => { if (event.matches) closeMenu(); });
})();
