# AI Collaboration Protocol

Status: active coordination record  
Date: 2026-07-08

This document is the shared operating protocol for Codex, Claude Code, and any
other AI or human contributor working on CultivateAgent at the same time. Its
purpose is to prevent conflicting edits, silent rollback, duplicate work, and
ambiguous handoffs.

## 1. Why This Exists

The project now has concurrent AI work streams. Session 2 from Claude added
operator extraction, evidence synthesis, piBO priors, and a live DeepSeek run.
Session 3 from Codex patched ontology normalization gaps exposed by that run.
Future work needs a lightweight coordination layer so agents can keep moving
without overwriting each other.

This protocol follows three documentation and collaboration references:

- [GitHub pull request documentation](https://docs.github.com/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests):
  use reviewable change proposals and discussion points instead of opaque edits.
- [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):
  use structured commit subjects so the log communicates intent.
- [Google developer documentation style guide](https://developers.google.com/style):
  keep instructions clear, task-oriented, and stable for developers.

## 2. Start-Of-Session Checklist

Every AI agent must do this before editing:

- [ ] Read `README.md`.
- [ ] Read `docs/PROJECT_WORKFLOW.md` or `docs/PROJECT_WORKFLOW_ZH.md`.
- [ ] Read `docs/SESSION_LOG.md` from the newest session entry backward.
- [ ] Run `git fetch --all --prune`.
- [ ] Run `git status --short --branch`.
- [ ] Run `git log --oneline --decorate -8`.
- [ ] Identify untracked files and treat them as someone else's work unless
  there is direct evidence they are yours.
- [ ] Decide the most valuable next task and record the decision in
  `docs/SESSION_LOG.md` before or with the implementation commit.

If another agent has landed new work, continue from that state. Do not restore an
older branch's assumptions over newer `main` content.

## 3. Ownership And Conflict Zones

High-conflict files require extra care:

| Area | Files | Rule |
|---|---|---|
| Extraction core | `cultivate_agent/extract/*`, `cultivate_agent/evidence/*` | Read latest Session Log before editing; avoid parallel rewrites. |
| Optimization core | `cultivate_agent/optimize/*` | Do not change acquisition or priors without tests and documentation. |
| Ontology | `config/ontology/*.yaml` | Additive changes are preferred; document whether entries are normalization hooks or wet-lab-approved variables. |
| Project control docs | `README.md`, `docs/PROJECT_WORKFLOW*.md`, `docs/SESSION_LOG.md` | Must be updated with every material change. |
| Human review data | `data/literature/bovine_human_review_queue.tsv` | AI may prepare fields but must not overwrite human notes. |
| Untracked files | Any `??` path in `git status` | Do not delete, rename, or commit unless you created it or can prove ownership. |

## 4. Commit Message Protocol

Use commit messages as coordination signals. Prefer:

```text
type(scope): short imperative summary

Why:
- One or two bullets explaining the decision.

Coordination:
- State what you deliberately did not touch.
- Mention known untracked or external work if relevant.
```

Allowed `type` values:

- `feat`: new capability
- `fix`: bug fix
- `docs`: documentation-only change
- `test`: tests only
- `refactor`: behavior-preserving code movement
- `data`: curated data or ontology updates
- `chore`: tooling or maintenance

Examples:

```text
data(ontology): normalize live-run medium aliases

Why:
- DeepSeek live run surfaced SFB, Beefy-R, GFE, APE, and copper ions.
- Canonicalization is required before evidence pooling.

Coordination:
- Did not edit operator extraction or evidence synthesis.
- Left untracked scripts untouched.
```

```text
docs(coordination): add AI collaboration protocol

Why:
- Codex and Claude are now working concurrently.
- Shared start-of-session and commit-message rules reduce rollback risk.

Coordination:
- Documentation-only change.
```

## 5. Handoff Protocol

At the end of a work session:

- [ ] Run the relevant tests. For code changes, run `.venv/bin/python -m pytest -q`.
- [ ] Run `.venv/bin/python -m cultivate_agent.cli smoke` unless the change is
  documentation-only.
- [ ] Run `.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6`
  unless the change is documentation-only.
- [ ] Update `docs/SESSION_LOG.md` with:
  - decision,
  - files changed,
  - tests run,
  - what was deliberately not done,
  - next 3 steps.
- [ ] Update `README.md` and both project workflow manuals when behavior,
  process, or project status changes.
- [ ] Commit only your owned changes.
- [ ] Push.
- [ ] Leave any untracked files owned by another agent untouched.

## 6. Current Coordination Notes

- `main` is the authoritative branch as of 2026-07-08.
- The current highest-value technical lane remains S3/S4: reliable full-text
  extraction, evidence synthesis, ontology-backed normalization, and human
  adjudication before any wet-lab design packet.
- Claude's operator extraction and evidence synthesis work should be treated as
  the current extraction baseline.
- Codex's ontology-normalization patch should be treated as a normalization
  support layer, not as wet-lab approval of those components.
- At the time this protocol was added, `scripts/ingest_pdfs.py` and
  `scripts/run_evidence_parallel.py` were untracked local files. They should not
  be removed or committed unless their author confirms ownership or they are
  intentionally adopted in a later documented commit.
