# SEO Audit Tool

A complete webpage scraping tool for SEO audits built from scratch.

## Features

1. **Page Title Analysis** - Character count & pixel width measurement
2. **Meta Description** - Character count & pixel width measurement
3. **3xx Redirect Links** - Status codes, follow/nofollow detection
4. **4xx Broken Links** - Status codes, follow/nofollow detection
5. **Phone Numbers** - Visibility, tel: links, clickability
6. **Email Addresses** - Visibility, mailto: links, obfuscation
7. **Contact Forms** - Detection and validation
8. **Image Analysis** - Alt tags, types, lazy loading, dimensions
9. **Index Status** - Robots meta, canonical, indexability
10. **FAQ Detection** - Schema markup & visual section detection
11. **Schema Markup** - Type detection, rich snippet eligibility

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Usage

### Command Line
```bash
# Basic audit
python seo_auditor.py https://example.com

# Save to specific file
python seo_auditor.py https://example.com -o my_audit.json
```

### Python API
```python
import asyncio
from seo_auditor import SEOAuditor

async def main():
    auditor = SEOAuditor()
    await auditor.init()
    result = await auditor.audit("https://example.com")
    print(f"SEO Score: {result.score}/100")
    await auditor.close()

asyncio.run(main())
```

### Dashboard
Open `dashboard.html` in your browser to view results visually.

## Architecture

- **Backend**: Python 3.8+ with Playwright (Chromium)
- **Frontend**: Pure HTML/CSS/JS dashboard
- **Data Format**: JSON output compatible with dashboard

## SEO Score Calculation

The tool calculates a 0-100 score based on:
- Title optimization (15 pts)
- Meta description (10 pts)
- Broken links penalty (-3 per link)
- Missing alt tags (-2 per image)
- Indexability (20 pts)
- Mobile viewport (10 pts)
- Schema markup (5 pts)
- Contact form (3 pts)
- Clickable phone/email (5 pts)

## Additional Features

- Heading structure analysis (H1-H6)
- Word count
- Internal/external link counts
- Page load time measurement
- Language detection
