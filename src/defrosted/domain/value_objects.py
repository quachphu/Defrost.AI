"""
Value objects for the Defrosted domain.

Value objects are immutable. Two value objects with the same data are equal.
They validate themselves on construction — never pass raw strings where a
typed value object is expected.

Karpathy rule: no magic validators. Every validation is an explicit if/raise.
"""
from __future__ import annotations

import re
from decimal import Decimal

from pydantic import BaseModel, model_validator


class Money(BaseModel):
    """
    Represents a monetary amount in USD cents to avoid float arithmetic.

    We store cents as integers because:
        Decimal("1850.00") * Decimal("12") is fine
        1850.0 * 12 = 22199.999999... is not

    Example:
        rent = Money(cents=185000)  # $1,850.00
        rent.dollars  # Decimal("1850.00")
    """
    model_config = {"frozen": True}

    cents: int  # always in USD cents, always positive

    @model_validator(mode="after")
    def cents_must_be_positive(self) -> Money:
        if self.cents <= 0:
            raise ValueError(
                f"Money.cents must be positive, got {self.cents}. "
                "Use Money(cents=185000) for $1,850.00."
            )
        return self

    @property
    def dollars(self) -> Decimal:
        return Decimal(self.cents) / 100

    @classmethod
    def from_dollars(cls, dollars: Decimal | float | int) -> Money:
        cents = int(Decimal(str(dollars)) * 100)
        return cls(cents=cents)

    def __add__(self, other: Money) -> Money:
        return Money(cents=self.cents + other.cents)

    def __lt__(self, other: Money) -> bool:
        return self.cents < other.cents

    def __repr__(self) -> str:
        return f"Money(${self.dollars:.2f})"


class Address(BaseModel):
    """
    A US postal address.
    PostGIS coordinates are stored separately in the Listing entity.
    """
    model_config = {"frozen": True}

    street: str
    unit: str | None = None      # apartment number, if any
    city: str
    state: str                   # 2-letter code: "CA", "NY"
    zip_code: str

    @model_validator(mode="after")
    def validate_fields(self) -> Address:
        if not re.match(r"^[A-Z]{2}$", self.state.upper()):
            raise ValueError(
                f"Address.state must be a 2-letter US state code, got '{self.state}'"
            )
        if not re.match(r"^\d{5}(-\d{4})?$", self.zip_code):
            raise ValueError(
                f"Address.zip_code must be 5-digit or ZIP+4 format, got '{self.zip_code}'"
            )
        return self

    @property
    def full_address(self) -> str:
        unit_part = f" #{self.unit}" if self.unit else ""
        return f"{self.street}{unit_part}, {self.city}, {self.state} {self.zip_code}"


class PhoneNumber(BaseModel):
    """
    E.164 formatted phone number for Twilio and Bland.ai calls.
    Always store normalized — never store raw user input.
    """
    model_config = {"frozen": True}

    e164: str  # e.g. "+14155552671"

    @model_validator(mode="after")
    def must_be_e164(self) -> PhoneNumber:
        if not re.match(r"^\+[1-9]\d{1,14}$", self.e164):
            raise ValueError(
                f"PhoneNumber must be E.164 format (e.g. '+14155552671'), got '{self.e164}'"
            )
        return self

    @classmethod
    def from_us_number(cls, raw: str) -> PhoneNumber:
        """
        Parse a US phone number in any common format to E.164.
        Raises ValueError if parsing fails — never returns None.
        """
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 10:
            return cls(e164=f"+1{digits}")
        if len(digits) == 11 and digits[0] == "1":
            return cls(e164=f"+{digits}")
        raise ValueError(
            f"Cannot parse '{raw}' as a US phone number. "
            f"Expected 10 digits (or 11 with country code 1), got {len(digits)} digits."
        )
