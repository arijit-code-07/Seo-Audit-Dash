#!/usr/bin/env python3
"""SEO Audit Tool - Complete Webpage Scraper"""

import asyncio
import json
import re
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import argparse

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Playwright not installed. Install with: pip install playwright && playwright install chromium")
    raise


@dataclass
class TitleAnalysis:
    text: str
    char_count: int
    pixel_width: int
    status: str


@dataclass
class MetaDescription:
    text: str
    char_count: int
    pixel_width: int
    status: str


@dataclass
class LinkInfo:
    url: str
    text: str
    status_code: int
    is_follow: bool
    link_type: str
    redirect_chain: List = None


@dataclass
class PhoneInfo:
    number: str
    is_visible: bool
    has_tel_link: bool
    tel_link: Optional[str]
    is_clickable: bool


@dataclass
class EmailInfo:
    address: str
    is_visible: bool
    has_mailto_link: bool
    mailto_link: Optional[str]
    is_obfuscated: bool


@dataclass
class ImageInfo:
    src: str
    alt: str
    has_alt: bool
    alt_quality: str
    img_type: str
    file_size: Optional[int]
    has_lazy_loading: bool
    width: Optional[int]
    height: Optional[int]


@dataclass
class SchemaInfo:
    type: str
    raw_json: Dict
    is_valid: bool
    has_rich_snippet: bool
    rich_snippet_type: Optional[str]


@dataclass
class SEOAuditResult:
    url: str
    audit_date: str
    title: TitleAnalysis
    meta_description: MetaDescription
    redirects_3xx: List[LinkInfo]
    broken_4xx: List[LinkInfo]
    phones: List[PhoneInfo]
    emails: List[EmailInfo]
    has_contact_form: bool
    contact_form_details: Dict
    images: List[ImageInfo]
    index_status: Dict
    has_faq: bool
    faq_details: Dict
    schemas: List[SchemaInfo]
    headings: Dict[str, List[str]]
    canonical: Optional[str]
    robots_meta: Optional[str]
    viewport: Optional[str]
    lang: Optional[str]
    word_count: int
    internal_links: int
    external_links: int
    page_load_time_ms: float
    score: int


