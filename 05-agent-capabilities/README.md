# Module 5 — Agent Extension Pack

[Module source](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/tree/main/05-agent-capabilities) ·
[Companion article](https://aishippingblog.com/p/coding-agent-building-blocks-reusable)

This module has no graded homework — the module deliverable here is carried
into the [final project](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp/tree/main/project)
instead. It extends the Card Catalog app built in Modules 2–3
(`../03-test-containerize-and-deploy-an-ai-assisted-app/`) with a scoped set
of agent capabilities.

Start here: [`docs/agent-extension-pack.md`](docs/agent-extension-pack.md)
maps each of the module's required components to the file that satisfies it.
[`docs/permissions.md`](docs/permissions.md) covers what each component can
and can't do. [`docs/demo.md`](docs/demo.md) walks through the module's
six-step demo script.

```
05-agent-capabilities/
├── docs/
│   ├── agent-extension-pack.md   # requirement → file map, start here
│   ├── permissions.md            # security/permission boundaries
│   └── demo.md                   # six-step demo walkthrough
├── mcp-server/                   # card-catalog-ops MCP server (source of truth)
│   ├── server.py
│   ├── pyproject.toml
│   └── README.md
└── plugins/
    └── ai-devtools-agent-pack/   # generalized, installable packaging
        ├── .claude-plugin/plugin.json
        ├── skills/debug-ci-failure/
        ├── agents/api-reviewer.md
        └── hooks/

../03-test-containerize-and-deploy-an-ai-assisted-app/   # where the "live" config actually lives
├── AGENTS.md          # updated: new "Agent Capabilities Quick Reference" section
├── CLAUDE.md           # new: @AGENTS.md import
├── .mcp.json           # new: registers card-catalog-ops
└── .claude/
    ├── settings.json              # new: wires the PreToolUse hook
    ├── skills/debug-ci-failure/   # new
    ├── agents/api-reviewer.md     # new
    └── hooks/block-secrets-write.py   # new
```

This module does not require Docker or a deployed app — see
[`docs/agent-extension-pack.md`](docs/agent-extension-pack.md) for why the
live `.claude/` config lives in the app directory rather than here, and the
relationship to the separate, Docker-dependent Module 4 work.
