/** @jsxImportSource @opentui/solid */
import { Plugin } from "@opencode/plugin/tui"
import { createSignal } from "solid-js"

// Codex subscription usage sidebar block (V2 TUI plugin).
// Credential: CODEX_USAGE_TOKEN env var (independent token, presence-checked;
//   sent only as an Authorization header, never logged or rendered).
// Refresh: 10s fetch timeout, 5-minute cache throttle, 60s UI tick for the
//   reset countdown; failures keep the last snapshot and mark it stale.
// Sidebar: rendered via the `sidebar.content` slot; V2 offers no
//   between-Context-and-MCP insertion point, so order is host-controlled.
const TOKEN_ENV_VAR = "CODEX_USAGE_TOKEN"
const USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
const USER_AGENT = "opencode-codex-usage"
const FETCH_TIMEOUT_MS = 10_000
const CACHE_MS = 5 * 60 * 1000
const TICK_MS = 60_000
const WEEK_SECONDS = 604_800
const DAY_SECONDS = 86_400

// Window/limit shapes mirror gentle-pi `shell-usage.ts` (RawCodexUsage).
interface RawWindow {
  used_percent?: number
  limit_window_seconds?: number
  reset_after_seconds?: number
  reset_at?: number
}

interface RawRateLimit {
  limit_reached?: boolean
  primary_window?: RawWindow | null
  secondary_window?: RawWindow | null
}

interface RawAdditionalLimit {
  limit_name?: string
  rate_limit?: RawRateLimit | null
}

interface RawCodexUsage {
  plan_type?: string
  rate_limit?: RawRateLimit | null
  additional_rate_limits?: RawAdditionalLimit[] | null
}

interface UsageWindow {
  label: string
  usedPercent: number
  windowSeconds: number
  resetAt: number | null
}

interface UsageLimit {
  name: string
  windows: UsageWindow[]
}

interface SnapshotWindow {
  remaining: number
  resetAt: number | null
}

interface UsageSnapshot {
  monthly: SnapshotWindow | null
  weekly: SnapshotWindow | null
  cost: string
  fetchedAt: number
  stale: boolean
  error: string | null
}

interface CacheState {
  snapshot: UsageSnapshot | null
  lastFetch: number
}

function windowLabel(seconds: number): string {
  if (seconds === WEEK_SECONDS) return "week"
  if (seconds >= DAY_SECONDS && seconds % DAY_SECONDS === 0) return `${seconds / DAY_SECONDS}d`
  if (seconds >= 3600 && seconds % 3600 === 0) return `${seconds / 3600}h`
  return `${Math.max(1, Math.round(seconds / 60))}m`
}

function parseWindow(raw: RawWindow | null | undefined, now: number): UsageWindow | undefined {
  if (!raw || typeof raw.used_percent !== "number" || typeof raw.limit_window_seconds !== "number") return undefined
  const resetAt =
    typeof raw.reset_at === "number"
      ? raw.reset_at * 1000
      : typeof raw.reset_after_seconds === "number"
        ? now + raw.reset_after_seconds * 1000
        : null
  return { label: windowLabel(raw.limit_window_seconds), usedPercent: raw.used_percent, windowSeconds: raw.limit_window_seconds, resetAt }
}

function parseRateLimit(name: string, raw: RawRateLimit | null | undefined, now: number): UsageLimit | undefined {
  if (!raw) return undefined
  const windows = [parseWindow(raw.primary_window, now), parseWindow(raw.secondary_window, now)].filter(
    (window): window is UsageWindow => window !== undefined,
  )
  if (windows.length === 0) return undefined
  return { name, windows }
}

function parseCodexUsage(payload: unknown, now: number): { plan: string | undefined; limits: UsageLimit[] } {
  const raw = (payload ?? {}) as RawCodexUsage
  const limits: UsageLimit[] = []
  const main = parseRateLimit("codex", raw.rate_limit, now)
  if (main) limits.push(main)
  for (const extra of raw.additional_rate_limits ?? []) {
    const limit = parseRateLimit(extra.limit_name ?? "limit", extra.rate_limit, now)
    if (limit) limits.push(limit)
  }
  return { plan: typeof raw.plan_type === "string" ? raw.plan_type : undefined, limits }
}

function toSnapshotWindow(window: UsageWindow): SnapshotWindow {
  const remaining = Math.max(0, Math.min(100, Math.round(100 - window.usedPercent)))
  return { remaining, resetAt: window.resetAt }
}

function pickWindows(limits: UsageLimit[]): { monthly: UsageWindow | null; weekly: UsageWindow | null } {
  const all = limits.flatMap((limit) => limit.windows)
  const weekly = all.find((window) => window.windowSeconds === WEEK_SECONDS || window.label === "week" || window.label === "7d") ?? null
  const monthly =
    all.find(
      (window) =>
        (window.windowSeconds >= 28 * DAY_SECONDS && window.windowSeconds <= 31 * DAY_SECONDS) ||
        window.label === "month" ||
        window.label === "30d",
    ) ??
    all[0] ??
    null
  return { monthly, weekly }
}

function extractCost(payload: unknown, plan: string | undefined): string {
  const root = (payload ?? {}) as Record<string, unknown>
  const candidates: unknown[] = [root["credits"], (root["billing"] as Record<string, unknown> | undefined)?.["credits"]]
  for (const candidate of candidates) {
    if (typeof candidate === "number" && Number.isFinite(candidate)) return `$${candidate.toFixed(2)}`
    if (candidate && typeof candidate === "object") {
      const fields = candidate as Record<string, unknown>
      for (const key of ["remaining", "balance", "total", "used", "amount"]) {
        const value = fields[key]
        if (typeof value === "number" && Number.isFinite(value)) return `$${value.toFixed(2)}`
      }
    }
  }
  if (typeof plan === "string" && plan.length > 0) return plan
  return "—"
}

