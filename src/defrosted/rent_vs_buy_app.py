"""
Defrost.AI — Rent vs Buy + AI Real Estate Agent
Run with: uvicorn defrosted.rent_vs_buy_app:app --reload --port 8000
Needs in .env: GROQ_API_KEY, RENTCAST_API_KEY, DATABASE_URL, JWT_SECRET_KEY
Docker:        docker compose up -d postgres
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import pathlib
import uuid
from datetime import datetime, timedelta, timezone

import asyncpg
import httpx
from ddgs import DDGS
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from groq import AsyncGroq
from jose import JWTError, jwt
from pydantic import BaseModel, Field

# ── Load .env ─────────────────────────────────────────────────────────────────

_env_file = pathlib.Path(__file__).parent.parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

app = FastAPI(title="Defrost.AI")
STATIC_DIR = pathlib.Path(__file__).parent / "static"
RENTCAST_BASE = "https://api.rentcast.io/v1"

US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT",
    "VA","WA","WV","WI","WY","DC",
}

_STATE_NAMES: dict[str, str] = {
    "alabama":"AL","alaska":"AK","arizona":"AZ","arkansas":"AR","california":"CA",
    "colorado":"CO","connecticut":"CT","delaware":"DE","florida":"FL","georgia":"GA",
    "hawaii":"HI","idaho":"ID","illinois":"IL","indiana":"IN","iowa":"IA",
    "kansas":"KS","kentucky":"KY","louisiana":"LA","maine":"ME","maryland":"MD",
    "massachusetts":"MA","michigan":"MI","minnesota":"MN","mississippi":"MS","missouri":"MO",
    "montana":"MT","nebraska":"NE","nevada":"NV","new hampshire":"NH","new jersey":"NJ",
    "new mexico":"NM","new york":"NY","north carolina":"NC","north dakota":"ND",
    "ohio":"OH","oklahoma":"OK","oregon":"OR","pennsylvania":"PA","rhode island":"RI",
    "south carolina":"SC","south dakota":"SD","tennessee":"TN","texas":"TX","utah":"UT",
    "vermont":"VT","virginia":"VA","washington":"WA","west virginia":"WV",
    "wisconsin":"WI","wyoming":"WY","district of columbia":"DC",
}

# ── Password helpers ───────────────────────────────────────────────────────────

def _hash_pw(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return base64.b64encode(salt + key).decode()

def _verify_pw(password: str, stored: str) -> bool:
    try:
        data = base64.b64decode(stored.encode())
        salt, stored_key = data[:32], data[32:]
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return hmac.compare_digest(key, stored_key)
    except Exception:
        return False

# ── JWT helpers ────────────────────────────────────────────────────────────────

_JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "dev-insecure-change-me")
_JWT_ALGO = "HS256"

def _make_token(user_id: str) -> str:
    return jwt.encode(
        {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7)},
        _JWT_SECRET, algorithm=_JWT_ALGO,
    )

async def _auth(authorization: str | None = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(authorization.split()[1], _JWT_SECRET, algorithms=[_JWT_ALGO])
        return payload["sub"]
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

# ── Database pool ──────────────────────────────────────────────────────────────

_pool: asyncpg.Pool | None = None

async def _db() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        url = os.environ.get(
            "DATABASE_URL", "postgresql://defrosted:defrosted@localhost:5432/defrosted"
        )
        try:
            _pool = await asyncpg.create_pool(url)
        except Exception:
            raise HTTPException(503, "Database unavailable. Run: docker compose up -d postgres")
        await _init_schema(_pool)
    return _pool

async def _init_schema(pool: asyncpg.Pool) -> None:
    await pool.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'buyer',
            age INTEGER,
            city TEXT,
            annual_income INTEGER,
            credit_score INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    await pool.execute("""
        CREATE TABLE IF NOT EXISTS property_listings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
            listing_type TEXT NOT NULL,
            title TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            price INTEGER NOT NULL,
            bedrooms INTEGER,
            bathrooms FLOAT,
            sqft INTEGER,
            description TEXT,
            agent_rules TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    await pool.execute("""
        CREATE TABLE IF NOT EXISTS interests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            listing_id UUID REFERENCES property_listings(id) ON DELETE CASCADE,
            buyer_id UUID REFERENCES users(id) ON DELETE CASCADE,
            status TEXT DEFAULT 'pending',
            buyer_message TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(listing_id, buyer_id)
        )
    """)
    # Add caching columns if they don't exist yet (safe on existing DBs)
    await pool.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS cached_listings JSONB DEFAULT '[]'::jsonb")
    await pool.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_analysis  JSONB DEFAULT '{}'::jsonb")

