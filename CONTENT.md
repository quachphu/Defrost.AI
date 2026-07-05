# CONTENT.md — What's real, what I wrote, what's placeholder

Inventory of copy on the marketing site so you know exactly what to trust.

## Legend
- **Pre-existing** — was on the site before this pass; untouched unless noted.
- **Written (factual)** — new copy I wrote describing the product/commitments; truthful to the product design in `docs/WEBSITE_SPEC.md`, but *you* must confirm it matches reality before launch.
- **Written (sourced)** — new copy backed by a fetched citation (see BUSINESS_MODEL.md / in-page source comments).
- **Placeholder** — visibly flagged `[[…]]` / `{{…}}`; not real content.

## By page

| Page | Status of copy |
|---|---|
| `/` hero, roadmap, buyer/seller tracks, legal-protection cards, founders | Pre-existing (eyebrow now says "Starting in California") |
| `/` trust strip, pricing teaser, FAQ teaser | Written (factual) |
| `/how-it-works` all sections | Written (factual) — pipeline & consent flow match the product spec ("written-only, user approves"); the authorization-screen box is labeled a sample |
| `/pricing` tiers, who-pays, FAQ | Written (factual + sourced for the "listing sites are landlord-paid" claim — sources in BUSINESS_MODEL.md); **price itself is `{{PRICE_TO_CONFIRM}}` placeholder**; fine-print block is placeholder pending counsel |
| `/blog` index + 3 posts | Written drafts, each banner-flagged `[[SAMPLE POST — review before launch]]`. Negotiate-rent post: general advice, no invented stats. CA-renter-rights post: every statutory specific carries an inline `[[verify]]` flag. Who-pays post: claims sourced in BUSINESS_MODEL.md |
| `/careers` values | Written (factual, derived from /company principles); perks intentionally absent (comment placeholder); **zero fake roles** — empty `ROLES` array shows an honest "no open roles" state; EEO + applicant-privacy = flagged placeholders |
| `/contact` | Written (factual); all emails + mailing address = flagged placeholders |
| `/help` FAQ (17 Q&As) | Written (factual) — availability, pricing, consent, fair-housing answers are non-committal where facts aren't final |
| `/legal/terms`, `/legal/privacy`, `/legal/cookies` | Structural scaffolds, banner-flagged drafts, `noindex`, every substantive clause placeholder-flagged. Original text; nothing copied from another company |
| `/legal/fair-housing` | Written (sourced: FHA, HUD PR 24-098) — flagged for attorney review; EHO mark is a placeholder SVG |
| `/legal/accessibility` | Written (factual — describes what was actually implemented; admits legacy gaps) |
| `/legal/security` | Written (factual — describes actual practices: HTTPS, hashed passwords, no funds custody; explicitly claims **no** certifications) |
| Footer (all pages) | Written; compliance lines flagged for legal review in comments; entity/address placeholders in comments |
| `/company`, `/team`, `/founders`, `/laws` | Pre-existing content untouched (nav/footer replaced only). Note: founders/team are real people with real photos |

## Things I deliberately did NOT create
- No testimonials, customer logos, press mentions, star ratings, or "X apartments found" counters.
- No prices, fee percentages, or savings claims.
- No license numbers, certifications (SOC 2 etc.), or claims of licensure.
- No fake team members, advisors, job openings, or social accounts (footer now links only the real LinkedIn).
- No invented statistics anywhere — the only market figure on the site ("$1.85T" on /company) is pre-existing and flagged in REVIEW.md.
