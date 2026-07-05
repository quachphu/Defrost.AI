# BUSINESS_MODEL.md — How Defrost.AI should monetize

**Prepared:** July 2026 · **Status:** recommendation for founder decision — nothing on the site states a final price.
**Method:** every factual claim below was fetched from a live web source in this session (cited inline) or comes from the repo's own `docs/WEBSITE_SPEC.md` (which carries its own citations, marked `[spec]`). No figures are invented. Unverified items are flagged `⚠️`.

---

## 1. How comparable companies actually monetize (fetched evidence)

| Company | Who pays | Model | Source |
|---|---|---|---|
| **Zillow Rentals** | Landlords / property managers | Listing/advertising fees (~$9.99–$29.99 per listing/mo for small landlords; subscriptions or pay-per-lease for 25+ unit operators). Rentals revenue $159M in Q2 2025, +36% YoY. | [Sharetribe: How does Zillow make money](https://www.sharetribe.com/how-to-build/how-does-zillow-make-money/), [Motley Fool](https://www.fool.com/investing/how-to-invest/stocks/how-does-zillow-make-money/), [Zillow FY2025 8-K](https://www.sec.gov/Archives/edgar/data/0001617640/000161764025000149/exhibit993.htm) |
| **Apartments.com (CoStar)** | Property managers / owners | Annual advertising subscription contracts; >70,000 properties advertising; >$1B annualized run-rate revenue (Jan 2024). | [CoStar investor release](https://investors.costargroup.com/news-releases/news-release-details/costar-group-2023-revenue-increased-13-apartmentscom-crosses-1) |
| **Zumper** | Mostly landlords; some renter fees | Free listings <10 units; paid promoted placement + "PowerLeads AI" lead delivery for multifamily; per-transaction fees on leases closed through its tools; renter pays $30 screening-report fee and 2.95% card-payment fee. | [Zumper help center](https://help.zumper.com/hc/en-us/articles/360045803273--Does-it-cost-to-post-on-Zumper-), [Canvas Business Model: Zumper](https://canvasbusinessmodel.com/blogs/how-it-works/zumper-how-it-works) |
| **Apartment List** | Property managers | Performance/success model — paid only when a matched renter moves in; reported ~20%–100%+ of one month's rent per signed lease (range varies by market/agreement) ⚠️ third-party estimate, not company-published. | [Vizologi: Apartment List business model](https://vizologi.com/business-strategy-canvas/apartment-list-business-model-canvas/), [Wikipedia: Apartment List](https://en.wikipedia.org/wiki/Apartment_List) |
| **Texas apartment locators** | The property (never the renter) | Success/referral fee when the locator's client signs a lease — a percentage of first month's rent or flat fee; standard practice in TX; requires a real-estate license; rebating part of the fee to the tenant is allowed with conditions. | [TexasAptLocators: What is a locator fee](https://www.texasaptlocators.com/blog/what-is-a-locator-fee/), [TREC FAQ on locator rebates](https://www.trec.texas.gov/can-rental-locator-rebate-portion-rental-locator%E2%80%99s-fee-received-apartment-complex-prospective-tenant) |
| **EliseAI** (landlord-side AI contrast) | Property managers | Per-unit/month SaaS — published list prices from $2.05/unit/mo (Funnel Essentials) to $3.70/unit/mo (Funnel Intelligence); quote-based enterprise deals. | [EliseAI blog: AI property management software costs](https://eliseai.com/blog/ai-property-management-software-costs) |
| **Renter-side AI agents** | — | No established renter-side AI agent with published subscription pricing surfaced in this session's searches (Renty.AI and similar are free search layers). The `[spec]` cites EU renter-agent comps at €15–30/mo ⚠️ founder-memo figure, spot-check before using in public copy. | Session searches, July 2026; `docs/WEBSITE_SPEC.md` §D.3 |

**The pattern:** every scaled US rental marketplace is paid by the landlord side (advertising, leads, or per-lease success fees). That is exactly the conflict of interest Defrost.AI positions against — and it means the renter-side lane has no entrenched pricing convention to undercut.

## 2. California legal constraints that shape the choice (from `docs/WEBSITE_SPEC.md`, cited there)

- **Advance fees charged to renters for listings** trigger California's **Prepaid Rental Listing Service (PRLS)** regime: listings-supply only ("negotiation of the rental of property is not a part of this activity"), $10,000 bond per location, DRE-approved contract, 90-day cap + refund rights. Source fetched in spec: [DRE PRLS page](https://www.dre.ca.gov/Licensees/PRLS.html). `[spec]`
- **Soliciting for prospective tenants or negotiating rentals for compensation is broker activity** under B&P §10131(b) — so a success/placement fee (whoever pays it), or any *paid* tier that includes negotiation, requires operating under a licensed CA broker. Source fetched in spec: [leginfo §10131](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=BPC&sectionNum=10131). `[spec]`
- `[[LEGAL REVIEW REQUIRED]]` — exact PRLS refund/contract mechanics (B&P §§10167.9–10167.10) and the broker-supervision structure are counsel questions, not website questions.

## 3. Model options for a renter-side agent

| Option | Who pays | Pros | Cons / legal implication |
|---|---|---|---|
| **A. Renter freemium subscription** — free search + analysis; paid monthly "agent" tier for outreach/automation | Renter | Incentives perfectly aligned with "renter's advocate" positioning; recurring revenue; monthly subscription (not an advance listing fee, not a per-lease commission) is the cleanest fit with CA rules; churn-friendly (cancel when housed) is acceptable for a high-value, short-duration job-to-be-done | Consumer willingness-to-pay unproven in US (no comps found); if the paid tier *negotiates*, it needs a broker structure — until licensed, paid tier must stay at drafting/organizing with the user approving and sending `[[LEGAL REVIEW REQUIRED]]`; if positioned as prepaid access to listings it could be argued into PRLS — structure the paid tier around *the agent's labor*, not listing access |
| **B. Success/placement fee paid by property** (Texas-locator style) | Landlord/PM | Proven, large per-lease economics (TX standard; Apartment List gets a % of first month's rent); free for renters = easy top-of-funnel | Requires CA DRE broker licensing *first*; recreates the exact conflict of interest the brand attacks (steering risk toward properties that pay); CA has no entrenched locator-fee culture like TX ⚠️ |
| **C. Flat per-successful-lease fee paid by renter** | Renter | Aligned incentives; pay-for-results | Compensation contingent on a lease = broker activity (§10131(b)); harder cash-flow; renter is payment-averse at move-in (deposits, first month) |
| **D. Pure free + landlord advertising** (Zillow/CoStar model) | Landlord | Proven at scale | Identical to incumbents; destroys the positioning; requires listing-side supply Defrost doesn't have |
| **E. Hybrid: A now, B later under a broker of record** | Renter now, property later | Ship revenue pre-license; add high-margin success fees once licensed, *rebated or disclosed* to keep renter trust (TX rebate mechanics show this is possible) | Complexity; must be disclosed prominently to preserve "works for the renter" claim |

## 4. Recommendation

**Option A — renter-paid freemium subscription — as the launch model, with E (adding a disclosed, licensed success-fee channel) as the explicit later path.**

Reasoning tied to the evidence:
1. **Positioning:** Every fetched incumbent (Zillow, CoStar, Zumper, Apartment List) is landlord-paid. "Who pays the platform?" is Defrost.AI's own attack line (it's already the centerpiece of `/company`). Renter-paid is the only model that keeps that page honest.
2. **California-first legality:** A monthly subscription for the agent's work is the path that neither collects an advance *listing* fee (PRLS trigger) nor a lease-contingent *commission* (clean broker trigger) — while the free tier (search + rent-vs-buy analysis + saved listings) stays safely outside both. The paid tier's negotiation features still need the broker-of-record structure the spec already anticipates — counsel must confirm sequencing. `[[LEGAL REVIEW REQUIRED]]`
3. **Evidence gap acknowledged:** No US renter-side AI agent with published pricing was found, so **no dollar price should be printed**. The only benchmark is the spec's ⚠️ EU comp (€15–30/mo). The pricing page therefore ships as "Free tier (live) + Agent tier ({{PRICE_TO_CONFIRM}}/mo, early access)" with a waitlist CTA.

**If the founder disagrees on renter willingness-to-pay,** the runner-up is E's end-state (property-paid success fee under a broker of record, with prominent disclosure and ideally a renter rebate) — but it cannot launch first, because the license has to exist before the fee does.

### What the Pricing page shows (driven by this doc)
- **Free** — profile, rent-vs-buy analysis, live listings, saved searches. Live today.
- **Agent** — written outreach with your authorization, follow-ups, response tracking, negotiation drafts for your approval. **{{PRICE_TO_CONFIRM}}/month — early access, pricing not final.**
- Disclosure block: cancellation/refunds placeholder, no-custody-of-funds statement, "brokerage services provided by [[PLACEHOLDER: broker of record]] once licensed," no savings claims.

## 5. Open items → REVIEW.md
- Confirm launch model (A) and target price point — no benchmark exists; consider willingness-to-pay interviews.
- Counsel: PRLS vs broker path for the paid tier; whether "drafts you approve and send" keeps the unlicensed tier safe.
- Spot-check the founder-memo EU comp (€15–30/mo) before citing it anywhere public.