class SEOAuditor:
    def __init__(self):
        self.browser = None
        self.playwright = None

    async def init(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    def _measure_text_width(self, text):
        narrow = "ijlI.,;:!|\'\" "
        normal = "abcdefghknopqrstuvwxyzABCDEFGHJKLMNOPQRSTUVWXYZ0123456789"
        wide = "mwM@#%&*()[]{}<>"
        width = 0
        for char in text:
            if char in narrow:
                width += 4
            elif char in wide:
                width += 12
            else:
                width += 8
        return width

    async def _check_link_status(self, url, page):
        try:
            response = await page.context.request.head(url, timeout=5000)
            status = response.status
            await response.dispose()
            return status, []
        except Exception:
            try:
                response = await page.context.request.get(url, timeout=5000)
                status = response.status
                await response.dispose()
                return status, []
            except Exception:
                return 0, []

    async def audit(self, target_url):
        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        start_time = datetime.now()

        try:
            response = await page.goto(target_url, wait_until="networkidle", timeout=30000)
        except Exception:
            response = None

        load_time = (datetime.now() - start_time).total_seconds() * 1000
        await page.wait_for_timeout(2000)

        # 1. PAGE TITLE
        title_text = await page.title()
        title_chars = len(title_text)
        title_pixels = self._measure_text_width(title_text)

        if not title_text:
            title_status = "missing"
        elif title_pixels > 580:
            title_status = "too_long"
        elif title_chars < 30:
            title_status = "too_short"
        else:
            title_status = "optimal"

        title_analysis = TitleAnalysis(
            text=title_text, char_count=title_chars,
            pixel_width=title_pixels, status=title_status
        )

        # 2. META DESCRIPTION
        meta_desc = await page.evaluate("""() => {
            const meta = document.querySelector('meta[name=\"description\"]');
            return meta ? meta.getAttribute('content') || '' : '';
        }""")
        desc_chars = len(meta_desc)
        desc_pixels = self._measure_text_width(meta_desc)

        if not meta_desc:
            desc_status = "missing"
        elif desc_pixels > 920:
            desc_status = "too_long"
        elif desc_chars < 120:
            desc_status = "too_short"
        else:
            desc_status = "optimal"

        meta_description = MetaDescription(
            text=meta_desc, char_count=desc_chars,
            pixel_width=desc_pixels, status=desc_status
        )

        # Extract all links
        links_data = await page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a[href]'));
            return links.map(a => ({
                href: a.href,
                text: a.innerText.trim().substring(0, 100),
                rel: a.getAttribute('rel') || '',
                is_nofollow: (a.getAttribute('rel') || '').toLowerCase().includes('nofollow')
            }));
        }""")

        # 3 & 4. CHECK 3xx AND 4xx LINKS
        redirects_3xx = []
        broken_4xx = []
        checked_urls = set()

        parsed_target = urllib.parse.urlparse(target_url)
        base_domain = parsed_target.netloc

        for link in links_data:
            href = link['href']
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            if href in checked_urls:
                continue
            checked_urls.add(href)

            try:
                status, chain = await self._check_link_status(href, page)
                parsed_link = urllib.parse.urlparse(href)
                is_internal = parsed_link.netloc == base_domain or not parsed_link.netloc

                link_info = LinkInfo(
                    url=href, text=link['text'], status_code=status,
                    is_follow=not link['is_nofollow'],
                    link_type="internal" if is_internal else "external",
                    redirect_chain=chain
                )

                if 300 <= status < 400:
                    redirects_3xx.append(link_info)
                elif 400 <= status < 500 or status == 0:
                    broken_4xx.append(link_info)
            except Exception:
                pass

        # 5. PHONE NUMBER DETECTION
        page_text = await page.evaluate('() => document.body.innerText')

        phone_patterns = [
            r'\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
            r'\+?[0-9]{1,3}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}',
            r'\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
        ]

        phones_found = []
        seen_phones = set()

        for pattern in phone_patterns:
            matches = re.findall(pattern, page_text)
            for match in matches:
                clean_phone = re.sub(r'[^0-9+]', '', match)
                if clean_phone and clean_phone not in seen_phones and len(clean_phone) >= 10:
                    seen_phones.add(clean_phone)

                    tel_links = await page.evaluate("""() => {
                        const links = Array.from(document.querySelectorAll('a[href^=\"tel:\"]'));
                        return links.map(a => a.href);
                    }""")

                    has_tel = any(clean_phone in re.sub(r'[^0-9+]', '', t) for t in tel_links)
                    matching_tel = next((t for t in tel_links if clean_phone in re.sub(r'[^0-9+]', '', t)), None)

                    phones_found.append(PhoneInfo(
                        number=match.strip(), is_visible=True,
                        has_tel_link=has_tel, tel_link=matching_tel,
                        is_clickable=has_tel
                    ))

        # 6. EMAIL DETECTION
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails_found = []
        seen_emails = set()

        email_matches = re.findall(email_pattern, page_text)
        for email in email_matches:
            if email not in seen_emails:
                seen_emails.add(email)

                mailto_links = await page.evaluate("""() => {
                    const links = Array.from(document.querySelectorAll('a[href^=\"mailto:\"]'));
                    return links.map(a => a.href);
                }""")

                has_mailto = any(email in m for m in mailto_links)
                matching_mailto = next((m for m in mailto_links if email in m), None)

                is_obf = await page.evaluate(f"""() => {{
                    return document.body.innerHTML.includes('{email}') === false;
                }}""")

                emails_found.append(EmailInfo(
                    address=email, is_visible=True,
                    has_mailto_link=has_mailto, mailto_link=matching_mailto,
                    is_obfuscated=is_obf
                ))

        # 7. CONTACT FORM DETECTION
        has_form = await page.evaluate("""() => {
            const forms = document.querySelectorAll('form');
            for (const form of forms) {
                const inputs = form.querySelectorAll('input, textarea');
                const hasEmail = Array.from(inputs).some(i => 
                    i.type === 'email' || i.name.toLowerCase().includes('email')
                );
                const hasMessage = Array.from(inputs).some(i => 
                    i.tagName === 'TEXTAREA' || i.name.toLowerCase().includes('message')
                );
                if (hasEmail || hasMessage) return true;
            }
            return false;
        }""")

        form_details = {"detected": has_form}

        # 8. IMAGE ANALYSIS
        images_data = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('img')).map(img => ({
                src: img.src,
                alt: img.getAttribute('alt') || '',
                width: img.naturalWidth,
                height: img.naturalHeight,
                loading: img.getAttribute('loading') || '',
                has_alt: img.hasAttribute('alt')
            }));
        }""")

        images_analysis = []
        for img in images_data:
            if not img['src'] or img['src'].startswith('data:'):
                continue

            alt = img['alt']
            has_alt = img['has_alt']

            if not has_alt:
                alt_quality = "missing"
            elif not alt.strip():
                alt_quality = "empty"
            elif len(alt) > 125:
                alt_quality = "too_long"
            elif re.search(r'\b(buy|cheap|discount|best|top)\b', alt.lower()) and len(alt.split()) < 3:
                alt_quality = "keyword_stuffed"
            else:
                alt_quality = "good"

            ext = urllib.parse.urlparse(img['src']).path.split('.')[-1].lower() if '.' in urllib.parse.urlparse(img['src']).path else 'unknown'
            if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'avif']:
                ext = 'unknown'

            images_analysis.append(ImageInfo(
                src=img['src'], alt=alt, has_alt=has_alt,
                alt_quality=alt_quality, img_type=ext,
                file_size=None, has_lazy_loading=img['loading'] == 'lazy',
                width=img['width'] if img['width'] > 0 else None,
                height=img['height'] if img['height'] > 0 else None
            ))

        # 9. INDEX STATUS
        robots_meta = await page.evaluate("""() => {
            const meta = document.querySelector('meta[name=\"robots\"]');
            return meta ? meta.getAttribute('content') : null;
        }""")

        canonical = await page.evaluate("""() => {
            const link = document.querySelector('link[rel=\"canonical\"]');
            return link ? link.href : null;
        }""")

        x_robots = response.headers.get('x-robots-tag', '') if response else ''

        is_indexable = True
        if robots_meta and 'noindex' in robots_meta.lower():
            is_indexable = False
        if x_robots and 'noindex' in x_robots.lower():
            is_indexable = False

        index_status = {
            "is_indexable": is_indexable,
            "robots_meta": robots_meta,
            "x_robots_tag": x_robots,
            "canonical": canonical,
            "note": "Use 'site:" + target_url + "' in Google for live index check"
        }

        # 10. FAQ DETECTION
        faq_schema = await page.evaluate("""() => {
            const scripts = document.querySelectorAll('script[type=\"application/ld+json\"]');
            for (const script of scripts) {
                try {
                    const data = JSON.parse(script.innerText);
                    if (data['@type'] === 'FAQPage' || (Array.isArray(data['@graph']) && data['@graph'].some(g => g['@type'] === 'FAQPage'))) {
                        return true;
                    }
                } catch(e) {}
            }
            return false;
        }""")

        faq_visual = await page.evaluate("""() => {
            const text = document.body.innerText.toLowerCase();
            const hasFaqHeading = Array.from(document.querySelectorAll('h2, h3')).some(h => 
                h.innerText.toLowerCase().includes('faq') || h.innerText.toLowerCase().includes('frequently')
            );
            const hasQuestions = (text.split("?").length - 1) > 3;
            return hasFaqHeading || hasQuestions;
        }""")

        has_faq = faq_schema or faq_visual
        faq_details = {
            "has_schema": faq_schema,
            "has_visual_section": faq_visual
        }

        # 11. SCHEMA ANALYSIS
        schemas = []
        schema_scripts = await page.evaluate("""() => {
            const scripts = document.querySelectorAll('script[type=\"application/ld+json\"]');
            return Array.from(scripts).map(s => s.innerText);
        }""")

        rich_snippet_types = ['Product', 'Recipe', 'Review', 'Event', 'JobPosting', 'Course', 'SoftwareApplication']

        for script_text in schema_scripts:
            try:
                data = json.loads(script_text)
                schemas_to_check = [data] if not isinstance(data, list) else data
                if isinstance(data, dict) and '@graph' in data:
                    schemas_to_check = data['@graph']

                for schema in schemas_to_check:
                    if not isinstance(schema, dict):
                        continue
                    schema_type = schema.get('@type', 'Unknown')
                    if isinstance(schema_type, list):
                        schema_type = schema_type[0]

                    has_rich = schema_type in rich_snippet_types
                    rich_type = schema_type if has_rich else None

                    if schema_type == 'Product' and ('aggregateRating' in schema or 'review' in schema):
                        has_rich = True
                        rich_type = 'Product (with Reviews)'

                    schemas.append(SchemaInfo(
                        type=schema_type, raw_json=schema,
                        is_valid=True, has_rich_snippet=has_rich,
                        rich_snippet_type=rich_type
                    ))
            except json.JSONDecodeError:
                pass

        # HEADINGS
        headings = await page.evaluate("""() => {
            const result = {};
            for (let i = 1; i <= 6; i++) {
                const tags = document.querySelectorAll('h' + i);
                result['h' + i] = Array.from(tags).map(h => h.innerText.trim()).filter(t => t);
            }
            return result;
        }""")

        word_count = len(page_text.split())

        internal_links = sum(1 for l in links_data if urllib.parse.urlparse(l['href']).netloc == base_domain or not urllib.parse.urlparse(l['href']).netloc)
        external_links = len(links_data) - internal_links

        viewport = await page.evaluate("""() => {
            const meta = document.querySelector('meta[name=\"viewport\"]');
            return meta ? meta.getAttribute('content') : null;
        }""")

        lang = await page.evaluate("""() => document.documentElement.lang || null""")

        # CALCULATE SCORE
        score = 100
        if title_status == "missing": score -= 15
        elif title_status == "too_long": score -= 5
        if desc_status == "missing": score -= 10
        elif desc_status == "too_long": score -= 5
        score -= min(len(broken_4xx) * 3, 15)
        score -= min(len(redirects_3xx) * 2, 10)
        score -= min(sum(1 for img in images_analysis if not img.has_alt) * 2, 10)
        if not canonical: score -= 3
        if not is_indexable: score -= 20
        if not viewport: score -= 10
        if not schemas: score -= 5
        if not has_form: score -= 3
        if phones_found and not all(p.is_clickable for p in phones_found): score -= 3
        if emails_found and not all(e.has_mailto_link for e in emails_found): score -= 2

        score = max(0, min(100, score))

        await context.close()

        return SEOAuditResult(
            url=target_url, audit_date=datetime.now().isoformat(),
            title=title_analysis, meta_description=meta_description,
            redirects_3xx=redirects_3xx, broken_4xx=broken_4xx,
            phones=phones_found, emails=emails_found,
            has_contact_form=has_form, contact_form_details=form_details,
            images=images_analysis, index_status=index_status,
            has_faq=has_faq, faq_details=faq_details,
            schemas=schemas, headings=headings,
            canonical=canonical, robots_meta=robots_meta,
            viewport=viewport, lang=lang,
            word_count=word_count, internal_links=internal_links,
            external_links=external_links, page_load_time_ms=load_time,
            score=score
        )

    def result_to_dict(self, result):
        data = asdict(result)
        data['title'] = asdict(result.title)
        data['meta_description'] = asdict(result.meta_description)
        data['redirects_3xx'] = [asdict(r) for r in result.redirects_3xx]
        data['broken_4xx'] = [asdict(b) for b in result.broken_4xx]
        data['phones'] = [asdict(p) for p in result.phones]
        data['emails'] = [asdict(e) for e in result.emails]
        data['images'] = [asdict(i) for i in result.images]
        data['schemas'] = [asdict(s) for s in result.schemas]
        return data


