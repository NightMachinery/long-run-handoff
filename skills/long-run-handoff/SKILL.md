---
name: long-run-handoff
description: Keep long agent runs resumable across compaction, lost child reports and coordinator replacement using durable instructions, narrative state, an org checklist and assigned result files.
---

# Long-run handoff

Prepare for three discontinuities: compaction loses context, a lost parent can
lose child reports, and a replacement coordinator must inherit live work.
Files preserve decisions; verify the world before resuming them.

## Before substantial work

Create a private shared run directory with `TASK.md`, `STATE.md`, `plan.md`,
`briefs/`, `results/` and `logs/`. Keep machine and account mappings there.

- `TASK.md` preserves the owner's task verbatim. Append each later instruction
  verbatim under a dated owner entry **before acting**, then record what was done.
- `plan.md` holds the design and links to shared contracts. Do not reopen settled
  decisions merely because their reasoning left the context window.
- `TASKS.org` is the checklist, at the main repository root and locally gitignored:
  verify with `git check-ignore TASKS.org`. Without a repository, put it in the
  run directory. The coordinator is its only writer; children report status.
  Follow an installed org-mode skill when present. Use TODO keywords and org
  `DEADLINE:` planning lines, replacing the timestamp template with a real date:

  ```org
  #+TODO: TODO NEXT WAITING BLOCKED | DONE CANCELED
  * TODO Review the worker result
  DEADLINE: <YYYY-MM-DD Day HH:MM>
  ```

`STATE.md` links to that checklist and keeps the narrative, not a second task list.
Take timestamps from `date`, name the clock/timezone, and record any clock drift.

## STATE.md, in order

- Updated time and current coordinator identity, predecessor and takeover time.
- Absolute pointers to TASKS.org, handoff/design briefs, contracts and logs.
- Owner requirements and constraints, including dated changes and who received them.
- Definitions marked owner-required, provisional or validated.
- Decisions and rejected approaches, each with its reason.
- Active workers/jobs: backend identifiers, ownership, status, evidence/output
  paths, result files and any resource expiry. Record actual state privately.
- Repositories: paths, branches, commits and whose uncommitted edits must be preserved.
- Completed work with evidence; blockers and ordered immediate next actions.
- Open owner questions and the provisional assumptions used within authorization.
- A newest-first progress log: one timestamped milestone per entry, with a commit,
  log or result path. Keep raw results in linked artifacts, not in the narrative.

Add this shortened pointer to a project-scoped `CLAUDE.md` or equivalent recovery
instructions. Substitute absolute paths; do not edit generated/global instructions.

```markdown
## Compact Instructions
1. Read /abs/run/TASK.md, this project instruction file, /abs/run/STATE.md,
   /abs/run/plan.md and the TASKS.org linked from STATE.md.
2. Verify repositories, live workers/jobs and expected outputs before acting.
3. Resume the next unfinished TASKS.org item; do not relaunch live work or reopen decisions.
4. Keep TASKS.org and STATE.md current; record unverifiable claims as uncertainties.
```

## Every worker brief

Assign an absolute result path and progress-note path from the first launch.
Require a result even if the worker also sends a message. Its first line is
`<ASSIGNMENT> DONE` or `<ASSIGNMENT> PARTIAL`, followed by artifacts, validation
and remaining work. Update the progress note after milestones so a stopped
worker can resume. State: "Runs unattended; this brief settles design questions."
That instruction does not expand permission; report unresolved boundaries as PARTIAL.

## After compaction or replacement

Read TASK.md, project recovery instructions, STATE.md, plan.md and linked TASKS.org.
Verify repository status/history, live worker/job state and output files using the
actual backend. Resume the first unfinished item; mark unverifiable claims uncertain.
A registry or remembered launch is not proof that work is running or finished.

## Coordinator replacement

1. Write a cover letter beside STATE.md, not a copy of it: reason, absolute read
   order, inherited live work with ownership/result paths, ordered next actions,
   and binding rules. Append later instructions as dated addenda.
2. Tell **every running child** to write its assigned result file, even if its
   original brief required only messaging. Checkpoint your own unfinished work.
3. Launch an authorized successor through the selected backend, give it the brief
   path, and verify it started and can read the required files.
4. Update STATE.md with the successor, predecessor and takeover time; transfer
   sole checklist ownership. The old coordinator stops decisions and launches.
5. Keep the old coordinator on relay duty for children only it can receive:
   copy their reports **verbatim** to assigned result files, without overwriting
   a child's existing report, and record each delivery in the progress log.

## Companion skills

- `delegate`: worker selection, accounts and execution backend.
- `paseo`: successor launch inside Paseo; `paseo-handoff`: its handoff procedure.
- `tmux-subagents`: tmux worker launch and resume mechanics.
- `paseo-compact`: compaction at a natural endpoint.
- `paseo-cache-warmer`: keepalive while waiting.
- `quota-management`: watch the main coordinator's quota and hand off when it says to.
- `event-driven-waiting`: arm the completion notification alongside each launch.
- `event-driven-coordination`: supervise many workers for hours with event-based
  hand-backs, checkpoints and the hourly recovery ping.

If a companion is absent, report it and use a verified backend equivalent;
if none is available, checkpoint rather than invent commands or lose ownership.

## Failure modes prevented

Duplicate launches after compaction; lost mid-run instructions; finished work
reported only to a vanished parent; missed events from relative waiter targets;
conflicting checklist writers; an unverified handoff; and repeated work caused
by reopening a settled decision.
