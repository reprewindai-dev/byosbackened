---
name: browser-agent
description: Playbook for browser agents (090-093) — the "hands and arms" of the workforce. Uses Playwright/CDP for UI automation, form filling, and flow testing.
---

# Browser Agent Playbook (Hands & Arms)

## When to Use
Invoke this skill when spinning up browser agents that need to interact with Veklom's UI.

## Prerequisites
- Access to `byosbackened` repo
- Playwright installed (`pip install playwright`)
- Chrome running with CDP on `http://localhost:29229`

## Important Constraints
- Browser agents use **Playwright via CDP** to interact with Veklom's own UI
- This is DIFFERENT from crawler agents which use Selenium for external sites
- Always capture screenshots as evidence
- Auth state persists after scripts run — just refresh and continue

## Connection Pattern

```python
from playwright.sync_api import sync_playwright

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://localhost:29229")
context = browser.contexts[0]
page = context.pages[0]
```

## Agent Assignments

### Agent-090 (Browser Lead)
- Coordinate browser agent tasks
- Maintain shared Playwright utilities
- Review test evidence screenshots

### Agent-091 (Signup & Onboarding)
- Automate user registration flow
- Test onboarding wizard steps
- Verify email confirmation flow

```python
page.goto("https://veklom.com/register")
page.fill('[name="name"]', 'Test User')
page.fill('[name="email"]', 'test@example.com')
page.fill('[name="password"]', 'SecurePass123!')
page.click('button[type="submit"]')
page.wait_for_url("**/onboarding")
page.screenshot(path="evidence/signup-success.png")
```

### Agent-092 (Marketplace & Purchase)
- Browse marketplace catalog
- Test tool purchase flow
- Verify payment processing

```python
page.goto("https://veklom.com/marketplace")
page.click('[data-testid="tool-card"]:first-child')
page.click('button:text("Purchase")')
page.wait_for_selector('[data-testid="payment-form"]')
page.screenshot(path="evidence/purchase-flow.png")
```

### Agent-093 (Admin & Settings)
- Test admin dashboard functionality
- Verify vendor management flows
- Test settings/profile updates

## Evidence Collection

Always capture screenshots at key steps:
```python
page.screenshot(path=f"evidence/{test_name}-{step}.png")
```

## Completion Checklist
- [ ] Read mission file from `agents/eyes-visual/agent-{ID}-*.md`
- [ ] Connect to Chrome via CDP
- [ ] Execute assigned UI flows
- [ ] Capture evidence screenshots
- [ ] Report pass/fail status
- [ ] Update PROGRESS.md
