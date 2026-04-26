# 🇪🇺 EU / UK Representative — Read Before First European Customer

**Status:** NOT NEEDED YET. Set up only when a paying EU or UK customer is on the table.
**Cost:** ~$200-500/mo (EU) + ~$100-200/mo (UK) — combined services exist.
**Time to set up:** 1-3 business days online. No travel, no notarization.

---

## What this is

GDPR Article 27 (and the UK equivalent post-Brexit) requires any company that:

1. Has **no establishment** (office, employee, subsidiary) in the EU/UK, AND
2. **Targets, sells to, or monitors** people in the EU/UK,

…to appoint a **"representative"** — a third-party firm physically in the EU/UK whose
job is to be the contact point for data-protection regulators and data subjects.

You list them in your Privacy Policy. That's it. They forward any regulator/user
inquiries to you. They are NOT a lawyer, NOT a DPO, NOT a tax agent.

## When you need it

✅ **Need it:** First paying customer with users/employees in any EU member state
or the UK. Even ONE.

❌ **Don't need it:** EU residents browsing your website with no signup, no payment,
no data collection beyond Cloudflare analytics (cookieless). Your current site is
fine as-is.

✅ **Need it:** EU customer signs MSA, pays an invoice, deploys Veklom in their
own VPC. Yes — even though their data never touches your infra, the **business
relationship** counts as "offering services" under GDPR Article 3(2).

## Cheapest reputable services (verified Apr 2026)

| Provider | EU Rep | UK Rep | Combined | Notes |
|---|---:|---:|---:|---|
| **Prighter** | €99/mo | £39/mo | **€138/mo (~$150)** | German, used by ~6k SaaS companies. Self-serve signup, online dashboard, fastest. **Recommended.** |
| **DataRep** | €40/mo | £40/mo | **€80/mo (~$87)** | UK-based, cheapest reputable. Slightly less polished dashboard than Prighter. |
| **EDPO** | €1,200/yr | £600/yr | **~$200/mo** | Belgian law firm-tier. Overkill for early stage. |
| **Mauve Group** | quote-based | quote-based | $$$ | Enterprise; ignore until you're at $1M+ ARR. |

**Pick:** DataRep if you want cheapest. Prighter if you want polish. Both are fine.
Skip if you don't have an EU/UK customer yet.

## Sign-up steps (when the day comes)

1. Confirm the customer's data subjects are actually in the EU/UK.
2. Sign up at https://prighter.com or https://datarep.com.
3. Pay the first month.
4. They'll send you an address block to paste into your Privacy Policy.
5. Update `landing/legal/privacy.html` — search for "EU/UK Representative" placeholder.
6. Notify your customer's procurement team you've appointed one. Score points.

## What happens if you skip this

- Most likely: **nothing**, because EU regulators rarely chase small US SaaS.
- Worst case: a regulator or data subject lodges a complaint, can't find a contact,
  and your customer's legal team panics + cancels.
- Fines are theoretical (max 4% global revenue) but enforcement against tiny
  US vendors is near-zero. The **real cost** is the deal you lose because the
  customer's privacy team can't tick the box.

## Other "global compatibility" boxes (do NOT pre-pay)

| Jurisdiction | Trigger | Cost when triggered |
|---|---|---:|
| **Brazil (LGPD)** | Brazilian customer | $0 (your privacy policy already covers it) |
| **Switzerland (FADP)** | Swiss customer | ~$100/mo Swiss Rep (Prighter sells this too) |
| **California (CCPA)** | CA resident with $25M+ revenue OR 100k+ records | Already covered in privacy.html |
| **Quebec (Law 25)** | Quebec customer | Designate a "Privacy Officer" — that's you the founder, free |
| **Australia, Japan, India** | Local customer | Privacy policy covers it; no rep needed |

---

## Decision rule

> **"Has someone written me a real check from Europe yet?"**
>
> No → ignore this file.
> Yes → sign up at DataRep or Prighter the same week. Add to privacy policy. Done.

---

_Last reviewed: 2026-04-26. Re-verify pricing before signing up — the market shifts._
