"""
All LLM prompts in one place (spec §3). Keeping prompts together makes them
easy to review, version, and A/B test — and keeps prompt text out of business
logic.

Karpathy rule: explicit. These are plain strings, not templates hidden behind
a framework. ``.format(...)`` at the call site, nothing magical.
"""
from __future__ import annotations

# Parses a renter's free-text message into the RentalRequirements schema.
# The model must return JSON matching RentalRequirements exactly.
REQUIREMENTS_PARSER_SYSTEM = """\
You convert a renter's free-text housing request into a strict JSON object.

Return ONLY JSON, no prose. Use these keys (omit a key only if truly unknown):
  city (string, required)
  neighborhoods (array of strings)
  max_monthly_rent_dollars (number, required)
  min_monthly_rent_dollars (number or null)
  bedrooms (integer or null)
  bathrooms (number or null)
  move_in_date (ISO 8601 date, required)
  lease_duration_months (integer, required)
  pets_allowed (boolean or null)
  parking_required (boolean)
  utilities_included (boolean or null)
  furnished (boolean or null)
  max_commute_minutes (integer or null)
  commute_destination (string or null)
  additional_notes (string or null)

If a required field is missing from the message, make the most reasonable
inference and put your assumption in additional_notes. Never invent a city.
"""

# Drafts the initial outreach email to a landlord. Tone: professional, concise.
OUTREACH_EMAIL_SYSTEM = """\
You write a short, professional outreach email to a landlord on behalf of a renter.

Constraints:
- Under 150 words.
- Address the landlord by name if known.
- State move-in date, lease length, and that the renter is pre-qualified to talk.
- Do NOT include the renter's SSN, income figures, or date of birth.
- Do NOT promise anything the renter has not authorized.
Return JSON with keys: subject (string), body (string).
"""

# Classifies a landlord reply so the workflow can branch (interested vs not).
RESPONSE_SENTIMENT_SYSTEM = """\
Classify a landlord's reply to a rental inquiry.

Return ONLY one lowercase word:
  positive  — landlord is open to renting / wants to schedule / asks for info
  negative  — unit is gone, not interested, or declines
  neutral   — ambiguous, autoreply, or off-topic
"""

# Decides the next outreach channel given a landlord's behavioral history.
CHANNEL_SELECTION_SYSTEM = """\
Given a landlord's contact history (response rate per channel, hours-to-respond,
ghost count), choose the single best next channel to reach them.

Return ONLY one lowercase word: email, sms, phone, or social_dm.
Prefer the channel with the highest historical response rate; if no history,
prefer email first, then sms, then phone.
"""
