# Defrost.AI

Your personal AI real estate agent. Tell it your city, income, and credit score
once — it runs a rent-vs-buy analysis, pulls live listings, and connects buyers
and sellers through agent-to-agent deals. Free to use, no commission.

## What's inside

```
src/defrosted/
  rent_vs_buy_app.py   FastAPI app: auth, profiles, listings, chat, analysis,
                       interests + all marketing-page routes, sitemap/robots,
                       placeholder form intake (/api/forms/*)
  static/
    site.css           Shared design tokens + nav/footer/component styles (edit tokens here)
    site.js            Shared JS: mobile menu, cookie banner, reveal, accordion, forms
    index.html         Landing page
    rent_vs_buy.html   The app (buyer chat + analysis, seller dashboard)
    how-it-works.html  Product walkthrough
    pricing.html       Pricing (Agent price is a placeholder — see REVIEW.md)
    blog.html          Blog index
    blog/*.html        Posts (drafts marked [[SAMPLE POST]])
    careers.html       Careers — edit the ROLES array in-page to list openings
    contact.html       Contact form (placeholder endpoint)
    help.html          Searchable FAQ
    legal/*.html       terms, privacy, cookies, fair-housing, accessibility, security
    founders.html      Founder profiles (/founders?f=phu | ?f=bryan)
    team.html          Team page (/team)
    company.html       About (/company)
    laws.html          State-by-state real estate laws (/laws)
    images/            Founder photos and other static assets
tools/
  build_shared.py      Canonical nav menu + footer live HERE. Edit, then run
                       `python3 tools/build_shared.py` to splice into every page.
docs/WEBSITE_SPEC.md   Site architecture & content spec (with legal citations)
AUDIT.md               UI/UX audit + change log
BUSINESS_MODEL.md      Sourced monetization research + recommendation
REVIEW.md              Everything pending founder confirmation / legal review
CONTENT.md             What copy is real vs. draft vs. placeholder
```

## Run it

```bash
docker compose up -d        # postgres + app on http://localhost:8000
```

Environment (see `docker-compose.yml` / `.env`): `DATABASE_URL`,
`JWT_SECRET_KEY`, `GROQ_API_KEY` (agent chat), `RENTCAST_API_KEY` (live listings),
`SITE_BASE_URL` (public domain used in sitemap.xml/robots.txt — placeholder until
the domain is confirmed).

Backend code changes need a container restart
(`docker restart defrostai-app-1`); static HTML changes are picked up on reload.

## Editing content

- **Nav / footer (all pages):** edit `MENU_HTML` / `FOOTER_HTML` in
  `tools/build_shared.py`, then run it. Don't edit the generated blocks in pages —
  they're overwritten between the `SITE:MENU`/`SITE:FOOTER` markers.
- **Design tokens (colors, type):** `:root` variables at the top of `static/site.css`.
  Legacy pages (index/company/team/founders/laws) still carry their own inline
  copies of the tokens.
- **Blog:** copy an existing file in `static/blog/`, add the slug to `BLOG_SLUGS`
  in `rent_vs_buy_app.py`, and add a card in `static/blog.html`.
- **Careers roles:** the `ROLES` array inside `static/careers.html`.
- **Legal pages:** `static/legal/*.html` — every page is a flagged draft; see REVIEW.md.
- **Forms:** contact/careers forms POST to `/api/forms/{name}`, which validates and
  logs only. Swap `data-endpoint` (or the handler) for a real service before launch.
- **Analytics:** none wired. Gate any future script on `window.defrostCookiePrefs()`
  (set by the cookie banner in `site.js`).
