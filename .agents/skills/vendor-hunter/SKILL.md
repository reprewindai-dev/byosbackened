---
name: vendor-hunter-agent
description: Playbook for Phase 2 vendor hunter agents (010-031). Covers automated vendor discovery, outreach, and onboarding across 20 platforms.
---

# Vendor Hunter Agent Playbook

## When to Use
Invoke this skill when spinning up any Phase 2 vendor acquisition agent (Agent-010 through Agent-031).

## Prerequisites
- Access to `byosbackened` repo
- Selenium + ChromeDriver (headless only)
- Platform-specific API keys where applicable (GitHub, HuggingFace, etc.)

## Important Constraints
- **Headless scrapers only** — headful webscrapers conflict with the machine's built-in browser
- Use Selenium and ChromeDriver, NOT Playwright for crawling
- Playwright/CDP is reserved for browser agents (090-093) interacting with Veklom's own UI
- Respect robots.txt and rate limits on all platforms

## Setup Steps

1. Read your agent mission file from `agents/phase2-vendor-acquisition/agent-{ID}-{name}.md`
2. Read `MASTER_STATE.md` for current vendor pipeline state
3. Check `PROGRESS.md` for vendor counts and targets

## Platform Assignments

| Agent | Platform | Discovery Method |
|---|---|---|
| 010 | GitHub | API search for AI/ML repos with >100 stars |
| 011 | HuggingFace | Model hub API, trending models |
| 012 | Product Hunt | Daily AI tool launches |
| 013 | Reddit | r/MachineLearning, r/artificial, r/LocalLLaMA |
| 014 | X/Twitter | AI tool creators, #buildinpublic |
| 015 | LinkedIn | AI startup founders, company pages |
| 016 | Indie Hackers | AI product makers |
| 017 | Hacker News | Show HN: AI tools |
| 018 | Dev.to | AI/ML tagged articles |
| 019 | PyPI/npm | New AI packages with >1k downloads |
| 020 | Discord | AI Discord servers |
| 021 | arXiv | Papers with code releases |
| 022 | Replicate | Model creators |
| 023 | Kaggle | Competition winners, dataset creators |
| 024 | Y Combinator | YC AI/ML startups |
| 025 | Conferences | NeurIPS, ICML, ACL speaker lists |
| 026 | App Directories | AI app stores, alternatives.to |
| 027 | Enterprise | Enterprise AI vendor lists |
| 028 | Open Source | CNCF, Apache, Linux Foundation AI projects |
| 029 | YouTube | AI tool reviewers, tutorial creators |

## Crawler Template

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=options)

# Platform-specific scraping logic here
driver.get("https://platform-url.com/search?q=ai+tools")

# Extract vendor candidates
results = driver.find_elements(By.CSS_SELECTOR, ".result-item")
vendors = []
for r in results:
    vendors.append({
        "name": r.find_element(By.CSS_SELECTOR, ".name").text,
        "url": r.find_element(By.CSS_SELECTOR, "a").get_attribute("href"),
        "description": r.find_element(By.CSS_SELECTOR, ".desc").text
    })

driver.quit()
```

## Output Format

Each vendor discovery should produce a JSON entry:
```json
{
  "vendor_name": "ExampleAI",
  "platform": "github",
  "url": "https://github.com/example/ai-tool",
  "contact_email": "founder@example.com",
  "category": "NLP",
  "stars_or_users": 5000,
  "discovery_date": "2024-01-15",
  "outreach_status": "pending"
}
```

## Completion Checklist
- [ ] Read mission file and MASTER_STATE.md
- [ ] Build headless scraper for assigned platform
- [ ] Discover minimum 5 vendor candidates
- [ ] Generate vendor candidate JSON
- [ ] Update PROGRESS.md with vendor count
- [ ] Create PR with scraper code and results
