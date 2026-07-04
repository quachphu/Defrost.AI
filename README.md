# Defrost.AI

Your personal AI real estate agent. Tell it your city, income, and credit score
once — it runs a rent-vs-buy analysis, pulls live listings, and connects buyers
and sellers through agent-to-agent deals. Free to use, no commission.

## What's inside

```
src/defrosted/
  rent_vs_buy_app.py   FastAPI app: auth, profiles, listings, chat, analysis, interests
  static/
    index.html         Landing page
    rent_vs_buy.html   The app (buyer chat + analysis, seller dashboard)
    founders.html      Founder profiles (/founders?f=phu | ?f=bryan)
    team.html          Team page (/team)
    laws.html          State-by-state real estate laws (/laws)
    images/            Founder photos and other static assets
```

## Run it

```bash
docker compose up -d        # postgres + app on http://localhost:8000
```

Environment (see `docker-compose.yml` / `.env`): `DATABASE_URL`,
`JWT_SECRET_KEY`, `GROQ_API_KEY` (agent chat), `RENTCAST_API_KEY` (live listings).

Backend code changes need a container restart
(`docker restart defrostai-app-1`); static HTML changes are picked up on reload.