function formatShortReset(resetAt: number | null, now: number): string {
  if (resetAt === null) return ""
  const seconds = Math.round((resetAt - now) / 1000)
  if (seconds <= 0) return " (now)"
  if (seconds < 3600) return ` (${Math.max(1, Math.round(seconds / 60))}m)`
  if (seconds < DAY_SECONDS) return ` (${Math.floor(seconds / 3600)}h)`
  return ` (${Math.floor(seconds / DAY_SECONDS)}d)`
}

function renderMeter(remaining: number): string {
  const cells = 10
  const filled = Math.max(0, Math.min(cells, Math.round((remaining / 100) * cells)))
  return `${"█".repeat(filled)}${"░".repeat(cells - filled)} ${remaining}%`
}

async function fetchSnapshot(token: string): Promise<UsageSnapshot> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS)
  try {
    const response = await fetch(USAGE_URL, {
      headers: { Authorization: `Bearer ${token}`, "User-Agent": USER_AGENT },
      signal: controller.signal,
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const payload: unknown = await response.json()
    const now = Date.now()
    const { plan, limits } = parseCodexUsage(payload, now)
    if (limits.length === 0) throw new Error("empty usage payload")
    const { monthly, weekly } = pickWindows(limits)
    return {
      monthly: monthly ? toSnapshotWindow(monthly) : null,
      weekly: weekly ? toSnapshotWindow(weekly) : null,
      cost: extractCost(payload, plan),
      fetchedAt: now,
      stale: false,
      error: null,
    }
  } finally {
    clearTimeout(timer)
  }
}

export default Plugin.define({
  id: "gentle-ai.codex-usage",
  setup(context) {
    // Presence check only; the value is read at fetch time and never logged.
    if (!process.env[TOKEN_ENV_VAR]) {
      const Missing = () => (
        <box flexDirection="column" gap={0}>
          <text>
            <span fg={context.theme.accent}>Codex</span>
          </text>
          <text>Codex monthly — · weekly — · cost — (set CODEX_USAGE_TOKEN)</text>
        </box>
      )
      const unregister = context.ui.slot({
        append: "sidebar.content",
        render: () => <Missing />,
      })
      return () => {
        unregister()
      }
    }

    const [cache, setCache] = context.storage.memory<CacheState>("codex-usage", {
      initial: { snapshot: null, lastFetch: 0 },
    })
    const [tick, setTick] = createSignal(0)
    let inFlight = false

    async function refresh(): Promise<void> {
      if (inFlight) return
      if (cache.snapshot && Date.now() - cache.lastFetch < CACHE_MS) return
      const token = process.env[TOKEN_ENV_VAR]
      if (!token) return
      inFlight = true
      try {
        const snapshot = await fetchSnapshot(token)
        setCache((draft) => {
          draft.snapshot = snapshot
          draft.lastFetch = Date.now()
        })
      } catch {
        // Keep the last valid snapshot and mark it stale; never throw to the TUI.
        setCache((draft) => {
          draft.lastFetch = Date.now()
          if (draft.snapshot) {
            draft.snapshot = { ...draft.snapshot, stale: true }
          } else {
            draft.snapshot = { monthly: null, weekly: null, cost: "—", fetchedAt: 0, stale: false, error: "unavailable" }
          }
        })
      } finally {
        inFlight = false
      }
    }

    const stopListening = context.data.listen(() => {
      void refresh()
    })
    // Cheap UI tick: re-renders the short reset countdown; fetch stays throttled.
    const interval = setInterval(() => {
      setTick((value) => value + 1)
      void refresh()
    }, TICK_MS)
    void refresh()

    const CodexUsage = () => {
      tick()
      const snapshot = cache.snapshot
      if (!snapshot) {
        return (
          <box flexDirection="column" gap={0}>
            <text>
              <span fg={context.theme.accent}>Codex</span>
            </text>
            <text>Codex … fetching usage</text>
          </box>
        )
      }
      if (snapshot.error && !snapshot.monthly && !snapshot.weekly) {
        return (
          <box flexDirection="column" gap={0}>
            <text>
              <span fg={context.theme.accent}>Codex</span>
            </text>
            <text>Codex unavailable · check token/network</text>
          </box>
        )
      }
      const now = Date.now()
      const staleSuffix = snapshot.stale ? " (stale)" : ""
      const monthlyText = snapshot.monthly
        ? `M ${snapshot.monthly.remaining}% left${formatShortReset(snapshot.monthly.resetAt, now)}`
        : "M —"
      const weeklyText = snapshot.weekly
        ? `W ${snapshot.weekly.remaining}% left${formatShortReset(snapshot.weekly.resetAt, now)}`
        : "W —"
      const meterBase = snapshot.monthly ?? snapshot.weekly
      return (
        <box flexDirection="column" gap={0}>
          <text>
            <span fg={context.theme.accent}>Codex</span>
            {staleSuffix ? <span fg={context.theme.warning}>{staleSuffix}</span> : null}
          </text>
          <text>
            {monthlyText} · {weeklyText} · {snapshot.cost}
          </text>
          {meterBase ? <text>{renderMeter(meterBase.remaining)}</text> : null}
        </box>
      )
    }

    const unregister = context.ui.slot({
      append: "sidebar.content",
      render: () => <CodexUsage />,
    })

    return () => {
      clearInterval(interval)
      stopListening()
      unregister()
    }
  },
})
