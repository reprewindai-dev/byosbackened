# Veklom Pricing and Entitlement Draft

## Subscription Tiers (Stripe Recurring Products)

| Tier | Monthly Price | Annual Price | Description |
|------|---------------|--------------|-------------|
| **Starter** | $99/month | $990/year | For builders and small teams testing controlled backend access |
| **Pro** | $499/month | $4,990/year | For AI teams and agencies trying to reduce waste |
| **Sovereign** | $2,500/month | $25,000/year | For regulated teams that need control and evidence |
| **Enterprise** | Custom | Custom | For banks, hospitals, government, defense |

### Starter Tier ($99/month)
**Includes:**
- Account access, login/session/profile
- Limited API keys (max 5)
- Basic health/status endpoints
- Limited execution (10K tokens/month included)
- Basic token wallet
- Limited cost prediction
- Basic usage summary
- Essential marketplace access
- Standard support (email, 48h response)

**Does NOT include:**
- Kill switch
- Compliance reports
- Audit verification
- Advanced routing
- Advanced security controls
- Plugin execution
- Enterprise admin controls
- SLA guarantees

### Pro Tier ($499/month)
**Includes Starter plus:**
- Higher execution limits (100K tokens/month included)
- Routing select/statistics
- Cost prediction/history
- Savings insights
- Projected savings
- Budget status/forecast
- Billing breakdown
- Performance metrics
- Alerts summary
- Text content scan
- Job history
- Search/usage analytics
- Token top-ups
- Priority support (email, 24h response)

**Positioning:** Optimize usage before it becomes waste.

### Sovereign Tier ($2,500/month)
**Includes Pro plus:**
- Hard budget caps
- Kill switch (emergency cost control)
- Audit logs
- Audit verification
- Compliance checks/reports
- Privacy workflows
- Explainability
- Detailed health
- Threat stats
- Security controls
- File scan
- Content logs
- Governed execution
- Audit/compliance exports
- SLA guarantees (99.9% uptime)
- Dedicated support channel
- White-label rights

**Positioning:** Govern execution before it becomes risk.

### Enterprise Tier (Custom)
**Includes Sovereign plus:**
- Custom endpoint access
- Custom usage limits
- Custom compliance package
- Dedicated support
- Workspace/user administration
- Advanced security control operations
- Custom routing rules
- Training/custom optimization
- Private deployment path
- Dedicated worker/GPU strategy
- MSA/procurement support
- Custom SLA (99.99% uptime)
- Priority engineering channel
- Annual architecture review
- Penetration test report

**Positioning:** Private control for serious AI operations.

---

## Token Packs (Stripe One-Time Products)

Token packs provide additional usage credits beyond monthly allotments.

| Pack | Price | Credits | Bonus | Effective Rate |
|------|-------|---------|-------|----------------|
| **Starter Pack** | $25 | 2,500,000 | - | 100K credits/$1 |
| **Growth Pack** | $100 | 12,000,000 | 20% | 120K credits/$1 |
| **Team Pack** | $500 | 75,000,000 | 50% | 150K credits/$1 |
| **Enterprise Pack** | $2,000 | 350,000,000 | 75% | 175K credits/$1 |

### Token Pack Details

**Starter Pack ($25)**
- 2.5 million credits
- No bonus
- Best for: Testing, small projects, topping up

**Growth Pack ($100)**
- 12 million credits (20% bonus over base rate)
- Best for: Growing teams, moderate usage
- Most popular choice

**Team Pack ($500)**
- 75 million credits (50% bonus over base rate)
- Best for: Teams, agencies, production workloads
- Includes priority support for 30 days

**Enterprise Pack ($2,000)**
- 350 million credits (75% bonus over base rate)
- Best for: Large operators, high-volume processing
- Includes dedicated support for 90 days

---

## Token/Credit Cost Model

### Token Cost Reference (Per-Endpoint)

| Endpoint Type | Token Cost | Credit Class |
|---------------|------------|--------------|
| **Basic gateway pass-through** | 10 tokens/call | low |
| **Standard routing** | 15 tokens/call | standard |
| **Cost-aware routing** | 25 tokens/call | standard |
| **Audit/compliance workflow** | 30 tokens/call | standard |
| **Locker security scan** | 40 tokens/call | heavy |
| **Heavy autonomous execution** | 50 tokens/call | heavy |
| **Compliance report** | 250-2,500 tokens/call | compliance |
| **LLM execution (exec)** | Variable (based on tokens used) | variable |