@app.on_event("startup")
async def _startup() -> None:
    try:
        await _db()
    except HTTPException:
        print("⚠  Database not available — auth features disabled. Run: docker compose up -d postgres")

# ── Pydantic models ────────────────────────────────────────────────────────────

class SignupReq(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    role: str = "buyer"

class LoginReq(BaseModel):
    email: str
    password: str

class ProfileUpdate(BaseModel):
    age: int | None = None
    city: str | None = None
    annual_income: int | None = None
    credit_score: int | None = None
    cached_listings: list | None = None
    last_analysis: dict | None = None

class ListingCreate(BaseModel):
    listing_type: str
    title: str
    address: str
    city: str
    price: int = Field(..., gt=0)
    bedrooms: int | None = None
    bathrooms: float | None = None
    sqft: int | None = None
    description: str | None = None
    agent_rules: str | None = None

class ChatReq(BaseModel):
    message: str
    history: list[dict] = []

class AnalysisRequest(BaseModel):
    age: int = Field(..., ge=18, le=90)
    city: str = Field(..., min_length=2)
    annual_income: int = Field(..., ge=1000)
    credit_score: int = Field(..., ge=300, le=850)

# ── Auth endpoints ─────────────────────────────────────────────────────────────

_JSON_COLS = {"cached_listings", "last_analysis"}

def _row_to_user(row: asyncpg.Record) -> dict:
    out = {}
    for k, v in dict(row).items():
        if k == "password_hash" or isinstance(v, datetime):
            continue
        if isinstance(v, uuid.UUID):
            out[k] = str(v)
        elif k in _JSON_COLS:
            # asyncpg may return JSONB as str or already-parsed object
            out[k] = json.loads(v) if isinstance(v, str) else (v or ([] if k == "cached_listings" else {}))
        else:
            out[k] = v
    return out

@app.post("/auth/signup")
async def signup(req: SignupReq) -> dict:
    if req.role not in ("buyer", "seller"):
        raise HTTPException(400, "role must be 'buyer' or 'seller'")
    pool = await _db()
    try:
        row = await pool.fetchrow(
            "INSERT INTO users (email, password_hash, full_name, role) "
            "VALUES ($1,$2,$3,$4) RETURNING id, email, full_name, role",
            req.email.lower().strip(), _hash_pw(req.password),
            req.full_name.strip(), req.role,
        )
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Email already registered")
    return {"token": _make_token(str(row["id"])), "user": _row_to_user(row)}

@app.post("/auth/login")
async def login(req: LoginReq) -> dict:
    pool = await _db()
    row = await pool.fetchrow("SELECT * FROM users WHERE email=$1", req.email.lower().strip())
    if not row or not _verify_pw(req.password, row["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    return {"token": _make_token(str(row["id"])), "user": _row_to_user(row)}

@app.get("/auth/me")
async def me(uid: str = Depends(_auth)) -> dict:
    pool = await _db()
    row = await pool.fetchrow(
        "SELECT id,email,full_name,role,age,city,annual_income,credit_score,"
        "cached_listings,last_analysis FROM users WHERE id=$1",
        uuid.UUID(uid),
    )
    if not row:
        raise HTTPException(404, "User not found")
    return _row_to_user(row)

@app.patch("/auth/profile")
async def update_profile(req: ProfileUpdate, uid: str = Depends(_auth)) -> dict:
    pool = await _db()
    fields, vals = [], []
    if req.age is not None:
        fields.append(f"age=${len(vals)+1}"); vals.append(req.age)
    if req.city is not None:
        fields.append(f"city=${len(vals)+1}"); vals.append(req.city)
    if req.annual_income is not None:
        fields.append(f"annual_income=${len(vals)+1}"); vals.append(req.annual_income)
    if req.credit_score is not None:
        fields.append(f"credit_score=${len(vals)+1}"); vals.append(req.credit_score)
    if req.cached_listings is not None:
        fields.append(f"cached_listings=${len(vals)+1}"); vals.append(json.dumps(req.cached_listings))
    if req.last_analysis is not None:
        fields.append(f"last_analysis=${len(vals)+1}"); vals.append(json.dumps(req.last_analysis))
    if not fields:
        return {"status": "no-op"}
    vals.append(uuid.UUID(uid))
    await pool.execute(
        f"UPDATE users SET {', '.join(fields)} WHERE id=${len(vals)}", *vals
    )
    return {"status": "updated"}

@app.delete("/auth/me")
async def delete_account(uid: str = Depends(_auth)) -> dict:
    pool = await _db()
    await pool.execute("DELETE FROM users WHERE id=$1", uuid.UUID(uid))
    return {"status": "deleted"}

# ── Listing endpoints (seller) ─────────────────────────────────────────────────

def _ser(row: asyncpg.Record) -> dict:
    return {k: str(v) if isinstance(v, (uuid.UUID, datetime)) else v for k, v in dict(row).items()}

@app.post("/api/my-listings")
async def create_listing(req: ListingCreate, uid: str = Depends(_auth)) -> dict:
    if req.listing_type not in ("rent", "sale"):
        raise HTTPException(400, "listing_type must be 'rent' or 'sale'")
    pool = await _db()
    row = await pool.fetchrow(
        """INSERT INTO property_listings
           (owner_id,listing_type,title,address,city,price,bedrooms,bathrooms,sqft,description,agent_rules)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) RETURNING *""",
        uuid.UUID(uid), req.listing_type, req.title, req.address, req.city,
        req.price, req.bedrooms, req.bathrooms, req.sqft, req.description, req.agent_rules,
    )
    return _ser(row)

@app.get("/api/my-listings")
async def get_my_listings(uid: str = Depends(_auth)) -> list:
    pool = await _db()
    rows = await pool.fetch(
        "SELECT * FROM property_listings WHERE owner_id=$1 ORDER BY created_at DESC",
        uuid.UUID(uid),
    )
    return [_ser(r) for r in rows]

@app.post("/api/listings/{listing_id}/interest")
async def express_interest(
    listing_id: str,
    buyer_message: str = Query(""),
    uid: str = Depends(_auth),
) -> dict:
    pool = await _db()
    try:
        await pool.execute(
            "INSERT INTO interests (listing_id,buyer_id,buyer_message) VALUES ($1,$2,$3)",
            uuid.UUID(listing_id), uuid.UUID(uid), buyer_message,
        )
    except asyncpg.UniqueViolationError:
        raise HTTPException(409, "Already expressed interest in this listing")
    return {"status": "pending"}

@app.get("/api/interests/received")
async def received_interests(uid: str = Depends(_auth)) -> list:
    pool = await _db()
    rows = await pool.fetch("""
        SELECT i.id, i.status, i.buyer_message, i.created_at,
               u.full_name AS buyer_name, u.email AS buyer_email,
               u.age, u.city, u.annual_income, u.credit_score,
               pl.title AS listing_title, pl.address AS listing_address,
               pl.price AS listing_price, pl.listing_type
        FROM interests i
        JOIN users u ON i.buyer_id = u.id
        JOIN property_listings pl ON i.listing_id = pl.id
        WHERE pl.owner_id=$1
        ORDER BY i.created_at DESC
    """, uuid.UUID(uid))
    return [_ser(r) for r in rows]

@app.patch("/api/interests/{interest_id}")
async def update_interest(
    interest_id: str,
    status: str = Query(...),
    uid: str = Depends(_auth),
) -> dict:
    if status not in ("approved", "declined"):
        raise HTTPException(400, "status must be 'approved' or 'declined'")
    pool = await _db()
    row = await pool.fetchrow("""
        SELECT i.id FROM interests i
        JOIN property_listings pl ON i.listing_id = pl.id
        WHERE i.id=$1 AND pl.owner_id=$2
    """, uuid.UUID(interest_id), uuid.UUID(uid))
    if not row:
        raise HTTPException(404, "Interest not found")
    await pool.execute("UPDATE interests SET status=$1 WHERE id=$2", status, uuid.UUID(interest_id))
    return {"status": status}

# ── AI Agent chat ──────────────────────────────────────────────────────────────

_AGENT_SYSTEM = """You are DefrostBot, the AI real estate agent for Defrost.AI.
You act on behalf of clients — buyers/renters or sellers/landlords — and negotiate deals between them.
Think of yourself as a licensed real estate professional who also handles outreach and paperwork.

RENTAL LEGAL PROTECTIONS you always enforce:
• Security deposit: 1–2 months rent held in escrow; returned within 21 days of move-out
• Late payment: 5-day grace period, then 5% of monthly rent as late fee
• Lease break penalty: 2 months rent (exceptions: military orders, domestic violence)
• Income requirement: tenant must earn ≥ 3× monthly rent (gross)
• Eviction path: 3-Day Pay or Quit → 30-day Cure notice → Unlawful detainer filing

PURCHASE LEGAL PROTECTIONS you always enforce:
• Earnest money: 1–3% of purchase price held in escrow (forfeited if buyer defaults)
• Inspection contingency: 10 days to inspect and request repairs or cancel
• Financing contingency: 21 days to secure loan commitment
• Appraisal contingency: property must appraise at or above offer price
• Title insurance required to protect against undisclosed liens
• Typical closing timeline: 30–45 days from accepted offer

Be concise, professional, and proactive. When someone asks about a property, help them understand
costs, risks, and next steps. If you're talking to a seller, help them set fair terms and screen
buyers properly."""

@app.post("/api/chat")
async def chat(req: ChatReq, uid: str = Depends(_auth)) -> dict:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise HTTPException(500, "GROQ_API_KEY not set")
    messages: list[dict] = [{"role": "system", "content": _AGENT_SYSTEM}]
    for h in req.history[-10:]:
        messages.append(h)
    messages.append({"role": "user", "content": req.message})
    resp = await AsyncGroq(api_key=key).chat.completions.create(
        model="llama-3.3-70b-versatile", max_tokens=600, messages=messages,
    )
    return {"reply": resp.choices[0].message.content}

# ── Existing analysis + listings API ──────────────────────────────────────────

_photo_cache: dict[str, str | None] = {}
_ddg_lock = asyncio.Lock()
PREFERRED_DOMAINS = ("zillowstatic.com", "apartments.com", "rdcpix.com", "homesnap.com")

ANALYSIS_PROMPT = """\
You are a financial advisor. Analyze this rent-vs-buy situation:
- Age: {age}, City: {city}, Annual income: ${annual_income:,}, Credit score: {credit_score}

Consider local housing market for {city}, mortgage rates for credit score {credit_score},
28%/36% debt rules on ${annual_income:,}/yr, life stage at age {age}, 2025-2026 rates (~6-7%).

Return ONLY this JSON:
{{
  "recommendation": "RENT" or "BUY",
  "confidence": "high" or "medium" or "low",
  "headline": "one punchy sentence",
  "reasons": ["reason 1", "reason 2", "reason 3"],
  "monthly_rent_estimate": <integer>,
  "monthly_buy_estimate": <integer>,
  "timeline": "plain-English sentence on when to reconsider",
  "risk_factors": ["risk 1", "risk 2"]
}}
"""

async def _ddg_photo(address: str) -> str | None:
    if address in _photo_cache:
        return _photo_cache[address]
    async with _ddg_lock:
        if address in _photo_cache:
            return _photo_cache[address]
        await asyncio.sleep(1.2)
        try:
            results = list(DDGS().images(f"{address} listing photos", max_results=5))
        except Exception:
            _photo_cache[address] = None
            return None
        for domain in PREFERRED_DOMAINS:
            for r in results:
                if domain in r.get("image", ""):
                    _photo_cache[address] = r["image"]
                    return r["image"]
        _photo_cache[address] = None
        return None

def _groq() -> AsyncGroq:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not set")
    return AsyncGroq(api_key=key)

@app.post("/api/analyze")
async def analyze(req: AnalysisRequest) -> dict:
    prompt = ANALYSIS_PROMPT.format(
        age=req.age, city=req.city,
        annual_income=req.annual_income, credit_score=req.credit_score,
    )
    resp = await _groq().chat.completions.create(
        model="llama-3.3-70b-versatile", max_tokens=1024,
        messages=[
            {"role": "system", "content": "Return ONLY valid JSON, no prose."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except (json.JSONDecodeError, KeyError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

def _parse_city_state(city: str) -> tuple[str, str]:
    # "City, ST"  or  "City, State Name"
    parts = [p.strip() for p in city.split(",")]
    if len(parts) >= 2:
        last = parts[-1].strip()
        if last.upper() in US_STATES:
            return ", ".join(parts[:-1]), last.upper()
        if last.lower() in _STATE_NAMES:
            return ", ".join(parts[:-1]), _STATE_NAMES[last.lower()]

    # "City StateName"  or  "City ST"  (no comma)
    words = city.strip().split()
    if len(words) >= 2:
        # Single last word: "Long Beach California" → CA
        w1 = words[-1]
        if w1.upper() in US_STATES:
            return " ".join(words[:-1]), w1.upper()
        if w1.lower() in _STATE_NAMES:
            return " ".join(words[:-1]), _STATE_NAMES[w1.lower()]
        # Two-word state: "New York City New York" → NY
        if len(words) >= 3:
            w2 = " ".join(words[-2:]).lower()
            if w2 in _STATE_NAMES:
                return " ".join(words[:-2]), _STATE_NAMES[w2]

    return city.strip(), ""

def _normalize_listing(raw: dict, listing_type: str) -> dict:
    addr = raw.get("formattedAddress") or raw.get("addressLine1") or ""
    city_state = raw.get("city", "")
    if raw.get("state"):
        city_state = f"{city_state}, {raw['state']}"
    sqft = raw.get("squareFootage") or raw.get("livingArea")
    price = raw.get("price") or raw.get("listPrice") or raw.get("rent") or 0
    beds  = raw.get("bedrooms") or raw.get("beds") or 0
    baths = raw.get("bathrooms") or raw.get("baths") or 0
    ptype = raw.get("propertyType") or "House"
    lat   = raw.get("latitude")
    lon   = raw.get("longitude")
    satellite_url = None
    if lat and lon:
        d = 0.0008
        bbox = f"{lon-d},{lat-d},{lon+d},{lat+d}"
        satellite_url = (
            "https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export"
            f"?bbox={bbox}&bboxSR=4326&imageSR=4326&size=600,400&format=png&f=image"
        )
    return {
        "address": addr, "neighborhood": city_state,
        "price": int(price), "beds": int(beds) if beds else 0,
        "baths": float(baths) if baths else 0, "sqft": int(sqft) if sqft else 0,
        "property_type": ptype, "days_on_market": max(0, raw.get("daysOnMarket") or 0),
        "highlights": [], "photo_url": satellite_url, "listing_type": listing_type,
        "year_built": raw.get("yearBuilt"), "lot_size": raw.get("lotSize"),
        "county": raw.get("county", ""), "zip_code": raw.get("zipCode", ""),
        "latitude": lat, "longitude": lon,
    }

def _platform_listing_to_card(row: dict, listing_type: str) -> dict:
    return {
        "listing_id": row["id"],
        "address": row["address"],
        "neighborhood": row["city"],
        "price": row["price"],
        "beds": row.get("bedrooms") or 0,
        "baths": row.get("bathrooms") or 0,
        "sqft": row.get("sqft") or 0,
        "property_type": "House",
        "days_on_market": 0,
        "highlights": [],
        "photo_url": None,
        "listing_type": listing_type,
        "year_built": None,
        "lot_size": None,
        "county": "",
        "zip_code": "",
        "latitude": None,
        "longitude": None,
        "platform": True,
        "title": row.get("title", ""),
    }

@app.get("/api/listings")
async def listings(
    city: str = Query(..., min_length=2),
    listing_type: str = Query("buy", pattern="^(buy|rent)$"),
    offset: int = Query(0, ge=0),
) -> dict:
    MAX = 10
    city_name, state = _parse_city_state(city)
    db_type = "rent" if listing_type == "rent" else "sale"

    # ── 1. Platform listings (always shown first) ──────────────────────────────
    platform: list[dict] = []
    try:
        pool = await _db()
        rows = await pool.fetch(
            "SELECT * FROM property_listings "
            "WHERE LOWER(city) LIKE $1 AND listing_type=$2 AND status='active' "
            "ORDER BY created_at DESC LIMIT 5",
            f"%{city_name.lower()}%", db_type,
        )
        platform = [_platform_listing_to_card(_ser(r), listing_type) for r in rows]
    except Exception:
        pass

    # ── 2. Rentcast listings (fill remaining slots up to MAX) ──────────────────
    rentcast: list[dict] = []
    rentcast_key = os.environ.get("RENTCAST_API_KEY")
    remaining = MAX - len(platform)
    if rentcast_key and remaining > 0:
        endpoint = "/listings/rental/long-term" if listing_type == "rent" else "/listings/sale"
        params: dict = {"city": city_name, "limit": remaining, "status": "Active", "offset": offset}
        if state:
            params["state"] = state
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    RENTCAST_BASE + endpoint,
                    headers={"X-Api-Key": rentcast_key, "Accept": "application/json"},
                    params=params,
                )
            if r.status_code == 401:
                raise HTTPException(401, "Invalid RENTCAST_API_KEY")
            if r.status_code == 429:
                raise HTTPException(429, "Rentcast rate limit reached")
            if r.is_success:
                raw = r.json() if isinstance(r.json(), list) else r.json().get("listings", [])
                rentcast = [_normalize_listing(l, listing_type) for l in raw[:remaining]]
        except HTTPException:
            raise
        except Exception:
            pass
    elif not rentcast_key and not platform:
        raise HTTPException(503, "RENTCAST_API_KEY not set — add it to your .env")

    combined = (platform + rentcast)[:MAX]
    return {"listings": combined, "listing_type": listing_type, "city": city}

@app.get("/api/listing-photo")
async def listing_photo(address: str = Query(..., min_length=2)) -> dict:
    return {"photo_url": await _ddg_photo(address)}

# ── Page routes ────────────────────────────────────────────────────────────────

@app.get("/")
async def landing() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/app")
async def app_view() -> FileResponse:
    return FileResponse(STATIC_DIR / "rent_vs_buy.html")

@app.get("/founders")
async def founders_view() -> FileResponse:
    return FileResponse(STATIC_DIR / "founders.html")

@app.get("/team")
async def team_view() -> FileResponse:
    return FileResponse(STATIC_DIR / "team.html")

app.mount("/images", StaticFiles(directory=STATIC_DIR / "images"), name="images")