async def main():
    parser = argparse.ArgumentParser(description='SEO Audit Tool')
    parser.add_argument('url', help='URL to audit')
    parser.add_argument('--output', '-o', default='seo_audit_result.json', help='Output JSON file')
    args = parser.parse_args()

    auditor = SEOAuditor()
    await auditor.init()

    try:
        print(f"Auditing: {args.url}")
        result = await auditor.audit(args.url)
        data = auditor.result_to_dict(result)

        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\nAudit complete! Score: {result.score}/100")
        print(f"Results saved to: {args.output}")

        print(f"\n=== SUMMARY ===")
        print(f"Title: {result.title.text[:60]}... [{result.title.char_count} chars, {result.title.pixel_width}px] ({result.title.status})")
        print(f"Description: {result.meta_description.text[:80]}... [{result.meta_description.char_count} chars] ({result.meta_description.status})")
        print(f"3xx Redirects: {len(result.redirects_3xx)}")
        print(f"4xx Broken: {len(result.broken_4xx)}")
        print(f"Phones found: {len(result.phones)}")
        print(f"Emails found: {len(result.emails)}")
        print(f"Contact form: {'Yes' if result.has_contact_form else 'No'}")
        print(f"Images: {len(result.images)} (missing alt: {sum(1 for i in result.images if not i.has_alt)})")
        print(f"FAQ: {'Yes' if result.has_faq else 'No'}")
        print(f"Schema types: {', '.join(set(s.type for s in result.schemas)) or 'None'}")
        print(f"Indexable: {'Yes' if result.index_status['is_indexable'] else 'No'}")
        print(f"Load time: {result.page_load_time_ms:.0f}ms")

    finally:
        await auditor.close()


if __name__ == "__main__":
    asyncio.run(main())
