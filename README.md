# Vercel AI SDK + Scalekit Agent Auth

A daily briefing agent that reads your Google Calendar and Gmail, built in both TypeScript and Python. Uses [Scalekit Agent Auth](https://docs.scalekit.com/agent-auth/quickstart/) to manage OAuth tokens so you never handle credentials manually.

## What it does

Ask the agent for a summary of your day. It fetches today's calendar events and your top unread emails, then returns a concise briefing:

```
Here's your day for Friday, March 27:

📅 Calendar (3 events)
- 9:00 AM  Team standup
- 1:00 PM  Product review with design
- 4:00 PM  1:1 with manager

📧 Unread emails (5)
- "Q1 roadmap feedback needed" — Sarah Chen (1h ago)
- "Deploy failed: production" — GitHub Actions (2h ago)
...
```

## Why this repo

Two ways to call third-party APIs with Scalekit-managed credentials are shown side by side:

| Tool | Pattern | How |
|------|---------|-----|
| Google Calendar | **OAuth token** | Scalekit provides a token → agent calls Google Calendar REST API directly |
| Gmail | **Built-in action** | Agent calls `execute_tool("gmail_fetch_mails")` → Scalekit makes the API call |

Both patterns use the same Scalekit auth layer. Pick the one that fits your use case.

## Prerequisites

- A [Scalekit account](https://app.scalekit.com) with `gmail` and `googlecalendar` connections configured
- An Anthropic API key
- Node.js 18+ and [pnpm](https://pnpm.io) (TypeScript version)
- Python 3.11+ and [uv](https://docs.astral.sh/uv/) (Python version)

## Setup

**1. Add credentials**

Copy the example env file into whichever folder you're running:

```bash
cp typescript/.env.example typescript/.env
# or
cp typescript/.env.example python/.env
```

Fill in your credentials:

```env
SCALEKIT_ENV_URL=https://your-env.scalekit.dev
SCALEKIT_CLIENT_ID=skc_...
SCALEKIT_CLIENT_SECRET=...

ANTHROPIC_API_KEY=sk-ant-...
```

> Get your Scalekit credentials at [app.scalekit.com](https://app.scalekit.com) → select your environment → Settings → API Credentials

**2. Run**

TypeScript:
```bash
cd typescript
pnpm install
pnpm start
```

Python:
```bash
cd python
uv venv .venv
uv pip install -r requirements.txt
.venv/bin/python index.py
```

## Authorizing a user

The first time a user runs the agent, Scalekit checks if they've authorized Gmail and Google Calendar. If not, an authorization link is printed in the terminal:

```
[gmail] Authorization required.
Open this link:

  https://auth.scalekit.dev/connect/...

Press Enter once you have completed the OAuth flow...
```

After the user clicks the link and completes OAuth, Scalekit stores the tokens. Subsequent runs skip the prompt entirely — tokens are refreshed automatically.

## How the two patterns work

### OAuth token pattern (Calendar)

```typescript
// Scalekit returns a valid, auto-refreshed token
const token = await getAccessToken('googlecalendar');

// Your code calls the API directly
const res = await fetch('https://www.googleapis.com/calendar/v3/...', {
  headers: { Authorization: `Bearer ${token}` },
});
```

Use this when you need full control over the API call — custom parameters, pagination, error handling.

### Built-in action pattern (Gmail)

```typescript
// Scalekit executes the API call for you
const result = await scalekit.tools.executeTool({
  toolName: 'gmail_fetch_mails',
  connectedAccountId: account.id,
  params: { query: 'is:unread', max_results: 5 },
});
```

Use this for speed — no API docs to read, no request building. Scalekit handles the call and returns structured data.

## Learn more

- [Agent Auth quickstart](https://docs.scalekit.com/agent-auth/quickstart/) — connect your first user in minutes
- [Calling tools via Scalekit SDK](https://docs.scalekit.com/agent-auth/tools/agent-tools-quickstart/) — direct execution, modifiers, and agentic tool calling
- [All supported connectors](https://docs.scalekit.com/guides/integrations/agent-connectors/) — Gmail, Google Calendar, Slack, Notion, and more
