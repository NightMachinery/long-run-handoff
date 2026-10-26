# long-run-handoff

Keep long agent runs resumable when a coordinator is compacted, loses a child
report or hands over to another session. The skill preserves owner instructions,
a coordinator-owned org checklist, narrative state and durable worker results.
It tells a successor what to read and what to verify before resuming live work.
The default run directory, `~/.agents/runs/<project>/<run>/`, is shared across
agent harnesses and lives outside every repository. Its `USER-VERBATIM.md`,
`STATE.md` and other run files are never committed because they contain owner
instructions and live state.

## Install

```sh
npx skills add NightMachinery/long-run-handoff --global \
  --agent claude-code codex --skill long-run-handoff
```

For another Claude profile, set `CLAUDE_CONFIG_DIR` and install with
`--agent claude-code`. The [short guide](docs/long-run-handoff.md) explains the
file layout and companion skills. No custom shell setup is required.

Use the [tree manifest helper](skills/long-run-handoff/scripts/tree-manifest.py) to freeze and check reviewed source, input and binary hashes.

MIT licensed. See [LICENSE](LICENSE).
