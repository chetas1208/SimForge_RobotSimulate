#!/usr/bin/env bash

set -euo pipefail

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI not found in PATH." >&2
  echo "Install or expose Codex first, then rerun this script." >&2
  exit 1
fi

if [[ -z "${BUTTERBASE_API_KEY:-}" ]]; then
  echo "BUTTERBASE_API_KEY is not set." >&2
  echo "Export your key first, then rerun this script." >&2
  exit 1
fi

codex mcp add butterbase \
  --url https://api.butterbase.ai/mcp \
  --bearer-token-env-var BUTTERBASE_API_KEY

echo "Butterbase MCP registration attempted successfully."
