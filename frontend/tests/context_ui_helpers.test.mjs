/**
 * tests/context_ui_helpers.test.mjs
 *
 * Regression tests for the two pure helper functions that drive the context
 * window UI: `messagesInRange` and the `isOutOfCtx` / `contextResolved` logic.
 *
 * These are plain Node ESM tests — no framework required.
 * Run with:  node --test tests/context_ui_helpers.test.mjs
 * (Node ≥ 18.x has a built-in test runner.)
 *
 * What is covered
 * ───────────────
 * Group A – messagesInRange
 *   A1  All messages when start=null, end=last (no truncation)
 *   A2  Slice between start and end (truncated head)
 *   A3  Returns [] when end_id is null
 *   A4  Returns [] when end_id is not found in messages (optimistic/unpatched)
 *   A5  Falls back to slice from index 0 when start_id is missing from messages
 *
 * Group B – isOutOfCtx / contextResolved
 *   B1  No messages labelled before context resolves (contextResolved=false)
 *   B2  No messages labelled when item has no id (pre-patch optimistic message)
 *   B3  Messages inside window are not labelled (id is in the Set)
 *   B4  Messages outside window are labelled (id is NOT in the Set)
 *   B5  All messages labelled correctly in a 4-message conversation where
 *       only the last 2 are in context (reproduces the original bug scenario)
 *
 * Group C – requestMessageCount / currentMessageCount fallback
 *   C1  Falls back to message_count from ContextWindowDetail when array is empty
 *   C2  Uses array length when IDs have resolved
 *
 * Group D – handleSubmit ID-patch logic (unit test of the patching transform)
 *   D1  Last user message (no id) gets patched with userMsgId
 *   D2  Non-last messages and already-ID'd messages are not touched
 *   D3  New assistant message is appended with assistantMsgId
 *   D4  No crash when context is absent (userMsgId / assistantMsgId are undefined)
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

// ── Pure helpers copied from App.tsx ────────────────────────────────────────
// Keep these in sync with the App.tsx implementations.

/** @param {Array} messages @param {string|null} start_id @param {string|null} end_id */
function messagesInRange(messages, start_id, end_id) {
  if (!end_id) return [];
  const endIdx = messages.findIndex((m) => m.id === end_id);
  if (endIdx === -1) return [];
  if (!start_id) return messages.slice(0, endIdx + 1);
  const startIdx = messages.findIndex((m) => m.id === start_id);
  if (startIdx === -1) return messages.slice(0, endIdx + 1);
  return messages.slice(startIdx, endIdx + 1);
}

/**
 * Simulate the ID-patch + append transform from handleSubmit.
 * @param {Array} prev  Current messages state
 * @param {string|undefined} userMsgId
 * @param {string|undefined} assistantMsgId
 * @param {string} assistantContent
 */
function patchAndAppend(prev, userMsgId, assistantMsgId, assistantContent) {
  const patched = prev.map((m, i) =>
    i === prev.length - 1 && m.role === 'user' && !m.id
      ? { ...m, id: userMsgId }
      : m
  );
  return [...patched, { role: 'assistant', content: assistantContent, id: assistantMsgId }];
}

/**
 * Compute isOutOfCtx for a message given the resolved context state.
 * @param {{id?: string}} item
 * @param {boolean} contextResolved
 * @param {Set<string>} currentContextIdSet
 */
function isOutOfCtx(item, contextResolved, currentContextIdSet) {
  return contextResolved && !!item.id && !currentContextIdSet.has(item.id);
}

// ── Fixtures ─────────────────────────────────────────────────────────────────

