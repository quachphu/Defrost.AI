# Defrost.AI — Website Architecture & Content Specification

**Prepared:** July 2026 · **For:** designer/developer handoff · **Scope:** public marketing site + trust/legal surface
**Method note:** Facts below were verified by live fetch/search where marked with a citation. Items that could not be verified in-session are flagged `⚠️`. Claims sourced from the founder's own research memo (July 2026) are marked `[founder memo]` — spot-check before print.

---

## ⚠️ TWO CONFLICTS RESOLVED UP FRONT (founder decisions already made or required)

1. **No calling — anywhere.** The spec brief described outreach "across email, phone, SMS." The founder's standing directive is **no phone/voice outreach, ever** — and this is also the low-risk path: the FCC's Feb 8, 2024 Declaratory Ruling (FCC 24-17) holds AI-generated voices are "artificial" under the TCPA, requiring prior express consent ([FCC](https://www.fcc.gov/document/fcc-confirms-tcpa-applies-ai-technologies-generate-human-voices), [ruling PDF](https://docs.fcc.gov/public/attachments/FCC-24-17A1.pdf)). **This spec assumes written-channel outreach only (listing reply forms + CAN-SPAM-compliant email).** Every page must be consistent with that. SMS is also excluded per founder directive (TCPA texting rules would apply if ever added).
2. **Brand name.** The brief says "Defrosted.ai"; the live product says "Defrost.AI"; the LinkedIn handle is `defrostedai`. `⚠️ FOUNDER MUST CONFIRM` one canonical name + domain before publishing legal pages (ToS/Privacy must name the legal entity exactly).

**Verified positioning wedge:** EliseAI (the best-funded rentals AI) sells to *property managers, owners, and operators* — its platform (EliseCRM, VoiceAI, LeasingAI, ResidentAI) automates the landlord side (verified by fetch of eliseai.com, July 2026). The renter-side agent lane is open. "The renter-side equivalent of EliseAI" is a defensible framing.

---

## A. Sitemap

```
/                       Homepage (exists — landing)
/how-it-works           Product walkthrough (partially exists as /#how — build out)
/pricing                Pricing + CA fee disclosures (TO BUILD)
/company                About / mission / compliance (exists)
/team                   Team (exists)
/founders?f=…           Founder profiles (exists)
/laws                   State-by-state renter/buyer law explainer (exists — SEO asset)
/blog                   Blog index + posts (TO BUILD; can start as 3 launch posts)
/careers                Careers (TO BUILD; minimal)
/contact                Contact / support (TO BUILD; can be a section on /company at first)
/legal/terms            Terms of Service (TO BUILD)
/legal/privacy          Privacy Policy + CCPA/CPRA (TO BUILD)
/legal/fair-housing     Fair Housing commitment (TO BUILD — REQUIRED, see §6.1)
/legal/cookies          Cookie Policy (TO BUILD)
/legal/accessibility    Accessibility statement (TO BUILD)
/legal/licenses         Licensing & broker-of-record disclosure (TO BUILD when DRE license lands)
/app                    The product (exists — behind auth)
```

Priority order to build: `pricing → legal/terms → legal/privacy → legal/fair-housing → legal/accessibility → legal/cookies → how-it-works → blog → careers → contact → legal/licenses`.

## B. Top navigation

Keep the current pattern (it matches YC-style minimalism): logo left, two dropdowns, one high-contrast CTA right. Target ≤ 6 items.

| Item | Contents | Notes |
|---|---|---|
| **Product** (rename from "Resources" split) | How it works, Pricing, State laws, For renters, For landlords | Pricing must be in the nav — renters expect fee transparency before signup |
| **Company** | About us, Team, Our Founders, Careers, Contact, Blog | exists; add Blog when live |
| **Log in** (ghost) | /app | existing |
| **Get started** (solid black CTA) | signup modal | existing; at pre-launch this can toggle to "Join waitlist" |

Design opinion: don't split "For renters / For landlords" into top-level nav until both funnels have real content; a single Product dropdown is cleaner at this stage.

## C. Footer (trust lives here)

4 columns + bottom bar. Current footer already has Product/Company/Resources + EHO mark; extend to:

- **Product:** How it works · Pricing · State laws · Live listings · Security
- **Company:** About us · Team · Our Founders · Careers · Contact · Blog
- **Resources:** Renter guides (blog tags) · State laws · Press · Help/FAQ
- **Legal:** Terms of Service · Privacy Policy · Cookie Policy · Accessibility · **Fair Housing** · **Do Not Sell or Share My Personal Information** (CCPA/CPRA link) · Licenses
- **Bottom bar:** © year + legal entity name + **physical mailing address** (⚠️ founder must supply) · **Equal Housing Opportunity logo** (already present) · socials · when licensed: "Defrost.AI operates under [Brokerage], CA DRE #____" — the DRE-number footer line is the industry convention (⚠️ Zillow's live footer could not be fetched — zillow.com returns 403 to bots; founder should visually confirm Zillow's pattern: EHO logo, fair-housing links, "Do Not Sell" link, accessibility link).

## D. Page-by-page content spec

### 1. Homepage (exists — adjust)
Slogan hero ("Let your agent find your home") — keep. Ordered blocks: Hero → roadmap photo → How it works (buyer/seller tracks) → Legal protections + "Browse laws by state" → Founders → CTA band → footer.
**Additions:** (a) a one-line trust strip under the hero: "Fair-housing-first · Written, consent-based outreach · You approve everything"; (b) pricing teaser band once /pricing exists; (c) coverage honesty line: "Live in California first — expanding state by state." Never claim dollar-savings figures (FTC/CA UDAP exposure — best practice, not statute-cited).

### 2. How it works (/how-it-works)
Sections: (1) hero: "One conversation. Then your agent works." (2) The pipeline, six steps: Profile → Analysis (rent-vs-buy) → Discovery (live listings) → Written outreach (email/listing forms; agent identifies itself as AI — CA SB 1001 bot-disclosure `[founder memo]`) → Negotiation (drafts for your approval; brokerage-supervised once licensed) → Lease prep. (3) **The consent moment** — a dedicated block showing the authorization screen: user explicitly authorizes the agent to contact landlords in writing on their behalf; this is both UX and the legal consent capture (CAN-SPAM sender obligations `[founder memo]`). (4) What the agent will never do: call anyone, commit you to anything, or misstate terms — with the "we stand behind our agent" promise (Moffatt v. Air Canada, 2024 BCCRT 149 `[founder memo]` — company is liable for its bot's representations). (5) FAQ accordion. CTA: Get started.

### 3. Pricing (/pricing) — legal constraints shape this page
Verified constraint set:
- Charging renters an **advance fee for listings** triggers California's **PRLS regime**: listings-supply only — "negotiation of the rental of property is not a part of this activity"; $10,000 bond (or cash deposit) per location; DRE-approved client contract required (verified by fetch of [dre.ca.gov PRLS page](https://www.dre.ca.gov/Licensees/PRLS.html), July 2026). 90-day contract cap and refund rights `[founder memo — B&P §§10167.9–10167.10]` ⚠️ verify exact refund text with counsel.
- **Negotiating leases or soliciting for prospective tenants for compensation = broker activity** under B&P §10131(b): "…solicits for prospective tenants, or negotiates…" (verified by fetch of [leginfo §10131](https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=BPC&sectionNum=10131), July 2026). So a success/placement fee, or any paid tier that includes negotiation, requires operating under a licensed CA broker.
**Page structure:** (1) Free tier — search + analysis + saved listings (unlicensed-safe). (2) Agent tier `⚠️ CONFIRM MODEL` — subscription while the agent works (EU renter-agent comps charge €15–30/mo `[founder memo]`). (3) Disclosure block (small print, on-page, not buried): fee terms, cancellation/refund policy, "brokerage services provided by [broker of record]" once licensed, and no-custody-of-funds statement. (4) FAQ: refunds, cancellation, what's included. No "save $X" claims anywhere.

### 4. Company/About (exists) — keep; add physical address + press contact when available.

### 5. Blog (/blog)
Purpose: SEO + trust. Launch with three posts: "How to negotiate rent (and what your AI agent does differently)", "California renter rights in 2026, in plain English" (links to /laws), "Why every rental platform works for landlords — and what we're doing about it." Structure: index (cards) + post template (title, date, author with photo, TOC). The /laws page already functions as the SEO cornerstone — interlink heavily.

### 6. Careers (/careers)
Minimal: mission line, values (reuse company principles), open-roles list (LinkedIn links fine), and an **applicant-privacy notice** paragraph (CCPA applies to applicant data — best practice; ⚠️ counsel review).

### 7. Contact (/contact or /company#contact)
Support email (custom domain), response-time expectation, business address ⚠️, press contact, link to help FAQ.

### 8. Legal/trust pages
- **Terms of Service:** agent scope + explicit "agent representations require your approval; the service will never bind you without confirmation" clause (Air Canada lesson `[founder memo]`); arbitration; liability limits. ⚠️ counsel-drafted.
- **Privacy Policy:** CCPA/CPRA rights, categories collected, no-sale statement or Do-Not-Sell mechanism, data-deletion flow. ⚠️ counsel-drafted.
- **Fair Housing (/legal/fair-housing):** REQUIRED given HUD's May 2, 2024 twin guidance applying the FHA to AI in tenant screening and housing advertising — providers are responsible regardless of the technology used, and screening should use only tenancy-relevant criteria ([HUD PR 24-098](https://archives.hud.gov/news/2024/pr24-098.cfm); [analysis](https://www.consumerfinancialserviceslawmonitor.com/2024/05/hud-issues-guidance-on-applicability-of-the-fair-housing-act-to-tenant-screening-and-housing-related-advertising-that-relies-upon-algorithms-and-ai/)). Content: protected classes; how matching avoids proxies/steering; logging + audits; complaint contact. EHO logo on-page.
- **Cookies / Accessibility:** consent banner + policy; WCAG 2.1 AA commitment statement (Zillow publishes one ⚠️ unverified this session — 403).
- **Licenses:** publish DRE number + broker of record when obtained; until then the /company wording ("built to operate under a licensed CA DRE broker structure") is the honest ceiling — do not print a license line before it exists.

## E. Trust & credibility inventory (where each lives)
Legal footer block (all pages) · EHO logo (footer, all pages — done; also fair-housing page) · physical address (footer bottom bar ⚠️) · real founder identities w/ photos + LinkedIn (done) · consistent brand system (done — monochrome editorial) · custom-domain email (⚠️ set up) · HTTPS + security page (roadmap: SOC 2 mention only when true) · press/investor logos (only when real) · coverage honesty ("California first") · bot-disclosure statement (how-it-works + ToS) · named metrics only when real (never fabricate counts).

## F. Design & aesthetic direction (opinion, anchored to current build)
Keep the existing monochrome editorial system — it already matches the Linear/Ramp/YC register: Inter + Inter Tight, #0A0A0A on #FFFFFF/#F5F5F3, 1px #E5E5E2 borders, 4–8px radii, uppercase 10–11px letter-spaced labels, black rectangular CTAs, grayscale photography. Motion: reveal-on-scroll, count-ups, and the map/list interactions — restrained, no parallax. Voice: plain, declarative, slightly dry ("A housing company has to earn trust the boring way."). One primary CTA per view.

## G. Component inventory (all exist unless marked)
Navbar w/ dropdowns · footer (4-col + bottom bar) · hero (slogan + rotating word) · photo roadmap · step tracks · stat tiles w/ count-up · comparison toggle · accordion · timeline · founder cards + profile template · team grid · state-law explorer · CTA band (light/dark) · auth modals · listing card/grid · map view (pins, preview popup, list sync) · **TO BUILD:** pricing table, FAQ accordion (reuse accordion), blog index/post templates, cookie-consent banner, legal-page text template.

---

## Founder must confirm / verify with counsel
1. Canonical brand name + domain (Defrost.AI vs Defrosted.ai) and legal entity name.
2. Business model: subscription vs success fee — determines PRLS vs full-broker path (§D.3). Counsel: exact PRLS refund/contract rules (B&P §§10167.9–10167.10) and broker-supervision structure for AI-drafted negotiation.
3. Physical mailing address + custom-domain email (CAN-SPAM requires a postal address in outreach mail `[founder memo]`).
4. ToS + Privacy + Fair Housing + Accessibility pages — counsel-drafted before public launch.
5. Zillow-pattern footer details (EHO/Do-Not-Sell/accessibility placement) — visually confirm on zillow.com (bot-blocked in this session).
6. Screening-fee cap current CPI figure if fees are ever surfaced (Civil Code §1950.6 / AB 2493 `[founder memo]`).
7. TCPA/FCC status is in flux (2024 NPRM; consent-revocation rule litigation `[founder memo]`) — re-verify before any future channel expansion. Current written-only stance avoids this entirely.
