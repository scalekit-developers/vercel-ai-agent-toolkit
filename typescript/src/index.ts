import { generateText, tool } from 'ai';
import { anthropic } from '@ai-sdk/anthropic';
import { ScalekitClient } from '@scalekit-sdk/node';
import { ConnectorStatus } from '@scalekit-sdk/node/lib/pkg/grpc/scalekit/v1/connected_accounts/connected_accounts_pb.js';
import { z } from 'zod';
import 'dotenv/config';

const USER_ID = 'user_123';

const scalekit = new ScalekitClient(
  process.env.SCALEKIT_ENV_URL!,
  process.env.SCALEKIT_CLIENT_ID!,
  process.env.SCALEKIT_CLIENT_SECRET!,
);

/**
 * Ensures a connected account exists and the user has completed OAuth.
 * Prompts in the terminal if authorization is needed.
 * Returns the connected account (with its ID for tool execution).
 */
async function ensureConnected(connector: string) {
  const { connectedAccount } = await scalekit.connectedAccounts.getOrCreateConnectedAccount({
    connector,
    identifier: USER_ID,
  });

  if (connectedAccount?.status !== ConnectorStatus.ACTIVE) {
    const { link } = await scalekit.connectedAccounts.getMagicLinkForConnectedAccount({
      connector,
      identifier: USER_ID,
    });
    console.log(`\n[${connector}] Authorization required.`);
    console.log(`Open this link to connect your account:\n\n  ${link}\n`);
    console.log('Press Enter once you have completed the OAuth flow...');
    await new Promise<void>(resolve => {
      process.stdin.resume();
      process.stdin.once('data', () => { process.stdin.pause(); resolve(); });
    });
  }

  return connectedAccount;
}

/**
 * Fetches a fresh OAuth access token for the connector.
 * Always calls getConnectedAccountByIdentifier — Scalekit auto-refreshes expired tokens.
 */
async function getAccessToken(connector: string): Promise<string> {
  const response = await scalekit.connectedAccounts.getConnectedAccountByIdentifier({
    connector,
    identifier: USER_ID,
  });
  const details = response?.connectedAccount?.authorizationDetails?.details;
  if (details?.case === 'oauthToken' && details.value?.accessToken) {
    return details.value.accessToken;
  }
  throw new Error(`No access token for ${connector}`);
}

async function main() {
  // Ensure both connectors are authorized (prompts in terminal if not ACTIVE)
  const [, gmailAccount] = await Promise.all([
    ensureConnected('googlecalendar'),
    ensureConnected('gmail'),
  ]);

  // Calendar: fetch a fresh OAuth token for direct Google Calendar API calls
  const calendarToken = await getAccessToken('googlecalendar');

  const today = new Date();
  const timeMin = new Date(today.getFullYear(), today.getMonth(), today.getDate()).toISOString();
  const timeMax = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 23, 59, 59).toISOString();

  const { text } = await generateText({
    model: anthropic('claude-sonnet-4-6'),
    prompt: `Give me a summary of my day for ${today.toDateString()}: list today's calendar events and my top 5 unread emails.`,
    tools: {
      // Calendar: direct Google Calendar API call using Scalekit-managed OAuth token
      getCalendarEvents: tool({
        description: "Fetch today's events from Google Calendar",
        parameters: z.object({
          maxResults: z.number().optional().default(5).describe('Max events to return'),
        }),
        execute: async ({ maxResults }) => {
          const url = new URL('https://www.googleapis.com/calendar/v3/calendars/primary/events');
          url.searchParams.set('timeMin', timeMin);
          url.searchParams.set('timeMax', timeMax);
          url.searchParams.set('maxResults', String(maxResults));
          url.searchParams.set('orderBy', 'startTime');
          url.searchParams.set('singleEvents', 'true');

          const res = await fetch(url.toString(), {
            headers: { Authorization: `Bearer ${calendarToken}` },
          });
          if (!res.ok) throw new Error(`Calendar API error: ${res.status}`);
          const data = await res.json() as { items?: unknown[] };
          return data.items ?? [];
        },
      }),

      // Gmail: executed via Scalekit's built-in gmail_fetch_mails action
      getUnreadEmails: tool({
        description: 'Fetch top unread emails from Gmail via Scalekit actions',
        parameters: z.object({
          maxResults: z.number().optional().default(5).describe('Max emails to return'),
        }),
        execute: async ({ maxResults }) => {
          const response = await scalekit.tools.executeTool({
            toolName: 'gmail_fetch_mails',
            connectedAccountId: gmailAccount?.id,
            params: {
              query: 'is:unread',
              max_results: maxResults,
            },
          });
          return response.data?.toJson() ?? {};
        },
      }),
    },
    maxSteps: 5,
  });

  console.log(text);
}

main().catch(console.error);
