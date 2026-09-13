"""
Tests for context_selector.py

All tests use mocked GeminiClient — no live DB or Gemini API calls.
Token counts are supplied by the mock so tests are fully deterministic.

Covers:
  - select_bounded_context (core primitive)
  - select_request_context (Phase 1 wrapper)
  - select_current_context (Phase 2 wrapper)
"""
import pytest
from unittest.mock import MagicMock
from app.services.context_selector import (
    select_bounded_context,
    select_request_context,
    select_current_context,
    BoundedContext,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_history(*pairs: tuple[str, str]) -> list[dict]:
    """Build a history list from (user_text, assistant_text) pairs."""
    msgs = []
    for i, (user_text, asst_text) in enumerate(pairs):
        msgs.append({"id": f"u{i+1}", "role": "user", "content": user_text})
        msgs.append({"id": f"a{i+1}", "role": "assistant", "content": asst_text})
    return msgs


def make_client(token_sequence: list[int]) -> MagicMock:
    """
    Build a mock GeminiClient whose count_tokens returns values from token_sequence
    in order (one value consumed per call).
    build_contents is a passthrough.
    """
    client = MagicMock()
    client.build_contents.side_effect = lambda msgs: msgs
    client.count_tokens.side_effect = iter(token_sequence)
    return client


# ════════════════════════════════════════════════════════════════════════════
# select_bounded_context — core primitive
# ════════════════════════════════════════════════════════════════════════════

def test_bounded_within_limit_returns_all():
    msgs = make_history(("Hello", "Hi"))
    client = make_client([800])
    result = select_bounded_context(client, msgs, protected_tail_ids={"a1"}, limit_tokens=1000)
    assert result.token_count == 800
    assert result.message_count == 2
    assert result.start_id == "u1"
    assert result.end_id == "a1"


def test_bounded_removes_oldest_pair():
    msgs = make_history(("A", "B"), ("C", "D"))
    client = make_client([1200, 700])
    result = select_bounded_context(
        client, msgs, protected_tail_ids={"a2"}, limit_tokens=1000
    )
    ids = [m["id"] for m in result.selected]
    assert "u1" not in ids
    assert "a1" not in ids
    assert "u2" in ids
    assert "a2" in ids


def test_bounded_never_removes_protected():
    msgs = make_history(("A", "B"))
    # Both messages exceed; only a1 is protected, so u1 gets removed.
    # After removing u1, still exceeds => protected alone exceeds => ValueError
    client = make_client([1100, 1050, 1050])
    with pytest.raises(ValueError, match="Protected messages"):
        select_bounded_context(
            client, msgs, protected_tail_ids={"u1", "a1"}, limit_tokens=1000
        )


def test_bounded_original_list_not_mutated():
    msgs = make_history(("A", "B"), ("C", "D"))
    original = [m["id"] for m in msgs]
    client = make_client([1200, 700])
    select_bounded_context(client, msgs, protected_tail_ids={"a2"}, limit_tokens=1000)
    assert [m["id"] for m in msgs] == original


def test_bounded_count_tokens_failure_raises():
    msgs = make_history(("A", "B"))
    client = MagicMock()
    client.build_contents.side_effect = lambda h: h
    client.count_tokens.side_effect = RuntimeError("Gemini token counting failed: API error")
    with pytest.raises(RuntimeError, match="Gemini token counting failed"):
        select_bounded_context(client, msgs, protected_tail_ids={"a1"}, limit_tokens=1000)


def test_bounded_multiple_pairs_removed():
    msgs = make_history(("A", "B"), ("C", "D"), ("E", "F"))
    client = make_client([1800, 1400, 900])
    result = select_bounded_context(
        client, msgs, protected_tail_ids={"a3"}, limit_tokens=1000
    )
    ids = [m["id"] for m in result.selected]
    assert "u1" not in ids
    assert "a1" not in ids
    assert "u2" not in ids
    assert "a2" not in ids
    assert "u3" in ids
    assert "a3" in ids


# ════════════════════════════════════════════════════════════════════════════
# select_request_context — Phase 1
# ════════════════════════════════════════════════════════════════════════════

def test_request_context_within_limit():
    history = make_history(("Hello", "Hi there"))
    client = make_client([800])
    result = select_request_context(client, history, "new-id", "Next", limit_tokens=1000)
    assert result.token_count == 800
    assert len(result.selected) == 3  # 2 history + 1 new user msg
    assert result.end_id == "new-id"


def test_request_context_full_history_sent():
    history = make_history(("A", "B"), ("C", "D"))
    client = make_client([400])
    result = select_request_context(client, history, "new-id", "E", limit_tokens=1000)
    assert result.message_count == 5
    assert result.selected[0]["id"] == "u1"
    assert result.start_id == "u1"


def test_request_context_truncates_oldest_first():
    history = make_history(("A", "B"), ("C", "D"), ("E", "F"))
    client = make_client([1500, 900])
    result = select_request_context(client, history, "new-id", "G", limit_tokens=1000)
    assert result.start_id == "u2"
    assert result.token_count == 900


def test_request_context_new_message_always_present():
    history = make_history(("A", "B"))
    client = make_client([1050, 400])
    result = select_request_context(client, history, "MY-ID", "Current", limit_tokens=1000)
    assert result.selected[-1]["id"] == "MY-ID"
    assert result.selected[-1]["role"] == "user"
    assert result.selected[-1]["content"] == "Current"


def test_request_context_never_exceeds_limit():
    history = make_history(("A", "B"), ("C", "D"), ("E", "F"))
    client = make_client([1800, 1400, 1100, 800])
    result = select_request_context(client, history, "new-id", "G", limit_tokens=1000)
    assert result.token_count <= 1000


def test_request_context_message_exceeds_limit_raises():
    history = []
    client = make_client([1200, 1200])
    with pytest.raises(ValueError, match="exceed"):
        select_request_context(client, history, "new-id", "Giant", limit_tokens=1000)


def test_request_context_message_exceeds_with_history_raises():
    history = make_history(("A", "B"))
    client = make_client([1500, 1300, 1300])
    with pytest.raises(ValueError, match="exceed"):
        select_request_context(client, history, "new-id", "Giant", limit_tokens=1000)


def test_request_context_start_id_after_truncation():
    history = make_history(("Msg1", "Reply1"), ("Msg2", "Reply2"), ("Msg3", "Reply3"))
    client = make_client([1100, 850])
    result = select_request_context(client, history, "new-id", "New", limit_tokens=1000)
    assert result.start_id == "u2"


def test_request_context_end_id_is_user_message():
    history = make_history(("A", "B"))
    client = make_client([500])
    result = select_request_context(client, history, "EXACT-ID", "Q", limit_tokens=1000)
    assert result.end_id == "EXACT-ID"


def test_request_context_complete_pair_removal():
    history = [
        {"id": "u1", "role": "user", "content": "Q1"},
        {"id": "a1", "role": "assistant", "content": "A1"},
        {"id": "u2", "role": "user", "content": "Q2"},
    ]
    client = make_client([1100, 700])
    result = select_request_context(client, history, "new-id", "New", limit_tokens=1000)
    ids = [m["id"] for m in result.selected]
    assert "u1" not in ids
    assert "a1" not in ids
    assert "u2" in ids


def test_request_context_empty_history_within_limit():
    client = make_client([300])
    result = select_request_context(client, [], "only-id", "First", limit_tokens=1000)
    assert result.token_count == 300
    assert result.message_count == 1
    assert result.start_id == "only-id"
    assert result.end_id == "only-id"


# ════════════════════════════════════════════════════════════════════════════
# select_current_context — Phase 2
# ════════════════════════════════════════════════════════════════════════════

def test_current_context_within_limit():
    req_context = make_history(("Hello", "Hi")) + [{"id": "u2", "role": "user", "content": "Next"}]
    client = make_client([900])
    result = select_current_context(
        client, req_context, "asst-1", "Response text", limit_tokens=1000
    )
    assert result.token_count == 900
    assert result.end_id == "asst-1"


def test_current_context_assistant_always_present():
    req_context = make_history(("A", "B"), ("C", "D")) + [
        {"id": "u3", "role": "user", "content": "Q"}
    ]
    client = make_client([1050, 700])
    result = select_current_context(
        client, req_context, "asst-new", "Long response", limit_tokens=1000
    )
    ids = [m["id"] for m in result.selected]
    assert "asst-new" in ids
    assert result.selected[-1]["id"] == "asst-new"


def test_current_context_removes_oldest_when_over_limit():
    req_context = [
        {"id": "u1", "role": "user", "content": "Old question"},
        {"id": "a1", "role": "assistant", "content": "Old answer"},
        {"id": "u2", "role": "user", "content": "New question"},
    ]
    client = make_client([1100, 650])
    result = select_current_context(
        client, req_context, "asst-2", "New answer", limit_tokens=1000
    )
    ids = [m["id"] for m in result.selected]
    assert "u1" not in ids
    assert "a1" not in ids
    assert "u2" in ids
    assert "asst-2" in ids
    assert result.token_count <= 1000


def test_current_context_never_exceeds_limit():
    req_context = make_history(("A", "B"), ("C", "D"), ("E", "F"))
    req_context.append({"id": "u4", "role": "user", "content": "G"})
    client = make_client([1800, 1400, 1000])
    result = select_current_context(
        client, req_context, "asst-4", "H", limit_tokens=1000
    )
    assert result.token_count <= 1000


def test_current_context_end_id_is_assistant():
    req_context = [{"id": "u1", "role": "user", "content": "Q"}]
    client = make_client([400])
    result = select_current_context(
        client, req_context, "ASST-ID", "Answer", limit_tokens=1000
    )
    assert result.end_id == "ASST-ID"


# ════════════════════════════════════════════════════════════════════════════
# Integration: request → current pipeline
# ════════════════════════════════════════════════════════════════════════════

def test_full_pipeline_within_limit():
    """Both phases fit in limit; assistant response ends up as current context tail."""
    history = make_history(("Hi", "Hello"))
    # Phase 1: history + new user msg = 600 tokens
    # Phase 2: request context + assistant = 780 tokens
    client = make_client([600, 780])
    req = select_request_context(client, history, "u2", "Question", limit_tokens=1000)
    assert req.token_count == 600

    cur = select_current_context(client, req.selected, "a2", "Answer", limit_tokens=1000)
    assert cur.token_count == 780
    assert cur.end_id == "a2"
    assert cur.token_count <= 1000


def test_assistant_response_pushes_current_context_over_limit():
    """
    Scenario: request context fits, but adding the assistant response exceeds the limit.
    Oldest turns are removed from the current context phase.
    """
    req_context = make_history(("A", "B"), ("C", "D"))
    req_context.append({"id": "u3", "role": "user", "content": "E"})
    # Phase 2: req_context + assistant = 1100 > 1000; after removing oldest pair = 750
    client = make_client([1100, 750])
    result = select_current_context(
        client, req_context, "asst-3", "Long response", limit_tokens=1000
    )
    assert result.token_count == 750
    assert result.token_count <= 1000
    assert result.end_id == "asst-3"
    ids = [m["id"] for m in result.selected]
    assert "u1" not in ids
    assert "a1" not in ids


# ════════════════════════════════════════════════════════════════════════════
# Complete-turn invariant — current context must not contain partial turns
# ════════════════════════════════════════════════════════════════════════════

def test_current_context_oversized_turn_returns_empty():
    """
    Bug reproduction: user=23 + assistant=43 = 66 tokens, limit=50.
    The ENTIRE turn must be excluded (empty context), not just the user message.
    Previously this would leave the 43-token assistant message alone = broken turn.
    """
    # Single-message request context (just the user message, no history)
    req_context = [{"id": "u1", "role": "user", "content": "My name is Abdullah."}]
    # Initial count: user + assistant = 66 > 50
    # After removing all non-protected → only protected turn remains → 66 > 50
    # With allow_empty=True → empty context returned
    client = make_client([66, 66])
    result = select_current_context(
        client, req_context, "a1", "Long response about name", limit_tokens=50
    )
    assert result.token_count == 0
    assert result.message_count == 0
    assert result.start_id is None
    assert result.end_id is None
    assert result.selected == []


def test_current_context_complete_turn_fits():
    """
    Complete turn (user + assistant) fits within the limit → both messages remain.
    """
    req_context = [{"id": "u1", "role": "user", "content": "Hi"}]
    # user + assistant = 30 tokens ≤ 50
    client = make_client([30])
    result = select_current_context(
        client, req_context, "a1", "Hello!", limit_tokens=50
    )
    assert result.token_count == 30
    assert result.message_count == 2
    assert result.start_id == "u1"
    assert result.end_id == "a1"
    ids = [m["id"] for m in result.selected]
    assert "u1" in ids
    assert "a1" in ids


def test_current_context_no_orphaned_assistant():
    """
    Verify the assistant message is NEVER left alone when its paired user
    message has been removed.  With the fix, both are protected, so if the
    pair doesn't fit, the result is empty — not just the assistant.
    """
    req_context = [{"id": "u1", "role": "user", "content": "Q"}]
    # Total = 100 > 50; only protected remain → allow_empty → empty
    client = make_client([100, 100])
    result = select_current_context(
        client, req_context, "a1", "Very long answer", limit_tokens=50
    )
    # Must NOT contain only the assistant message
    assert not (result.message_count == 1 and result.end_id == "a1")
    # Must be empty
    assert result.message_count == 0
    assert result.token_count == 0


def test_request_after_oversized_turn_only_new_message():
    """
    After an oversized turn produced empty current context, the next request
    should contain only the new user message (since no previous complete turn
    fits within the limit).
    """
    # Full history: one previous turn that totals 66 tokens
    history = [
        {"id": "u1", "role": "user", "content": "My name is Abdullah."},
        {"id": "a1", "role": "assistant", "content": "Long response about name"},
    ]
    # Phase 1: history + new user = 70 > 50; after removing history pair = 5
    client = make_client([70, 5])
    result = select_request_context(
        client, history, "u2", "Hi", limit_tokens=50
    )
    assert result.token_count == 5
    assert result.message_count == 1
    assert result.start_id == "u2"
    assert result.end_id == "u2"
    ids = [m["id"] for m in result.selected]
    assert "u1" not in ids
    assert "a1" not in ids
    assert "u2" in ids


def test_current_context_with_history_oversized_newest_turn():
    """
    Multiple turns in history; the newest complete turn (user+assistant) exceeds
    the limit.  All turns, including the oversized protected newest turn, should
    result in an empty context.
    """
    req_context = make_history(("A", "B"), ("C", "D"))
    req_context.append({"id": "u3", "role": "user", "content": "E"})
    # Total = 200 > 50; after removing (A,B) pair = 170 > 50;
    # after removing (C,D) pair = 130 > 50;
    # only protected (u3, asst-3) remain = 130 > 50 → empty
    client = make_client([200, 170, 130, 130])
    result = select_current_context(
        client, req_context, "asst-3", "F", limit_tokens=50
    )
    assert result.token_count == 0
    assert result.message_count == 0
    assert result.selected == []


def test_bounded_context_allow_empty_returns_empty():
    """
    select_bounded_context with allow_empty=True returns empty BoundedContext
    when protected messages alone exceed the limit.
    """
    msgs = [{"id": "p1", "role": "user", "content": "protected"}]
    client = make_client([200, 200])
    result = select_bounded_context(
        client, msgs, protected_tail_ids={"p1"}, limit_tokens=50, allow_empty=True
    )
    assert result.token_count == 0
    assert result.message_count == 0
    assert result.start_id is None
    assert result.end_id is None
    assert result.selected == []


def test_bounded_context_allow_empty_false_still_raises():
    """
    select_bounded_context with allow_empty=False (default) still raises
    ValueError when protected messages exceed the limit.
    """
    msgs = [{"id": "p1", "role": "user", "content": "protected"}]
    client = make_client([200, 200])
    with pytest.raises(ValueError, match="exceed"):
        select_bounded_context(
            client, msgs, protected_tail_ids={"p1"}, limit_tokens=50
        )
