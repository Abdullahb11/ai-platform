"""
context_selector.py — Application Context Window Selection

Implements deterministic oldest-first truncation to fit a list of messages
within the configured APP_CONTEXT_WINDOW_TOKENS limit.

There are TWO selection phases in the chat lifecycle:

  Phase 1 — REQUEST CONTEXT (before Gemini call)
    Input:  DB conversation history + new user message
    Output: messages that Gemini will receive, token count <= limit

  Phase 2 — CURRENT CONTEXT (after Gemini call)
    Input:  selected request context + assistant response
    Output: post-response active context, token count <= limit

Both phases reuse the same core function: `select_bounded_context`.

This module has NO I/O — it receives data and returns results.
The GeminiClient is the only external dependency (used only for count_tokens).
"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.clients.gemini_client import GeminiClient


@dataclass
class BoundedContext:
    """
    The result of a single bounded-context selection pass.

    selected     — ordered list of message dicts (oldest → newest)
    token_count  — authoritative Gemini token count for selected
    start_id     — id of the first selected message (None if selected is empty)
    end_id       — id of the last selected message (None if selected is empty)
    message_count — len(selected)
    """
    selected: list[dict]
    token_count: int
    start_id: str | None
    end_id: str | None
    message_count: int


def select_bounded_context(
    gemini_client: "GeminiClient",
    messages: list[dict],
    protected_tail_ids: set[str],
    limit_tokens: int,
    allow_empty: bool = False,
) -> BoundedContext:
    """
    Core selection primitive.

    Given an ordered list of message dicts (oldest → newest), removes the oldest
    complete user/assistant pairs until the token count fits within limit_tokens.
    Messages whose id is in `protected_tail_ids` are NEVER removed.

    Args:
        gemini_client:      Used for count_tokens and build_contents only.
        messages:           Full candidate list, ordered oldest → newest.
                            Each dict must have "id", "role", "content".
        protected_tail_ids: Set of message ids that must not be removed.
                            Typically {new_user_message_id} for request context
                            and {assistant_message_id} for current context.
        limit_tokens:       Maximum allowed token count.
        allow_empty:        If True and the protected messages alone exceed the
                            limit, return an empty BoundedContext instead of
                            raising ValueError.  Used by select_current_context
                            where an oversized turn simply means "no active
                            context" rather than a user error.

    Returns:
        BoundedContext with the selected slice, its token count, and boundary ids.

    Raises:
        ValueError:   If protected messages alone exceed limit_tokens
                      (only when allow_empty is False).
        RuntimeError: If the Gemini count_tokens API call fails.
    """
    candidate = list(messages)  # never mutate the caller's list

    # ── Initial count ──────────────────────────────────────────────────────────
    contents = gemini_client.build_contents(candidate)
    token_count = gemini_client.count_tokens(contents)

    if token_count <= limit_tokens:
        return BoundedContext(
            selected=candidate,
            token_count=token_count,
            start_id=candidate[0]["id"] if candidate else None,
            end_id=candidate[-1]["id"] if candidate else None,
            message_count=len(candidate),
        )

    # ── Truncate oldest-first, preserving protected_tail_ids ─────────────────
    while True:
        # Find the oldest removable message index (not in protected_tail_ids)
        removable_start = None
        for i, msg in enumerate(candidate):
            if msg["id"] not in protected_tail_ids:
                removable_start = i
                break

        if removable_start is None:
            # Nothing left to remove — protected messages alone exceed the limit
            if allow_empty:
                return BoundedContext(
                    selected=[],
                    token_count=0,
                    start_id=None,
                    end_id=None,
                    message_count=0,
                )
            protected_contents = gemini_client.build_contents(candidate)
            protected_count = gemini_client.count_tokens(protected_contents)
            raise ValueError(
                f"Protected messages ({protected_count} tokens) exceed the "
                f"configured context window limit ({limit_tokens} tokens). "
                "Please send a shorter message."
            )

        # Prefer removing a complete user/assistant pair
        if (
            removable_start + 1 < len(candidate)
            and candidate[removable_start]["role"] == "user"
            and candidate[removable_start + 1]["role"] == "assistant"
            and candidate[removable_start + 1]["id"] not in protected_tail_ids
        ):
            candidate = candidate[:removable_start] + candidate[removable_start + 2:]
        else:
            candidate = candidate[:removable_start] + candidate[removable_start + 1:]

        contents = gemini_client.build_contents(candidate)
        token_count = gemini_client.count_tokens(contents)

        if token_count <= limit_tokens:
            return BoundedContext(
                selected=candidate,
                token_count=token_count,
                start_id=candidate[0]["id"] if candidate else None,
                end_id=candidate[-1]["id"] if candidate else None,
                message_count=len(candidate),
            )


# ── Phase convenience wrappers ─────────────────────────────────────────────────

def select_request_context(
    gemini_client: "GeminiClient",
    history: list[dict],
    new_message_id: str,
    new_message: str,
    limit_tokens: int,
) -> BoundedContext:
    """
    Phase 1 — build the request context Gemini will receive.

    history + new user message → BoundedContext <= limit_tokens

    The new user message is ALWAYS the last item and is protected from removal.

    Raises:
        ValueError:   If the new user message alone exceeds limit_tokens.
        RuntimeError: If count_tokens fails.
    """
    new_user_entry = {"id": new_message_id, "role": "user", "content": new_message}
    candidate = history + [new_user_entry]
    return select_bounded_context(
        gemini_client=gemini_client,
        messages=candidate,
        protected_tail_ids={new_message_id},
        limit_tokens=limit_tokens,
    )


def select_current_context(
    gemini_client: "GeminiClient",
    request_context: list[dict],
    assistant_message_id: str,
    assistant_message: str,
    limit_tokens: int,
) -> BoundedContext:
    """
    Phase 2 — build the post-response current context.

    request context + assistant response → BoundedContext <= limit_tokens

    The latest complete turn (the user message that triggered this response +
    the assistant response) is protected as a unit.  If the complete turn alone
    exceeds the limit, an empty BoundedContext is returned — no partial turns
    are ever kept in the active context.

    Raises:
        RuntimeError: If count_tokens fails.
    """
    assistant_entry = {
        "id": assistant_message_id,
        "role": "assistant",
        "content": assistant_message,
    }
    candidate = request_context + [assistant_entry]

    # Protect the entire latest turn: the user message (last item in
    # request_context) + the assistant response.  This ensures truncation
    # can never leave an orphaned assistant message without its user message.
    protected = {assistant_message_id}
    if request_context:
        last_request_msg = request_context[-1]
        if last_request_msg["role"] == "user" and last_request_msg.get("id"):
            protected.add(last_request_msg["id"])

    return select_bounded_context(
        gemini_client=gemini_client,
        messages=candidate,
        protected_tail_ids=protected,
        limit_tokens=limit_tokens,
        allow_empty=True,
    )
