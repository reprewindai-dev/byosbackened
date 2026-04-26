# BYOS Landing Page

A single-file premium landing page. **No build step, no dependencies, no framework.** Open `index.html` in a browser — that's it.

## What's in it

- Modern dark hero with gradient + animated glow
- 4 hero stat callouts (126 routes, 21K LOC, 100% success, $0 lock-in) — all verified facts
- Embedded demo video placeholder (replace with your Loom)
- 8-feature grid
- **Side-by-side comparison vs. Portkey / LangSmith / Helicone / Langfuse** with verified pricing
- Real stress test results with full transparency caveat
- 3-tier pricing — Starter ($1.5K/mo), Pro ($3.5K/mo highlighted), Outright ($300K)
- "Who buys this" segmentation (vertical SaaS, agencies, mid-market, enterprise)
- 7-question FAQ
- Bold CTA section with mailto + LinkedIn

## Before you publish

Edit `landing/index.html` and replace these placeholders:

| Find | Replace with |
|---|---|
| `YOUR_EMAIL@example.com` | Your actual email |
| `YOUR_HANDLE` (in LinkedIn URL) | Your LinkedIn handle |
| The placeholder `<div>` in the demo video section | `<iframe src="https://www.loom.com/embed/YOUR_VIDEO_ID" frameborder="0" allowfullscreen class="w-full h-full"></iframe>` |

That's it. Everything else is plug-and-play.

## Where to host it (free)

| Option | Time | Cost | Custom domain? |
|---|---|---:|---|
| **GitHub Pages** | 5 min | $0 | Yes (free, with your domain) |
| **Cloudflare Pages** | 5 min | $0 | Yes (free) |
| **Netlify drop** | 60 seconds — drag the folder onto netlify.com/drop | $0 | Yes (free) |
| **Vercel** | 5 min | $0 | Yes (free) |
| **Same Cloudflare Tunnel as your API** | already set up | $0 | Yes |

Netlify Drop is the fastest if you've never deployed a site before — literally drag the `landing/` folder onto the page and you have a URL.

## Customizing further

The whole page is in one file. Tailwind via CDN means you can edit any class inline and refresh the browser — instant feedback. No build, no npm, no nothing.

Sections to potentially edit:

- **Hero stats** (`126`, `21K`, `100%`, `$0`) — search for those, change as needed
- **Comparison table** — add/remove competitors
- **Pricing tiers** — change dollar amounts, swap features
- **FAQ** — add your own questions

## Posting it on LinkedIn

When you have the deployed URL, here's a launch post that's not cringe:

---

> Spent 12 months building an AI operations platform — multi-LLM gateway, cost intelligence, RBAC, GDPR, audit, billing, kill switches. The kind of thing companies pay Portkey or LangSmith $5K–$10K/month to use as SaaS.
>
> Today I'm making it source-available. License it for $3,500/mo and self-host. Or buy outright at $300K with full IP transfer.
>
> Why? Because every serious enterprise I've talked to wants self-hosted, not vendor lock-in. And small teams can't justify $10K/mo for a SaaS feature surface this broad.
>
> If you're building anything with LLMs, take a look:
> [your URL]
>
> 5-minute demo on the page. Real stress tests. Full audit report in the repo. No marketing fluff.
>
> DMs open for serious buyers and strategic acquirers.

---

That's it. Don't overthink it.
