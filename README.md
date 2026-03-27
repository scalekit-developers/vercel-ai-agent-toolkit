# Vercel AI SDK + Scalekit Agent Auth — Daily Summary Agent

Fetches today's Google Calendar events and top unread Gmail messages using **Scalekit Agent Auth** for OAuth token management and **Vercel AI SDK / Anthropic SDK** for the LLM layer.

## How it works

This demo shows **two ways** to call third-party APIs with Scalekit-managed credentials:

| Tool | Approach | How |
|------|----------|-----|
| Google Calendar | **Direct API call** | Scalekit provides an OAuth token → agent calls Google Calendar REST API directly |
| Gmail | **Scalekit built-in action** | Agent calls `execute_tool("gmail_fetch_mails")` → Scalekit handles the API call |

```
User prompt
  → LLM calls getCalendarEvents
      → Scalekit returns OAuth token for user
          → Agent calls Google Calendar API directly with token
  → LLM calls getUnreadEmails
      → Agent calls scalekit.execute_tool("gmail_fetch_mails")
          → Scalekit calls Gmail API and returns results
  → LLM summarizes both and responds
```

Scalekit handles the full OAuth lifecycle (authorization, token storage, auto-refresh) for both connectors.

---

## Prerequisites

- Node.js 18+ and pnpm (TypeScript version)
- Python 3.11+ and [uv](https://docs.astral.sh/uv/) (Python version)
- Anthropic API key with credits
- Scalekit account with `gmail` and `googlecalendar` connected accounts for `user_123`

---

## Setup

Copy the shared `.env` into each project folder:

```bash
cp typescript/.env.example typescript/.env
cp typescript/.env.example python/.env
```

Fill in both `.env` files:

```env
SCALEKIT_ENV_URL=https://your-env.scalekit.dev
SCALEKIT_CLIENT_ID=skc_...
SCALEKIT_CLIENT_SECRET=...

ANTHROPIC_API_KEY=sk-ant-...
```

> Get Scalekit credentials: [app.scalekit.com](https://app.scalekit.com) → select your environment → Settings → API Credentials

---

## TypeScript

```bash
cd typescript
pnpm install
pnpm start
```

**How it works:**
- Uses `@ai-sdk/anthropic` + `generateText` with two tools
- **`getCalendarEvents`**: Scalekit SDK fetches an OAuth token → agent calls Google Calendar REST API directly with `fetch()`
- **`getUnreadEmails`**: agent calls `scalekit.tools.executeTool("gmail_fetch_mails")` → Scalekit executes the Gmail API call

**Key files:**
- `src/index.ts` — main agent script

---

## Python

```bash
cd python
uv venv .venv
uv pip install -r requirements.txt
.venv/bin/python index.py
```

**How it works:**
- Uses the `anthropic` SDK directly with a manual tool-calling loop
- **`get_calendar_events`**: Scalekit SDK fetches an OAuth token → agent calls Google Calendar REST API directly with `requests`
- **`get_unread_emails`**: agent calls `actions.execute_tool("gmail_fetch_mails")` → Scalekit executes the Gmail API call

**Key files:**
- `index.py` — main agent script

---

## Authorizing a user (first time)

Both agents automatically check if the user has authorized each connector. If not, they print an authorization link and wait for you to complete the OAuth flow.

To manually generate an authorization link:

**TypeScript**
```typescript
const { link } = await scalekit.connectedAccounts.getMagicLinkForConnectedAccount({
  connector: 'googlecalendar',
  identifier: 'user_123',
});
console.log('Authorize here:', link);
```

**Python**
```python
link_response = actions.get_authorization_link(
    connection_name="googlecalendar",
    identifier="user_123",
)
print("Authorize here:", link_response.link)
```

Visit the link, complete Google OAuth, then re-run the agent.

---

## Learn more

- [Agent Auth quickstart](https://docs.scalekit.com/agent-auth/quickstart/) — get started with Scalekit Agent Auth
- [Calling tools via Scalekit SDK](https://docs.scalekit.com/agent-auth/tools/agent-tools-quickstart/) — direct tool execution, modifiers, and agentic calling
- [All supported agent connectors](https://docs.scalekit.com/guides/integrations/agent-connectors/) — Gmail, Google Calendar, Slack, Notion, and more
