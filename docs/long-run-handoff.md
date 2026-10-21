# Durable handoff guide

Load [the skill](../skills/long-run-handoff/SKILL.md) before substantial work
that may outlive one coordinator session. It is a recovery protocol, independent
of the backend used to run workers.

## File ownership

Keep the run directory outside public repositories. `TASK.md` records the
owner's exact instructions, `STATE.md` carries concise narrative and evidence,
and `plan.md` links design decisions and shared contracts. Worker briefs assign
absolute result and progress-note paths.

The coordinator alone writes `TASKS.org`. Put it at the main repository root
and verify its local ignore rule with `git check-ignore TASKS.org`; use the run
directory when there is no repository. Worker status messages do not give workers
checklist ownership. On handoff, name the new writer in state before it resumes.

A project-scoped Compact Instructions block points back to the durable files.
The copy-ready block is in the skill. Substitute the run's actual absolute paths.
Do not insert it into generated or global agent instructions.

## Use existing skills for execution

The handoff protocol names companions by their installed skill names. It does
not duplicate launch flags, account selection, compaction, waiting or keepalive
procedures. Each companion can be absent; the skill explains the fallback.

Useful standalone companions include:

- [delegate](https://github.com/NightMachinery/delegate) for worker selection and
  its `paseo-compact` and `paseo-cache-warmer` entrypoints.
- [tmux-subagents](https://github.com/NightMachinery/tmux-subagents) for tmux workers.
- [event-driven-waiting](https://github.com/NightMachinery/event-driven-waiting)
  for a completion notification armed alongside the launch.
- [quota-management](https://github.com/NightMachinery/quota-management) for
  watching the main coordinator's allowance and deciding when to hand off.
- `paseo` and `paseo-handoff`, when installed, for operating a successor in Paseo.
- `event-driven-coordination`, when installed, for fleet checkpoints, event-based
  hand-backs and the hourly recovery ping.

No skill grants permission to move data, change account or launch another agent.
After any notification or coordinator change, inspect actual state and durable
outputs before marking a task done or relaunching work.