### Variable Cost Calculation (exec_router)

For LLM execution, token cost is calculated as:
```
token_cost = base_cost + (input_tokens * input_rate) + (output_tokens * output_rate)

Where:
- base_cost = 100 tokens
- input_rate = 1 token per 10 input tokens
- output_rate = 1 token per 5 output tokens

Example:
- Input: 1000 tokens
- Output: 500 tokens
- Cost = 100 + (1000/10) + (500/5) = 100 + 100 + 100 = 300 tokens
```

---

## Monthly Included Credits

| Tier | Monthly Included Credits | Overage Rate |
|------|-------------------------|--------------|
| Starter | 10,000,000 (10M) | $0.001 per 1K credits |
| Pro | 100,000,000 (100M) | $0.0008 per 1K credits |
| Sovereign | 500,000,000 (500M) | $0.0005 per 1K credits |
| Enterprise | Custom | Custom |

**Note:** Credits do not roll over month-to-month. Unused credits expire at billing period end.

---

## Wallet Ledger Rules

1. **Atomic Deduction**: Deduct tokens atomically per request BEFORE execution
2. **Insufficient Balance**: If wallet balance < token_cost for route → reject with 402 Payment Required
3. **Ledger Entry**: Every deduction writes to token_ledger table with:
   - user_id
   - endpoint_id
   - tokens_deducted
   - balance_before
   - balance_after
   - timestamp
   - request_id (for correlation)

4. **Top-up Flow**: Token top-ups from Stripe webhook → credit wallet → write to ledger as "credit" transaction

5. **Source of Truth**: Wallet balance column is the source of truth. Never derive from summing ledger rows at runtime.

6. **Caching**: Cache wallet balance in Redis with 5-minute TTL for read-heavy operations.

---

## Stripe Product Structure

### Recurring Products (Subscriptions)

```
Product: Veklom Starter
  ├── Price: $99/month (recurring)
  └── Price: $990/year (recurring, 2 months free)

Product: Veklom Pro
  ├── Price: $499/month (recurring)
  └── Price: $4,990/year (recurring, 2 months free)

Product: Veklom Sovereign
  ├── Price: $2,500/month (recurring)
  └── Price: $25,000/year (recurring, 2 months free)

Product: Veklom Enterprise
  └── Custom pricing (manual invoice)
```

### One-Time Products (Token Packs)

```
Product: Veklom Token Pack - Starter
  └── Price: $25 (one-time)
  └── Metadata: credits=2500000

Product: Veklom Token Pack - Growth
  └── Price: $100 (one-time)
  └── Metadata: credits=12000000

Product: Veklom Token Pack - Team
  └── Price: $500 (one-time)
  └── Metadata: credits=75000000

Product: Veklom Token Pack - Enterprise
  └── Price: $2,000 (one-time)
  └── Metadata: credits=350000000
```

---

## Stripe Webhook Events

### Subscription Events
- `customer.subscription.created` → Create subscription record
- `customer.subscription.updated` → Update plan entitlements
- `customer.subscription.deleted` → Cancel subscription, downgrade to free
- `invoice.paid` → Add monthly included credits
- `invoice.payment_failed` → Notify user, grace period

### Checkout Events
- `checkout.session.completed` → Credit token wallet (token packs)

### Payment Events
- `payment_intent.succeeded` → Record successful payment
- `payment_intent.payment_failed` → Log failed payment attempt

---

## Plan Entitlement Matrix

