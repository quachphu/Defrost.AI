# AUDIT.md — Existing site audit & change log

**Audited:** July 2026. Scope: the public marketing surface served by `src/defrosted/rent_vs_buy_app.py` from `src/defrosted/static/`.

## 1. What exists

| Route | File | State |
|---|---|---|
| `/` | `index.html` | Landing: nav w/ dropdowns, hero, photo roadmap, buyer/seller how-it-works tracks, "legal protections" cards, founders section, dark CTA band, footer w/ EHO line, auth modals (signup/login wired to real `/auth/*` endpoints) |
| `/company` | `company.html` | Strong about page: mission, market framing, "who pays the platform?" section, principles, timeline, founders |
| `/team` | `team.html` | Team grid |
| `/founders?f=…` | `founders.html` | Founder profile template (Phu Quach, Bryan Tineo — real people, real photos) |
| `/laws` | `laws.html` | State-by-state law explorer — genuine SEO asset |
| `/app` | `rent_vs_buy.html` | The product (behind auth) — out of scope for this pass |

**Design system (keep):** monochrome editorial — Inter + Inter Tight, `#0A0A0A` on `#FFFFFF`/`#F5F5F3`, 1px `#E5E5E2` borders, 4–8px radii, uppercase letter-spaced micro-labels, black rectangular CTAs, grayscale photography, scroll-reveal motion. Tokens exist as CSS variables in each page's inline `<style>`. This already hits the YC/Linear register the brief asks for.

**Architecture:** FastAPI + self-contained static HTML pages (inline CSS/JS per page). Not Next.js — see REVIEW.md #1 for why we deviate from the brief's default stack rather than rebuild.

## 2. Strengths (preserved)
- Coherent, restrained brand system across all pages; real founders with photos and stories (rare, credible trust signal).
- `/laws` is a real content moat; `/company` already articulates the "who pays?" positioning honestly.
- Working auth modals with validation and error states; EHO mark already present in the footer.
- Scroll-reveal via IntersectionObserver, no heavy animation.

## 3. Weaknesses found (and what was done)

| # | Issue | Severity | Action |
|---|---|---|---|
| W1 | ~15 nav/footer links point to the company LinkedIn page as a stand-in (Pricing, Careers, Contact, Blog, Press, Privacy, Terms, "Live listings") — reads as a demo, kills credibility | High | Replaced with real pages (this build) |
| W2 | No pricing, how-it-works, blog, careers, contact, help, or any legal page (terms/privacy/cookies/fair-housing/accessibility/security) | High | Built all of them |
| W3 | Nav menu simply disappears below 960px — no mobile menu at all | High | `site.js` builds an accessible hamburger drawer from the existing nav markup on every page |
| W4 | No per-page meta descriptions, no OG/Twitter cards, no sitemap.xml/robots.txt | Med | Added on all pages + `/sitemap.xml`, `/robots.txt` routes |
| W5 | No skip-to-content link; no `prefers-reduced-motion` handling; dropdowns hover-only (keyboard `focus-within` works, but no touch affordance); `#9C9C9C` micro-labels are below AA contrast for text | Med | Skip link + reduced-motion + focus-visible styles in `site.css` (new pages) and injected banner styles; contrast of body-size muted text bumped where I touched pages; full sweep of legacy inline styles left for a dedicated pass (flagged) |
| W6 | "Legal protections" homepage cards state statutory specifics (21-day deposit return, 5-day grace, etc.) as if they were product guarantees | Med | Left content untouched (surgical rule) but flagged for counsel in REVIEW.md — reframe as "what the law provides in California" |
| W7 | Hero/roadmap image hotlinked from Unsplash (external dependency, unpinned) | Low | Kept (works today), flagged as placeholder imagery in REVIEW.md |
| W8 | Footer social icons (X, Facebook, YouTube) all link to LinkedIn — implies accounts that don't exist | Med | Reduced to LinkedIn only; other slots removed until real accounts exist |
| W9 | No cookie consent, no CCPA "Do Not Sell or Share" link, no AI-agent disclosure, no compliance line | High | Cookie banner (category toggles, localStorage), Legal footer column, Do-Not-Sell link, AI-disclosure + placeholder compliance line on every page |
| W10 | `/company` market stats rely on a small-print source line (Matrix, Census, Harvard JCHS, Apartment List) | Low | Content untouched; flagged in REVIEW.md to re-verify figures stay current |
| W11 | No 404 handling for unknown legal/blog slugs | Low | Routes return 404 correctly via FastAPI defaults |

## 4. Gaps vs. target structure → what was added

New shared assets (single source of truth for new pages, additive for old ones):
- `static/site.css` — design tokens + shared nav/footer/buttons/sections/forms/accordion/cookie-banner/a11y styles.
- `static/site.js` — mobile menu (built from existing nav markup), cookie banner injection, scroll reveal, accordion, footer-year.

New pages (all self-consistent with the existing brand system):
- `/how-it-works` — six-step pipeline, the consent moment, "what the agent will never do," FAQ teaser.
- `/pricing` — Free + Agent tiers per `BUSINESS_MODEL.md`; `{{PRICE_TO_CONFIRM}}` placeholder, disclosure block, pricing FAQ.
- `/blog` + three launch posts (marked `[[SAMPLE POST — review before launch]]`).
- `/careers` — values, roles from an easy-to-edit config array, application instructions, EEO + applicant-privacy placeholders.
- `/contact` — support/press slots, validated form wired to a placeholder endpoint.
- `/help` — searchable FAQ.
- `/legal/terms`, `/legal/privacy`, `/legal/cookies`, `/legal/fair-housing`, `/legal/accessibility`, `/legal/security` — structured shells, placeholder copy, every section flagged `[[LEGAL REVIEW REQUIRED]]` with source comments.

Existing pages upgraded surgically:
- All five pages: nav dropdowns and footer rebuilt to the new IA (Product / Company / Resources / Legal + compliance bottom bar); everything else untouched.
- Homepage additions per `docs/WEBSITE_SPEC.md` §D.1: trust strip under hero, pricing teaser band, "California first" coverage line, FAQ teaser.

## 5. Wholesale-redesign justification
None needed. The existing design system is the target aesthetic; every change above is additive or link-level. No page was thrown away.