function makeMsg(id, role, content = 'x') {
  return { id, role, content };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('A – messagesInRange', () => {
  const msgs = [
    makeMsg('u1', 'user', 'Q1'),
    makeMsg('a1', 'assistant', 'A1'),
    makeMsg('u2', 'user', 'Q2'),
    makeMsg('a2', 'assistant', 'A2'),
  ];

  test('A1: start=null, end=last → all messages returned', () => {
    const result = messagesInRange(msgs, null, 'a2');
    assert.deepEqual(result.map((m) => m.id), ['u1', 'a1', 'u2', 'a2']);
  });

  test('A2: start=u2, end=a2 → only last 2 messages', () => {
    const result = messagesInRange(msgs, 'u2', 'a2');
    assert.deepEqual(result.map((m) => m.id), ['u2', 'a2']);
  });

  test('A3: end_id=null → empty array', () => {
    assert.deepEqual(messagesInRange(msgs, null, null), []);
  });

  test('A4: end_id not found (optimistic/unpatched) → empty array', () => {
    // Reproduces the pre-fix bug: optimistic message has no id so
    // 'some-real-uuid' is never found → messagesInRange returned []
    assert.deepEqual(messagesInRange(msgs, null, 'some-real-uuid'), []);
  });

  test('A5: start_id missing → falls back to slice from 0 up to end', () => {
    const result = messagesInRange(msgs, 'nonexistent-start', 'a2');
    assert.deepEqual(result.map((m) => m.id), ['u1', 'a1', 'u2', 'a2']);
  });

  test('A6: start=u2, end=u2 → single message', () => {
    const result = messagesInRange(msgs, 'u2', 'u2');
    assert.deepEqual(result.map((m) => m.id), ['u2']);
  });

  test('A7: empty messages array → empty result', () => {
    assert.deepEqual(messagesInRange([], null, 'u1'), []);
  });
});

describe('B – isOutOfCtx / contextResolved guard', () => {
  const inCtxIds = new Set(['u2', 'a2']);

  test('B1: contextResolved=false → no message is labelled out-of-context', () => {
    const item = makeMsg('u1', 'user');
    assert.equal(isOutOfCtx(item, false, inCtxIds), false);
  });

  test('B2: item has no id (pre-patch optimistic) → never labelled', () => {
    // Before the handleSubmit patch, the optimistic user message has id=undefined.
    // It must NEVER get the ↑ history label.
    const item = { role: 'user', content: 'hello' }; // no id
    assert.equal(isOutOfCtx(item, true, inCtxIds), false);
  });

  test('B3: message id IS in context set → not labelled', () => {
    assert.equal(isOutOfCtx(makeMsg('u2', 'user'), true, inCtxIds), false);
    assert.equal(isOutOfCtx(makeMsg('a2', 'assistant'), true, inCtxIds), false);
  });

  test('B4: message id NOT in context set → labelled out-of-context', () => {
    assert.equal(isOutOfCtx(makeMsg('u1', 'user'), true, inCtxIds), true);
    assert.equal(isOutOfCtx(makeMsg('a1', 'assistant'), true, inCtxIds), true);
  });

  test('B5: 4-message conversation, last 2 in context — correct per-message labelling', () => {
    // This is the exact scenario from the bug report:
    // Request 2 included prior conversation context, but all 4 messages were labelled ↑ history.
    // After the fix: u1/a1 are out-of-context, u2/a2 are in-context.
    const allMsgs = [
      makeMsg('u1', 'user', 'Q1'),
      makeMsg('a1', 'assistant', 'A1'),
      makeMsg('u2', 'user', 'Q2'),
      makeMsg('a2', 'assistant', 'A2'),
    ];

    // Current context window: only u2, a2 (truncated after adding assistant)
    const currentContextMsgs = messagesInRange(allMsgs, 'u2', 'a2');
    const contextIdSet = new Set(currentContextMsgs.map((m) => m.id));
    const contextResolved = currentContextMsgs.length > 0;

    assert.equal(contextResolved, true, 'context should resolve');
    assert.equal(contextIdSet.size, 2);

    const labels = allMsgs.map((m) => ({
      id: m.id,
      outOfCtx: isOutOfCtx(m, contextResolved, contextIdSet),
    }));

    assert.deepEqual(labels, [
      { id: 'u1', outOfCtx: true },
      { id: 'a1', outOfCtx: true },
      { id: 'u2', outOfCtx: false },
      { id: 'a2', outOfCtx: false },
    ]);
  });
});

describe('C – requestMessageCount / currentMessageCount fallback', () => {
  function computeMessageCount(arrayLen, apiCount) {
    // Mirrors the derived variable logic in App.tsx
    return arrayLen > 0 ? arrayLen : apiCount;
  }

  test('C1: array empty (IDs unresolved) → falls back to API message_count', () => {
    assert.equal(computeMessageCount(0, 3), 3);
    assert.equal(computeMessageCount(0, 1), 1);
  });

  test('C2: array non-empty (IDs resolved) → uses array length', () => {
    assert.equal(computeMessageCount(4, 99), 4);
    assert.equal(computeMessageCount(2, 0), 2);
  });

  test('C3: both zero → 0 (no context yet)', () => {
    assert.equal(computeMessageCount(0, 0), 0);
  });
});

describe('D – handleSubmit ID-patch transform', () => {
  test('D1: last user message (no id) is patched with userMsgId', () => {
    const prev = [
      makeMsg('u1', 'user', 'First'),
      makeMsg('a1', 'assistant', 'First reply'),
      { role: 'user', content: 'Second', id: undefined }, // optimistic, no id
    ];
    const result = patchAndAppend(prev, 'real-u2', 'real-a2', 'Second reply');
    assert.equal(result[2].id, 'real-u2');
    assert.equal(result[2].role, 'user');
    assert.equal(result[2].content, 'Second');
  });

  test('D2: earlier messages and already-ID\'d messages are not touched', () => {
    const prev = [
      makeMsg('u1', 'user'),
      makeMsg('a1', 'assistant'),
      { role: 'user', content: 'Q2' }, // optimistic
    ];
    const result = patchAndAppend(prev, 'u2', 'a2', 'A2');
    assert.equal(result[0].id, 'u1');
    assert.equal(result[1].id, 'a1');
  });

  test('D3: assistant message is appended with assistantMsgId', () => {
    const prev = [
      makeMsg('u1', 'user'),
      { role: 'user', content: 'Q2' },
    ];
    const result = patchAndAppend(prev, 'u2', 'a2', 'My answer');
    assert.equal(result.length, 3);
    assert.equal(result[2].role, 'assistant');
    assert.equal(result[2].content, 'My answer');
    assert.equal(result[2].id, 'a2');
  });

  test('D4: graceful when context absent (ids are undefined)', () => {
    const prev = [{ role: 'user', content: 'Hi' }];
    const result = patchAndAppend(prev, undefined, undefined, 'Hello');
    // Should not throw; ids will be undefined (not null)
    assert.equal(result[0].id, undefined);
    assert.equal(result[1].id, undefined);
    assert.equal(result[1].role, 'assistant');
  });

  test('D5: request context message count matches patched window', () => {
    // After patching, messagesInRange should find 4 messages for a 2-turn conversation
    const dbMsgs = [makeMsg('u1', 'user'), makeMsg('a1', 'assistant')];
    const prev = [...dbMsgs, { role: 'user', content: 'Q2' }]; // optimistic u2
    const afterPatch = patchAndAppend(prev, 'u2', 'a2', 'A2');

    // Request context: start=u1, end=u2 (user message)
    const requestMsgs = messagesInRange(afterPatch, 'u1', 'u2');
    assert.equal(requestMsgs.length, 3, 'request context: u1, a1, u2');

    // Current context: start=u1, end=a2 (assistant message)
    const currentMsgs = messagesInRange(afterPatch, 'u1', 'a2');
    assert.equal(currentMsgs.length, 4, 'current context: u1, a1, u2, a2');
  });
});
