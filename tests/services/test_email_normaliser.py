"""
Hypothesis property test for email normalisation.

Property: normalise(normalise(x)) == normalise(x)  (idempotency)

Verifies that our email normaliser (lowercase + strip whitespace) is
idempotent across at least 100 examples.
"""

from __future__ import annotations

import pytest

try:
    from hypothesis import given, settings
    import hypothesis.strategies as st

    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False
    # Provide no-op stubs so module-level decorators don't raise NameError
    def given(*_args, **_kwargs):  # type: ignore[misc]
        return lambda f: f

    def settings(*_args, **_kwargs):  # type: ignore[misc]
        return lambda f: f

    class _StubStrategies:  # type: ignore[misc]
        def __getattr__(self, name: str) -> object:  # type: ignore[override]
            return lambda *_a, **_kw: None

    st = _StubStrategies()  # type: ignore[assignment]


def normalise(email: str) -> str:
    """
    Normalise an email address: lowercase and strip surrounding whitespace.

    This is the canonical normalisation function used across the outreach
    pipeline when storing or comparing email addresses.
    """
    return email.strip().lower()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_normalise_lowercases():
    assert normalise("User@EXAMPLE.COM") == "user@example.com"


def test_normalise_strips_whitespace():
    assert normalise("  user@example.com  ") == "user@example.com"


def test_normalise_combined():
    assert normalise("  HELLO@World.org  ") == "hello@world.org"


def test_normalise_already_normalised():
    assert normalise("hello@world.org") == "hello@world.org"


@pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@given(st.emails())
@settings(max_examples=100)
def test_normalise_idempotent_on_emails(email: str):
    """normalise is idempotent: normalise(normalise(x)) == normalise(x)."""
    once = normalise(email)
    twice = normalise(once)
    assert once == twice


@pytest.mark.skipif(not HYPOTHESIS_AVAILABLE, reason="hypothesis not installed")
@given(st.text())
@settings(max_examples=100)
def test_normalise_idempotent_on_arbitrary_strings(s: str):
    """Idempotency holds for arbitrary strings, not just valid email addresses."""
    once = normalise(s)
    twice = normalise(once)
    assert once == twice
