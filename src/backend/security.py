import hashlib
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from enum import StrEnum
from threading import Lock
from typing import Optional

from src.backend.config import settings

logger = logging.getLogger(__name__)


class QueryScope(StrEnum):
    PARTY_PROGRAMMES = "party_programmes"
    POLITICIANS_OPINIONS = "politicians_opinions"
    VOTINGS = "votings"


class QuerySafetyError(ValueError):
    """Raised when user query violates prompt-injection or scope constraints."""


INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(ignore|disregard|bypass)\b.{0,80}\b(instruction\w*|system\w*|prompt\w*)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(ignoruj|zignoruj|pomiń|obejdź)\b.{0,80}\b(instrukcj\w*|system\w*|prompt\w*)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(developer mode|jailbreak|prompt injection)\b", re.IGNORECASE),
    re.compile(
        r"\b(reveal|show|print)\b.{0,80}\b(system prompt|hidden prompt)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(ujawnij|pokaż|wydrukuj)\b.{0,80}\b(prompt|instrukcj[ea])\b", re.IGNORECASE
    ),
)

POLITICAL_KEYWORDS_BY_SCOPE: dict[QueryScope, tuple[str, ...]] = {
    QueryScope.PARTY_PROGRAMMES: (
        "parti",
        "program",
        "stanowisk",
        "postulat",
        "wybor",
        "rząd",
        "rządu",
        "sejm",
        "senat",
        "ustaw",
        "podatk",
        "zdrow",
        "edukac",
        "energi",
        "mieszkan",
        "cpk",
        "in vitro",
        "abor",
        "emerytur",
        "rent",
        "rolnict",
        "obron",
        "ukrain",
        "sądownict",
        "koalicj",
        "pis",
        "lewic",
        "konfeder",
        "psl",
        "trzecia droga",
        "2050",
    ),
    QueryScope.POLITICIANS_OPINIONS: (
        "poseł",
        "posł",
        "posłank",
        "polityk",
        "politycz",
        "wypowied",
        "opinia",
        "stanowisk",
        "parti",
        "klub",
        "sejm",
        "senat",
        "rząd",
        "ustaw",
        "głosowan",
        "podatk",
        "zdrow",
        "edukac",
        "energi",
        "mieszkan",
        "cpk",
        "in vitro",
        "abor",
        "emerytur",
        "rent",
        "rolnict",
        "obron",
        "ukrain",
        "sądownict",
        "co sądzi",
        "co myśli",
        "jak ocenia",
        "czy popiera",
    ),
    QueryScope.VOTINGS: (
        "głosowan",
        "głosow",
        "sejm",
        "senat",
        "ustaw",
        "projekt",
        "druk",
        "uchwa",
        "podatk",
        "zdrow",
        "edukac",
        "energi",
        "mieszkan",
        "cpk",
        "in vitro",
        "abor",
        "emerytur",
        "rent",
        "rolnict",
        "obron",
        "ukrain",
        "sądownict",
        "zus",
        "wakacje od zus",
        "frekwencj",
        "jak głosował",
        "jak głosowali",
    ),
}

NON_POLITICAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(stolica|capital)\b", re.IGNORECASE),
    re.compile(r"\b(pogoda|weather)\b", re.IGNORECASE),
    re.compile(r"\b(przepis|recipe)\b", re.IGNORECASE),
    re.compile(r"\b(film|serial|muzyka|song)\b", re.IGNORECASE),
    re.compile(r"\b(football|piłka nożna|mecz)\b", re.IGNORECASE),
)

BLOCKED_PROMPT_INJECTION_MESSAGE = (
    "Ze względów bezpieczeństwa nie mogę wykonać tej prośby, ponieważ zawiera próbę "
    "nadpisania instrukcji systemowych (prompt injection)."
)
BLOCKED_SCOPE_MESSAGE = (
    "To pytanie jest poza zakresem tej sekcji. Mogę odpowiadać wyłącznie na pytania "
    "dotyczące programów partii, wypowiedzi polityków lub głosowań sejmowych."
)


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def _contains_prompt_injection(query: str) -> bool:
    return any(pattern.search(query) for pattern in INJECTION_PATTERNS)


def _is_scope_related(query: str, scope: QueryScope) -> bool:
    keywords = POLITICAL_KEYWORDS_BY_SCOPE.get(scope, ())
    if any(keyword in query for keyword in keywords):
        return True
    if any(pattern.search(query) for pattern in NON_POLITICAL_PATTERNS):
        return False
    return False


def enforce_query_safety(query: str, scope: QueryScope) -> None:
    normalized_query = _normalize_query(query)
    if _contains_prompt_injection(normalized_query):
        raise QuerySafetyError(BLOCKED_PROMPT_INJECTION_MESSAGE)
    if not _is_scope_related(normalized_query, scope):
        raise QuerySafetyError(BLOCKED_SCOPE_MESSAGE)


class InMemoryRateLimiter:
    """
    Sliding-window in-memory rate limiter to mitigate DDoS/spam requests.
    Thread-safe and prunes stale records periodically.
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        with self.lock:
            # Clean up old timestamps for this client
            cutoff = now - self.window_seconds
            timestamps = [ts for ts in self.requests[client_id] if ts > cutoff]
            if len(timestamps) >= self.max_requests:
                self.requests[client_id] = timestamps
                return False
            timestamps.append(now)
            self.requests[client_id] = timestamps
            return True

    def reset(self) -> None:
        with self.lock:
            self.requests.clear()


# Global rate limiter for contact form submissions (5 requests per 10 minutes per IP)
contact_rate_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=600)


def anonymize_ip(ip: Optional[str]) -> str:
    """
    Anonymize or hash IP address for RODO/GDPR compliance while retaining
    auditability against abuse.
    """
    if not ip or ip == "unknown":
        return "anonymous"
    # Create a 1-way salted truncated hash
    salt = "politics-antispam-salt"
    hashed = hashlib.sha256(f"{salt}-{ip}".encode("utf-8")).hexdigest()[:16]
    return f"anon_{hashed}"


def verify_cloudflare_turnstile(
    token: Optional[str], remote_ip: Optional[str] = None
) -> tuple[bool, str]:
    """
    Verifies Cloudflare Turnstile captcha token.
    If no secret key is configured (e.g. local environment), allows requests
    unless an explicit dummy token is invalid.
    """
    secret = settings.cloudflare_turnstile_secret_key
    if not secret:
        # In local/test mode without Cloudflare secret key configured
        return (
            True,
            "Cloudflare Turnstile secret key not configured (bypassed in dev mode)",
        )

    if not token or not token.strip():
        return False, "Wymagana weryfikacja antyspamowa Cloudflare Turnstile."

    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    payload = {
        "secret": secret,
        "response": token.strip(),
    }
    if remote_ip and remote_ip != "unknown":
        payload["remoteip"] = remote_ip

    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("success"):
                return True, "Turnstile verification successful"
            error_codes = result.get("error-codes", [])
            logger.warning("Cloudflare Turnstile verification failed: %s", error_codes)
            return (
                False,
                f"Weryfikacja Cloudflare Turnstile nie powiodła się: {', '.join(error_codes)}",
            )
    except Exception as exc:
        logger.error("Error communicating with Cloudflare Turnstile API: %s", exc)
        return False, f"Błąd weryfikacji Cloudflare: {exc}"