| Feature | Starter | Pro | Sovereign | Enterprise |
|---------|---------|-----|-----------|------------|
| **Auth & Session** | ✅ | ✅ | ✅ | ✅ |
| **API Keys** | 5 | 20 | 100 | Unlimited |
| **Basic Health/Status** | ✅ | ✅ | ✅ | ✅ |
| **Cost Prediction** | Limited | ✅ | ✅ | ✅ |
| **Budget Management** | View only | ✅ | ✅ | ✅ |
| **Routing Selection** | ❌ | ✅ | ✅ | ✅ |
| **Savings Insights** | ❌ | ✅ | ✅ | ✅ |
| **Content Scan** | Text only | ✅ | ✅ | ✅ |
| **Kill Switch** | ❌ | ❌ | ✅ | ✅ |
| **Audit Logs** | Last 7 days | Last 30 days | ✅ | ✅ |
| **Compliance Reports** | ❌ | ❌ | ✅ | ✅ |
| **Privacy Tools** | Basic | Basic | ✅ | ✅ |
| **Security Dashboard** | ❌ | ❌ | ✅ | ✅ |
| **Plugin Management** | ❌ | ❌ | ✅ | ✅ |
| **Custom Training** | ❌ | ❌ | ❌ | ✅ |
| **SLA Guarantee** | None | None | 99.9% | 99.99% |
| **Support** | Email (48h) | Email (24h) | Priority | Dedicated |
| **Monthly Credits** | 10M | 100M | 500M | Custom |
| **White-label** | ❌ | ❌ | ✅ | ✅ |

---

## Upgrade/Downgrade Rules

### Upgrades
- Immediate effect upon payment confirmation
- Prorated charges for current billing period
- New monthly credit allotment takes effect immediately
- Unused credits from previous tier do NOT roll over

### Downgrades
- Takes effect at end of current billing period
- User keeps current tier until period ends
- No refunds for prepaid annual subscriptions
- Can downgrade to lower tier or free (limited access)

### Cancellation
- Access continues until end of billing period
- No refunds for partial months
- Data retained for 90 days, then archived
- Can reactivate within 90 days without data loss

---

## Promotional Pricing

### Launch Promotion (First 30 Days)
- 50% off first 3 months for new customers
- Code: `VEKLOM50`
- Applies to Starter, Pro, Sovereign tiers
- Not combinable with annual discount

### Annual Discount
- 2 months free when paying annually
- Equivalent to ~17% discount
- Applied automatically at checkout

### Non-Profit / Open Source
- 50% discount for verified non-profits
- 100% discount for open source projects (application required)
- Contact sales@veklom.com

---

## Revenue Sharing (Future)

When marketplace vendors are added:

- Platform fee: 20-30% of vendor revenue
- Vendor receives: 70-80% of revenue
- Minimum payout: $100
- Payout schedule: Monthly, NET-15
- Payment methods: ACH, Wire, PayPal

---

## Pricing Comparison (Competitive Analysis)

| Competitor | Their Price | Veklom Equivalent | Our Price | Savings |
|------------|-------------|-------------------|-----------|---------|
| Helicone | $2K-10K/mo | Pro | $499/mo | 75% |
| LangSmith | $1.5K-5K/mo | Pro | $499/mo | 67% |
| Portkey | $2K-10K+/mo | Pro | $499/mo | 75% |
| Custom Build | $500K-2M | Sovereign | $2,500/mo | 99% |

---

## Billing FAQ

**Q: What happens when I run out of credits?**
A: API requests return 402 Payment Required. You can purchase token packs or upgrade your plan.

**Q: Do credits roll over?**
A: No, monthly included credits expire at the end of each billing period.

**Q: Can I buy credits without a subscription?**
A: No, token packs require an active subscription (Starter or higher).

**Q: How do I cancel?**
A: Use the billing portal or contact support. Access continues until period end.

**Q: Is there a free tier?**
A: Not at launch. Plans start at $99/month. Contact sales for trial access.

**Q: Can I change plans mid-cycle?**
A: Upgrades are immediate. Downgrades take effect at period end.

---

## Implementation Notes

### Database Schema Required
- `token_wallet` table (workspace_id, balance, updated_at)
- `token_transactions` table (id, workspace_id, type, amount, balance_before, balance_after, metadata, created_at)
- `subscription` table (existing - add monthly_credits_included column)

### Stripe Configuration Required
- Product and price IDs for each tier
- Webhook endpoint configured
- Webhook secret stored securely
- Test and live mode keys separated

### Environment Variables Required
```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_STARTER_PRICE_ID=price_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_SOVEREIGN_PRICE_ID=price_...
STRIPE_TOKEN_PACK_25_PRICE_ID=price_...
STRIPE_TOKEN_PACK_100_PRICE_ID=price_...
STRIPE_TOKEN_PACK_500_PRICE_ID=price_...
STRIPE_TOKEN_PACK_2000_PRICE_ID=price_...
```

---

*Draft Version: 1.0*
*Last Updated: 2026-04-27*
