# REVIEW.md — Everything that needs your confirmation

Running checklist of placeholders, assumptions, and items needing founder decision or attorney review. Grouped by scope, then page. **Nothing marked `[[…]]` or `{{…}}` on the site is final.**

## 0. Big decisions / deviations

1. **Tech stack — deviated from the brief's Next.js default, deliberately.** The existing site is FastAPI + self-contained static HTML with a working design system, live auth modals, and Docker deployment. Rebuilding in Next.js would violate the brief's own rule #5 ("improve, don't rebuild") and discard working code. I extended the existing architecture instead: shared `site.css`/`site.js` tokens + components, canonical nav/footer spliced by `tools/build_shared.py`. If you want the Next.js migration anyway, say so — it's a separate project.
2. **Brand name kept as "Defrost.AI"** (brief says "Defrosted.ai"; the live site, README, and LinkedIn handle disagree with each other). Per `docs/WEBSITE_SPEC.md` conflict #2, one canonical name + domain must be confirmed before legal pages are final. All new copy uses the site's existing "Defrost.AI."
3. **Positioning kept broader than "renter-only."** The brief frames the product as renter-side rental agent; the existing product and homepage also serve buyers/sellers (rent-vs-buy analysis, seller dashboard). Per `docs/WEBSITE_SPEC.md` §D.1 ("hero — keep"), I kept the existing hero and buyer/seller tracks, and pushed the renter-advocate framing in the new pages, footer, and pricing. Confirm if you want the homepage narrowed to renters-only.
4. **Business model:** recommended renter-paid freemium subscription (see `BUSINESS_MODEL.md`). **Confirm the model and a price point** — the pricing page ships with `{{PRICE_TO_CONFIRM}}` until then.
5. **CTA framing:** homepage keeps "Sign up free" (product is live); the paid tier uses waitlist framing ("Join the early-access waitlist"). Confirm this hybrid is what you want vs. full waitlist framing.

## 1. Legal / attorney review (blocking before public launch)

- [ ] **Terms of Service** (`/legal/terms`) — entire page is scaffold; counsel must draft. Has `noindex` until approved.
- [ ] **Privacy Policy** (`/legal/privacy`) — CCPA/CPRA sections especially; confirm the "we do not sell or share" position survives any analytics tooling. `noindex` until approved.
- [ ] **Cookie Policy** (`/legal/cookies`) + banner copy in `site.js` — confirm categories and wording. `noindex` until approved.
- [ ] **Fair Housing Statement** (`/legal/fair-housing`) — wording pending review; sources cited in-page (HUD PR 24-098, May 2024 AI guidance).
- [ ] **EHO logo** — footer + fair-housing page use an *approximate SVG placeholder*. Obtain and drop in the official HUD Equal Housing Opportunity logo asset and confirm usage/wording rules.
- [ ] **AI-agent disclosure** (footer, all pages; how-it-works consent block) — final wording; sources: CA B&P 17941 (SB 1001) bot disclosure, CAN-SPAM sender obligations.
- [ ] **Licensing line** (footer, pricing, help) — "not a licensed real estate broker and does not negotiate rentals for compensation." Counsel must confirm this scope line and the unlicensed-safe boundary of the paid tier (B&P §10131(b); PRLS B&P §10167 if any advance fee could be construed as listing access).
- [ ] **Refund/cancellation policy** (pricing + terms) — placeholder; counsel to confirm whether PRLS-style refund rights apply.
- [ ] **EEO statement + applicant-privacy notice** (`/careers`) — placeholder wording.
- [ ] Homepage **"Legal protections" cards** (pre-existing content, untouched): they state statutory specifics (21-day deposit return, grace periods, contingency windows) as if product guarantees. Counsel should reframe as "what the law provides (California)" or verify each claim.
- [ ] `/laws` page content (pre-existing, untouched) — same class of risk; verify currency of legal claims.
- [ ] `/company` market figures (pre-existing) — the page cites its sources in small print (Matrix, Census, Harvard JCHS, Apartment List); re-verify they're current before fundraising use.

## 2. Founder must supply (placeholders on the site)

- [ ] Legal entity name (© line, terms) — currently "© 2026 Defrost.AI" with no entity.
- [ ] Mailing address (contact page card + should be added to footer bottom bar; CAN-SPAM requires a postal address in outreach email).
- [ ] Custom-domain emails: support@, press@, privacy@, legal@, security@, accessibility@, fairhousing@ (referenced as placeholders on contact/legal pages).
- [ ] `SITE_BASE_URL` env var — canonical domain for sitemap.xml/robots.txt absolute URLs (currently defaults to localhost).
- [ ] Agent-plan price (`{{PRICE_TO_CONFIRM}}` on /pricing) — see BUSINESS_MODEL.md; no US benchmark exists, spec's EU comp (€15–30/mo) is founder-memo, unverified.
- [ ] Careers: real perks/benefits list (comment placeholder in careers.html); roles go in the `ROLES` array.
- [ ] Blog: the three launch posts are drafts marked `[[SAMPLE POST — review before launch]]`. The CA-renter-rights post has inline `[[verify]]` flags on every statutory specific — verify or strip before publishing.
- [ ] Social accounts: footer links LinkedIn only (the old X/Facebook/YouTube icons all pointed to LinkedIn and were removed). Add real accounts when they exist.
- [ ] Hero/roadmap image is hot-linked from Unsplash (pre-existing) — replace with an owned/licensed asset before launch.

## 3. Wiring to real services (currently placeholder endpoints)

- [ ] `/api/forms/contact` and `/api/forms/careers` validate and **log only** (server console). Point `data-endpoint` in contact.html/careers.html (or the backend handler) at a real destination (email service / ATS).
- [ ] Analytics: none wired, by design. The cookie banner already gates future analytics via `window.defrostCookiePrefs()` — load any tool only when `analytics: true`.
- [ ] "Join the early-access waitlist" buttons currently route to the signup modal on `/`. Confirm whether you want a dedicated waitlist capture instead.

## 4. Known gaps / follow-ups (non-blocking)

- [ ] Legacy pages (`/company`, `/team`, `/founders`, `/laws`, `/app`) still have pre-existing accessibility gaps (contrast of `#9C9C9C` micro-labels, no reduced-motion in their inline CSS). New pages + shared css handle this; a dedicated a11y pass on legacy inline styles is pending.
- [ ] Old footer CSS rules in the five legacy pages are now unused (footer markup was replaced with `ft-*` classes) — harmless dead rules; strip in a cleanup pass.
- [ ] `/legal/licenses` page intentionally **not built** — per docs/WEBSITE_SPEC.md, don't publish a license page before a license exists.
- [ ] Organization JSON-LD schema not yet added (needs confirmed entity name/domain first — add after #2 items land).
- [ ] Announcement-bar component exists in `site.css` (`.announce-bar`) but is not enabled anywhere; add the element to a page if wanted.
