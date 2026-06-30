"""
Enrichment Agent — prospect discovery and enrichment.

Accepts a niche descriptor string, crawls the web, extracts company and
contact information, computes an intent score, and persists each new
Prospect to the ``leads`` table via the LinearEngine.

Design constraints
------------------
- All I/O (HTTP, Ollama) is isolated behind replaceable helpers so the
  agent is fully unit-testable without network access.
- Ollama is the primary entity extractor; regex is the fallback.
- Deduplication: non-null emails are updated in-place; null-email records
  are always inserted as new rows.
- A ``prospect_discovered`` event is published to the EventBus after each
  successful persist.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

logger = logging.getLogger("EnrichmentAgent")

# Maximum pages crawled per prospect to limit latency / bandwidth.
_MAX_PAGES_PER_PROSPECT = 5

# Additive intent-score bonuses (sum capped at 100).
_SCORE_JOB_POSTING = 30
_SCORE_EMAIL_RESOLVED = 20
_SCORE_HOMEPAGE_OK = 20
_SCORE_NAME_IN_RESULTS = 30


class Prospect:
    """Lightweight value object representing a discovered prospect."""

    __slots__ = (
        "company_name",
        "contact_name",
        "email",
        "website",
        "linkedin_url",
        "intent_score",
        "needs_review",
    )

    def __init__(
        self,
        company_name: str = "",
        contact_name: str = "",
        email: Optional[str] = None,
        website: str = "",
        linkedin_url: str = "",
        intent_score: int = 0,
        needs_review: bool = False,
    ) -> None:
        self.company_name = company_name
        self.contact_name = contact_name
        self.email = email
        self.website = website
        self.linkedin_url = linkedin_url
        self.intent_score = intent_score
        self.needs_review = needs_review


class EnrichmentAgent:
    """
    Discovers and enriches prospects for a given niche.

    Parameters
    ----------
    db_session:
        Optional SQLAlchemy ``Session``.  If omitted a new session is created
        from ``SessionLocal`` when ``run()`` is called.
    ollama_timeout:
        Seconds to wait for Ollama before falling back to regex extraction.
    """

    def __init__(self, db_session=None, ollama_timeout: float = 10.0) -> None:
        self._db = db_session
        self._ollama_timeout = ollama_timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, niche_descriptor: str) -> list[Prospect]:
        """
        Discover and enrich prospects for ``niche_descriptor``.

        Validates the input, performs web search + crawling, persists results
        and returns the list of successfully persisted Prospects.

        Raises
        ------
        ValueError
            If ``niche_descriptor`` has fewer than 1 or more than 500
            non-whitespace characters.
        """
        non_ws = len(niche_descriptor.strip())
        if non_ws < 1:
            raise ValueError(
                "niche_descriptor must contain at least 1 non-whitespace character."
            )
        if non_ws > 500:
            raise ValueError(
                "niche_descriptor must contain at most 500 non-whitespace characters."
            )

        logger.info("EnrichmentAgent.run() niche=%r", niche_descriptor)
        search_results = self._web_search(niche_descriptor)
        prospects: list[Prospect] = []

        for result in search_results:
            url = result.get("url", "")
            company_name = result.get("title", "")
            if not url:
                continue

            # Crawl the prospect website
            pages_html = self._crawl_prospect(url)
            combined_html = " ".join(pages_html)

            # Entity extraction: Ollama first, regex fallback
            extracted = self._extract_entities(combined_html, niche_descriptor, url)
            if not extracted:
                logger.debug("No usable fields for %s — skipping.", url)
                continue

            # Merge search-result metadata with extracted fields
            p = Prospect(
                company_name=extracted.get("company_name") or company_name,
                contact_name=extracted.get("contact_name", ""),
                email=extracted.get("email"),
                website=url,
                linkedin_url=extracted.get("linkedin_url", ""),
            )

            if p.email is None:
                p.needs_review = True

            # Compute intent score
            signals = {
                "job_posting_match": extracted.get("has_job_posting", False),
                "email_resolved": p.email is not None,
                "homepage_ok": extracted.get("homepage_ok", False),
                "name_in_results": bool(
                    company_name and company_name.lower() in niche_descriptor.lower()
                ),
            }
            p.intent_score = self._compute_intent_score(signals)

            # Persist to database
            persisted = self._persist_prospect(p)
            if persisted:
                prospects.append(p)

        return prospects

    # ------------------------------------------------------------------
    # Intent scoring
    # ------------------------------------------------------------------

    def _compute_intent_score(self, signals: dict) -> int:
        """
        Compute additive intent score from observable signals, capped at 100.

        Signals
        -------
        job_posting_match : bool  → +30
        email_resolved    : bool  → +20
        homepage_ok       : bool  → +20
        name_in_results   : bool  → +30
        """
        score = 0
        if signals.get("job_posting_match"):
            score += _SCORE_JOB_POSTING
        if signals.get("email_resolved"):
            score += _SCORE_EMAIL_RESOLVED
        if signals.get("homepage_ok"):
            score += _SCORE_HOMEPAGE_OK
        if signals.get("name_in_results"):
            score += _SCORE_NAME_IN_RESULTS
        return min(score, 100)

    # ------------------------------------------------------------------
    # Web search (uses agents.tools.web_search if available)
    # ------------------------------------------------------------------

    def _web_search(self, query: str) -> list[dict]:
        """Return a list of {title, url, snippet} dicts for the query."""
        try:
            from agents.tools.web_search import search_web  # type: ignore[import]

            return search_web(query) or []
        except Exception as exc:
            logger.warning("Web search unavailable: %s", exc)
            return []

    # ------------------------------------------------------------------
    # HTTP crawler
    # ------------------------------------------------------------------

    def _crawl_prospect(self, start_url: str) -> list[str]:
        """
        Crawl ``start_url`` and up to ``_MAX_PAGES_PER_PROSPECT - 1``
        internal links, returning a list of raw HTML strings.
        """
        import requests  # imported lazily to allow mocking in tests
        from bs4 import BeautifulSoup  # type: ignore[import]

        visited: set[str] = set()
        queue = [start_url]
        pages: list[str] = []

        while queue and len(pages) < _MAX_PAGES_PER_PROSPECT:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                resp = requests.get(url, timeout=10, allow_redirects=True)
                if resp.status_code == 200:
                    html = resp.text
                    pages.append(html)
                    # Queue internal links
                    soup = BeautifulSoup(html, "html.parser")
                    base = urlparse(start_url)
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        abs_href = urljoin(url, href)
                        parsed = urlparse(abs_href)
                        if parsed.netloc == base.netloc and abs_href not in visited:
                            queue.append(abs_href)
            except Exception as exc:
                logger.debug("Crawl error for %s: %s", url, exc)

        return pages

    # ------------------------------------------------------------------
    # Entity extraction
    # ------------------------------------------------------------------

    def _extract_entities(
        self, html: str, niche: str, url: str
    ) -> Optional[dict]:
        """
        Try Ollama first; fall back to regex.  Returns None if neither
        method yields any usable fields.
        """
        try:
            result = self._extract_with_ollama(html, niche)
            if result:
                result.setdefault("homepage_ok", True)
                return result
        except Exception as exc:
            logger.warning(
                "Ollama unavailable (%s) — falling back to regex extraction.", exc
            )

        result = self._extract_with_regex(html, url)
        return result if result else None

    def _extract_with_ollama(self, html: str, niche: str) -> Optional[dict]:
        """
        Call local Ollama to extract structured data from HTML.

        Raises
        ------
        Exception
            On connection refused, timeout, or any Ollama error — callers
            should fall back to regex extraction.
        """
        import requests

        prompt = (
            f"Extract JSON from this HTML for a '{niche}' company website.\n"
            "Return ONLY a JSON object with keys: company_name, contact_name, "
            "email, linkedin_url, has_job_posting (bool).\n"
            "If a field cannot be determined, set it to null.\n"
            f"HTML (first 4000 chars):\n{html[:4000]}"
        )

        ollama_url = "http://localhost:11434/api/generate"
        try:
            import os

            ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip(
                "/"
            ) + "/api/generate"
        except Exception:
            pass

        resp = requests.post(
            ollama_url,
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=self._ollama_timeout,
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "")

        # Parse JSON from response
        json_match = re.search(r"\{.*?\}", raw, re.DOTALL)
        if not json_match:
            return None
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            return None

    def _extract_with_regex(self, html: str, url: str) -> Optional[dict]:
        """
        Fallback regex extraction for company name, email, and LinkedIn URL.

        Returns None if no usable fields can be extracted.
        """
        result: dict = {}

        # Email
        email_match = re.search(
            r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", html
        )
        if email_match:
            result["email"] = email_match.group()

        # LinkedIn
        li_match = re.search(r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[^\s\"'>]+", html)
        if li_match:
            result["linkedin_url"] = li_match.group()

        # Company name from <title>
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if title_match:
            result["company_name"] = title_match.group(1).strip()

        # Job posting detection
        result["has_job_posting"] = bool(
            re.search(r"(careers?|jobs?|hiring|we.?re.?hiring)", html, re.IGNORECASE)
        )
        result["homepage_ok"] = True

        return result if (result.get("email") or result.get("company_name")) else None

    # ------------------------------------------------------------------
    # Database persistence
    # ------------------------------------------------------------------

    def _persist_prospect(self, prospect: Prospect) -> bool:
        """
        Upsert prospect into the ``leads`` table.

        - Non-null email: update existing record if found, else insert.
        - Null email: always insert as a new record.

        Returns True on success, False on failure.
        """
        from backend.db.models import Lead
        from backend.db.session import SessionLocal
        from backend.services.event_bus import event_bus

        db = self._db or SessionLocal()
        close_on_exit = self._db is None
        try:
            if prospect.email is not None:
                existing = (
                    db.query(Lead).filter(Lead.email == prospect.email).first()
                )
                if existing:
                    existing.company = prospect.company_name
                    existing.name = prospect.contact_name
                    existing.website = prospect.website
                    existing.linkedin_url = prospect.linkedin_url
                    existing.intent_score = prospect.intent_score
                    db.commit()
                    lead_id = existing.id
                else:
                    lead = Lead(
                        email=prospect.email,
                        name=prospect.contact_name,
                        company=prospect.company_name,
                        website=prospect.website,
                        linkedin_url=prospect.linkedin_url,
                        intent_score=prospect.intent_score,
                        needs_review=prospect.needs_review,
                    )
                    db.add(lead)
                    db.commit()
                    db.refresh(lead)
                    lead_id = lead.id
            else:
                lead = Lead(
                    email=None,
                    name=prospect.contact_name,
                    company=prospect.company_name,
                    website=prospect.website,
                    linkedin_url=prospect.linkedin_url,
                    intent_score=prospect.intent_score,
                    needs_review=True,
                )
                db.add(lead)
                db.commit()
                db.refresh(lead)
                lead_id = lead.id

            event_bus.publish(
                "prospect_discovered",
                {
                    "lead_id": lead_id,
                    "company": prospect.company_name,
                    "email": prospect.email,
                },
            )
            return True
        except Exception as exc:
            logger.error("Failed to persist prospect %s: %s", prospect.website, exc)
            db.rollback()
            return False
        finally:
            if close_on_exit:
                db.close()
