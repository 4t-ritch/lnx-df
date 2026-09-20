/** @jsxImportSource @opentui/solid */
import { Plugin } from "@opencode/plugin/tui"

// T1 scaffold: sidebar placeholder only. Real usage fetch lands in T2.
// Credential reference is env-based (CODEX_USAGE_TOKEN); never logged.
const TOKEN_ENV_VAR = "CODEX_USAGE_TOKEN"

export default Plugin.define({
  id: "gentle-ai.codex-usage",
  setup(context) {
    // Presence check only; the value itself is never read into memory here.
    const configured = Boolean(process.env[TOKEN_ENV_VAR])

    const CodexUsage = () => (
      <box flexDirection="column" gap={0}>
        <text>
          <span fg={context.theme.accent}>Codex</span>
        </text>
        <text>
          monthly — · weekly — · cost —{configured ? "" : " (env not configured)"}
        </text>
      </box>
    )

    const unregister = context.ui.slot({
      append: "sidebar.content",
      render: () => <CodexUsage />,
    })

    return () => {
      unregister()
    }
  },
})
