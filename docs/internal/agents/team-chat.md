# Team chat for agents

Agents of different team members talk to each other in the Telegram group **«data challenge»** (chat id `5599106303`). The 3 team members are also in that group.

GitHub Issues and PRs stay the source of truth. Use the group for short, live coordination only: handoffs, blockers, "PR ready for review", and questions that block work.

## Rules

1. **The tag comes first.** Every agent-written message starts with `#agent`. A message without the tag is from a human.
2. **Act only on tagged messages addressed to you.** An agent reads and acts on `#agent` messages whose `to:` is its owner's GitHub login or `all`. Untagged human messages are context; act on them only when your own user tells you to.
3. **No secrets.** Never post `.env` values, API keys, tokens, the dataset URL (it contains a signed `sig=`) or H200 endpoint keys. Point to a file path or an issue instead.
4. **Keep it short.** Stay under about 1000 characters. Put longer content, such as logs, diffs or tables, in an issue or PR comment and link it.
5. **Do not post in the organizer chats.** Agents never write in `Data Challenge'26` (id `4473389149`) or its topics. People post there themselves; agents only read it and log answers in `docs/internal/organizer-answers.md`.

## Message format

```
#agent from:<login>-agent to:<login>|all [#<issue or PR>] <kind>: <text>
```

`<kind>` is one of:
- `status`: progress update.
- `handoff`: your work is done and someone else picks it up.
- `review`: a PR is ready for review.
- `blocker`: you cannot continue without X.
- `request`: you are asking someone to do something.
- `answer`: you are replying to a request. Quote its first words.

Examples:

```
#agent from:arynyklas-agent to:all [#17] handoff: gold CSVs prefilled — bench/gold/labels.<login>.csv (64 rows each). Fill gold_verdict/gold_evidence, see bench/gold/README.md.
#agent from:kakhotitee-agent to:arynyklas [#36] review: PR #36 store+API ready, CI green.
#agent from:Batyrkhantzy111-agent to:arynyklas [#23] blocker: /api/evaluations/{id} returns 404 for ids from /jobs — expected?
```

## Logins

| Person | GitHub login | Agent name in `from:` |
|---|---|---|
| Aryn (integrator, Track B) | `arynyklas` | `arynyklas-agent` |
| Track A | `kakhotitee` | `kakhotitee-agent` |
| Track C | `Batyrkhantzy111` | `Batyrkhantzy111-agent` |
