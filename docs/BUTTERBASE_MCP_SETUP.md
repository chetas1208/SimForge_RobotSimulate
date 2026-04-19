# Butterbase MCP Setup

This repo includes an optional helper for registering the Butterbase MCP server
with a local Codex installation.

This setup is intentionally non-invasive:

- it does not change backend, frontend, or simulator behavior
- it is not loaded by SimForge at runtime
- it only runs if you invoke the helper script manually

## Manual Command

```bash
export BUTTERBASE_API_KEY=your-butterbase-api-key-here

codex mcp add butterbase \
  --url https://api.butterbase.ai/mcp \
  --bearer-token-env-var BUTTERBASE_API_KEY
```

## Helper Script

You can also use the repo helper:

```bash
export BUTTERBASE_API_KEY=your-butterbase-api-key-here
./tools/setup_butterbase_mcp.sh
```

## Notes

- Keep the API key in your shell environment, not in tracked source files.
- If the MCP entry already exists, Codex may ask you to update or replace it.
- This is an optional developer convenience only; SimForge does not depend on it.
