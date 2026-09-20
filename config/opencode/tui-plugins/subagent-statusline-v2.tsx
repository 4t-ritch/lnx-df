/** @jsxImportSource @opentui/solid */
import { Plugin } from "@opencode/plugin/tui"
import { createSignal } from "solid-js"

type Counts = {
  running: number
  done: number
  failed: number
}

export default Plugin.define({
  id: "gentle-ai.subagent-statusline-v2",
  setup(context) {
    const [revision, setRevision] = createSignal(0)
    const stop = context.data.listen(() => {
      setRevision((value) => value + 1)
    })

    const children = (sessionID?: string) => {
      revision()
      if (!sessionID) return context.data.session.list().filter((session) => session.parentID)
      const rootID = context.data.session.root(sessionID)
      return context.data.session
        .family(rootID)
        .filter((id) => id !== rootID)
        .map((id) => context.data.session.get(id))
        .filter((session) => session !== undefined)
    }

    const counts = (sessionID?: string): Counts =>
      children(sessionID).reduce<Counts>(
        (result, session) => {
          if (context.data.session.status(session.id) === "running") result.running++
          else if (session.outcome === "failed" || session.outcome === "interrupted") result.failed++
          else result.done++
          return result
        },
        { running: 0, done: 0, failed: 0 },
      )

    const Status = (props: { sessionID?: string }) => {
      const value = counts(props.sessionID)
      const total = value.running + value.done + value.failed
      if (total === 0) return null
      return (
        <text>
          agents <span fg={context.theme.warning}>{value.running} running</span>
          {" · "}
          <span fg={context.theme.success}>{value.done} done</span>
          {value.failed > 0 ? <span fg={context.theme.error}> · {value.failed} failed</span> : null}
        </text>
      )
    }

    const unregisterHome = context.ui.slot({
      append: "home.footer.status",
      render: () => <Status />,
    })
    const unregisterPrompt = context.ui.slot({
      append: "prompt.footer.status",
      render: ({ sessionID }) => <Status sessionID={sessionID} />,
    })

    return () => {
      stop()
      unregisterHome()
      unregisterPrompt()
    }
  },
})
