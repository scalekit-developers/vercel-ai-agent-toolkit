import os
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
import anthropic
import scalekit.client

load_dotenv()

USER_ID = "user_123"

scalekit_client = scalekit.client.ScalekitClient(
    client_id=os.environ["SCALEKIT_CLIENT_ID"],
    client_secret=os.environ["SCALEKIT_CLIENT_SECRET"],
    env_url=os.environ["SCALEKIT_ENV_URL"],
)
actions = scalekit_client.actions


def ensure_connected(connector: str):
    """
    Ensures a connected account exists and the user has completed OAuth.
    Prompts in the terminal if authorization is needed.
    Returns the connected account object.
    """
    response = actions.get_or_create_connected_account(
        connection_name=connector,
        identifier=USER_ID,
    )
    connected_account = response.connected_account

    if connected_account.status != "ACTIVE":
        link_response = actions.get_authorization_link(
            connection_name=connector,
            identifier=USER_ID,
        )
        print(f"\n[{connector}] Authorization required.")
        print(f"Open this link to connect your account:\n\n  {link_response.link}\n")
        input("Press Enter once you have completed the OAuth flow...")

    return connected_account


def get_access_token(connector: str) -> str:
    """
    Fetches a fresh OAuth access token for the connector.
    Always calls get_connected_account — Scalekit auto-refreshes expired tokens.
    """
    response = actions.get_connected_account(
        connection_name=connector,
        identifier=USER_ID,
    )
    tokens = response.connected_account.authorization_details["oauth_token"]
    return tokens["access_token"]


def fetch_calendar_events(access_token: str, max_results: int = 5) -> list:
    """Direct Google Calendar API call using Scalekit-managed OAuth token."""
    today = datetime.now(timezone.utc).astimezone()
    time_min = today.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    time_max = today.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

    resp = requests.get(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "timeMin": time_min,
            "timeMax": time_max,
            "maxResults": max_results,
            "orderBy": "startTime",
            "singleEvents": "true",
        },
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def fetch_unread_emails(connected_account_id: str, max_results: int = 5) -> dict:
    """Fetch unread emails via Scalekit's built-in gmail_fetch_mails action."""
    response = actions.execute_tool(
        tool_name="gmail_fetch_mails",
        connected_account_id=connected_account_id,
        tool_input={
            "query": "is:unread",
            "max_results": max_results,
        },
    )
    return response.result


def run_agent():
    # Ensure both connectors are authorized (prompts in terminal if not ACTIVE)
    gmail_account = ensure_connected("gmail")
    ensure_connected("googlecalendar")

    # Calendar: fetch a fresh OAuth token for direct API calls
    calendar_token = get_access_token("googlecalendar")

    client = anthropic.Anthropic()
    today = datetime.now().strftime("%A, %B %d, %Y")

    tools = [
        {
            "name": "get_calendar_events",
            "description": "Fetch today's events from Google Calendar (direct API call)",
            "input_schema": {
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "description": "Max number of events to return",
                        "default": 5,
                    }
                },
            },
        },
        {
            "name": "get_unread_emails",
            "description": "Fetch top unread emails from Gmail via Scalekit actions",
            "input_schema": {
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "description": "Max number of emails to return",
                        "default": 5,
                    }
                },
            },
        },
    ]

    messages = [
        {
            "role": "user",
            "content": f"Give me a summary of my day for {today}: list today's calendar events and my top 5 unread emails.",
        }
    ]

    # Agentic loop
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(block.text)
            break

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                max_results = block.input.get("max_results", 5)

                if block.name == "get_calendar_events":
                    # Direct Google Calendar API call
                    result = fetch_calendar_events(calendar_token, max_results)
                elif block.name == "get_unread_emails":
                    # Scalekit built-in gmail_fetch_mails action
                    result = fetch_unread_emails(gmail_account.id, max_results)
                else:
                    result = {"error": f"Unknown tool: {block.name}"}

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        else:
            break


if __name__ == "__main__":
    run_agent()
