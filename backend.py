import os
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

os.environ["AICORE_AUTH_URL"]       = os.getenv("AICORE_AUTH_URL", "")
os.environ["AICORE_CLIENT_ID"]      = os.getenv("AICORE_CLIENT_ID", "")
os.environ["AICORE_CLIENT_SECRET"]  = os.getenv("AICORE_CLIENT_SECRET", "")
os.environ["AICORE_BASE_URL"]       = os.getenv("AICORE_BASE_URL", "")
os.environ["AICORE_RESOURCE_GROUP"] = os.getenv("AICORE_RESOURCE_GROUP", "")

from gen_ai_hub.proxy.native.openai import chat

BASE_URL   = os.getenv("JIRA_BASE_URL")
EMAIL      = os.getenv("JIRA_EMAIL")
API_TOKEN  = os.getenv("JIRA_API_TOKEN")

AUTH    = (EMAIL, API_TOKEN)
HEADERS = {"Content-Type": "application/json"}


def fetch_user_issues(account_id):
    response = requests.get(
        f"{BASE_URL}/rest/api/3/search/jql",
        headers=HEADERS,
        auth=AUTH,
        params={
            "jql": f"assignee = \"{account_id}\" ORDER BY updated DESC",
            "maxResults": 50,
            "fields": "summary,status,issuetype,priority,assignee,created,updated"
        }
    )
    if response.status_code != 200:
        return None, f"Error {response.status_code}: {response.text}"
    return response.json().get("issues", []), None


def find_user_by_email(email):
    response = requests.get(
        f"{BASE_URL}/rest/api/3/user/search",
        headers=HEADERS,
        auth=AUTH,
        params={"query": email}
    )
    if response.status_code != 200 or not response.json():
        return None, "User not found"
    user = response.json()[0]
    return user, None


def analyze_with_ai(user_name, issues):
    if not issues:
        return "No issues found for this user."

    issue_list = "\n".join([
        f"- [{issue['key']}] {issue['fields']['issuetype']['name']} | "
        f"{issue['fields']['summary']} | "
        f"Status: {issue['fields']['status']['name']}"
        for issue in issues
    ])

    prompt = f"""
You are an AI assistant helping with employee offboarding and knowledge transfer.

The following Jira issues are assigned to {user_name} who is leaving the team:

{issue_list}

Please provide a concise analysis with these 4 sections:

1. PENDING ITEMS: List open/in-progress items that need immediate attention.
2. KNOWLEDGE AREAS: What modules or domains does this person own based on their work?
3. RISK ASSESSMENT: What is the impact risk if this person leaves without a handover?
4. HIRING SUGGESTION: What skills/profile should their replacement have?

Keep it short and practical.
"""

    response = chat.completions.create(
        model_name="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
