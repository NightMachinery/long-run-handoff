# Durable handoff guide

Load [the skill](../skills/long-run-handoff/SKILL.md) before substantial work
that may outlive one coordinator session. It is a recovery protocol, independent
of the backend used to run workers.

## File ownership

Use `~/.agents/runs/<project>/<run>/` by default, outside every repository.
Claude Code, Codex and other agents share this neutral location so successors
from another harness resume the same files. It contains `USER-VERBATIM.md`, `STATE.md`,
`plan.md`, `briefs/`, `results/` and `logs/`, never committed because they hold the
owner's words, account mappings and live state. If an in-repository run directory
is unavoidable, exclude it locally. Worker briefs assign absolute result and
progress-note paths.

The coordinator alone writes `TASKS.org`. Put it at the main repository root
and ignore it through `.git/info/exclude` or global excludes without a committed
ignore rule. Verify with `git check-ignore -v TASKS.org`; use the run directory
when there is no repository. Worker status messages do not give workers
checklist ownership. On handoff, name the new writer in state before it resumes.

A project-scoped Compact Instructions block points back to the durable files.
The copy-ready block is in the skill. A committed pointer may use a `~/` run path,
never an absolute home path, and must contain no private content. Do not insert
it into generated or global agent instructions.

## Reviewed output manifests

Before reusing reviewed outputs, snapshot the directories holding their source,
inputs and binaries. Keep manifests with the review receipts, outside those
directories, and check them before trusting receipts copied later:

```sh
python3 skills/long-run-handoff/scripts/tree-manifest.py snapshot output -o milestone.json
python3 skills/long-run-handoff/scripts/tree-manifest.py check output milestone.json
```

The [helper](../skills/long-run-handoff/scripts/tree-manifest.py) needs only Python 3.
Without `-o`, it creates the sibling `output.manifest.json`; it refuses overwrites
and output paths inside the inspected tree. `.git` and `__pycache__` are excluded.
Add `--exclude '*.tmp' 'logs/**'`: slashless globs match any path component; others
match relative POSIX paths (also with a trailing `/` for pruning directories).
`check` reuses the saved excludes and groups differences by top-level folder.

The flat JSON records file SHA-256, size and executable bits, and symlink targets
without following them. Its root hashes sorted canonical JSON entry lines (sorted
keys, compact separators, ASCII escaping, UTF-8 and a newline per entry). Times and
empty directories are ignored; relocated identical trees match. Keep inputs
quiescent while hashing, since this is not an atomic filesystem snapshot.
Unreadable or special files fail instead of being skipped. Exit codes are `0`
for a saved snapshot/identical check, `1` for differences and `2` for usage or
IO/format errors. Run tests from the repository root:

```sh
python3 -B -m unittest discover -s skills/long-run-handoff/scripts -p 'test_tree_manifest.py'
```

## Use existing skills for execution

The handoff protocol names companions by their installed skill names. It does
not duplicate launch flags, account selection, compaction, waiting or keepalive
procedures. Each companion can be absent; the skill explains the fallback.

Useful standalone companions include:

- [delegate](https://github.com/NightMachinery/delegate) for worker selection and
  its `paseo-compact` and `paseo-cache-warmer` entrypoints.
- [tmux-subagents](https://github.com/NightMachinery/tmux-subagents) for tmux workers.
- [event-driven-agents](https://github.com/NightMachinery/event-driven-agents)
  for completion notifications and its optional fleet-policy reference.
- [quota-management](https://github.com/NightMachinery/quota-management) for
  watching the main coordinator's allowance and deciding when to hand off.
- `paseo` and `paseo-handoff`, when installed, for operating a successor in Paseo.

No skill grants permission to move data, change account or launch another agent.
After any notification or coordinator change, inspect actual state and durable
outputs before marking a task done or relaunching work.
