import os
import time
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

JIRA_BASE_URL  = os.getenv("JIRA_BASE_URL")
JIRA_EMAIL     = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

AICORE_AUTH_URL       = os.getenv("AICORE_AUTH_URL", "").rstrip("/")
AICORE_CLIENT_ID      = os.getenv("AICORE_CLIENT_ID", "")
AICORE_CLIENT_SECRET  = os.getenv("AICORE_CLIENT_SECRET", "")
AICORE_BASE_URL       = os.getenv("AICORE_BASE_URL", "").rstrip("/")
AICORE_RESOURCE_GROUP = os.getenv("AICORE_RESOURCE_GROUP", "default")
AICORE_DEPLOYMENT_ID  = os.getenv("AICORE_DEPLOYMENT_ID", "")

JIRA_AUTH    = (JIRA_EMAIL, JIRA_API_TOKEN)
JIRA_HEADERS = {"Content-Type": "application/json"}

_TOKEN_CACHE = {}
_DEP_CACHE   = {}


def _get_token():
    now = time.time()
    if _TOKEN_CACHE.get("token") and now < _TOKEN_CACHE.get("expires_at", 0) - 300:
        return _TOKEN_CACHE["token"]
    r = requests.post(
        AICORE_AUTH_URL + "/oauth/token",
        data={"grant_type": "client_credentials"},
        auth=(AICORE_CLIENT_ID, AICORE_CLIENT_SECRET),
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    _TOKEN_CACHE["token"]      = data["access_token"]
    _TOKEN_CACHE["expires_at"] = now + float(data.get("expires_in", 3600))
    return _TOKEN_CACHE["token"]


def _get_dep_url():
    if "url" in _DEP_CACHE:
        return _DEP_CACHE["url"]
    if AICORE_DEPLOYMENT_ID:
        url = f"{AICORE_BASE_URL}/v2/inference/deployments/{AICORE_DEPLOYMENT_ID}"
        _DEP_CACHE["url"] = url
        return url
    token = _get_token()
    r = requests.get(
        f"{AICORE_BASE_URL}/v2/lm/deployments",
        headers={"Authorization": f"Bearer {token}", "AI-Resource-Group": AICORE_RESOURCE_GROUP},
        timeout=30,
    )
    r.raise_for_status()
    for dep in r.json().get("resources", []):
        if dep.get("status") == "RUNNING":
            url = f"{AICORE_BASE_URL}/v2/inference/deployments/{dep['id']}"
            _DEP_CACHE["url"] = url
            return url
    raise RuntimeError("No running deployment found in AI Core.")


def _aicore_chat(prompt):
    token   = _get_token()
    dep_url = _get_dep_url()
    r = requests.post(
        f"{dep_url}/v1/chat/completions",
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}]},
        headers={
            "Authorization":     f"Bearer {token}",
            "AI-Resource-Group": AICORE_RESOURCE_GROUP,
            "Content-Type":      "application/json",
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def find_user_by_email(email):
    r = requests.get(
        f"{JIRA_BASE_URL}/rest/api/3/user/search",
        headers=JIRA_HEADERS, auth=JIRA_AUTH,
        params={"query": email}
    )
    if r.status_code != 200 or not r.json():
        return None, "User not found"
    return r.json()[0], None


def fetch_user_issues(account_id):
    r = requests.get(
        f"{JIRA_BASE_URL}/rest/api/3/search/jql",
        headers=JIRA_HEADERS, auth=JIRA_AUTH,
        params={
            "jql": f'assignee = "{account_id}" ORDER BY updated DESC',
            "maxResults": 50,
            "fields": "summary,status,issuetype,priority,assignee,created,updated"
        }
    )
    if r.status_code != 200:
        return None, f"Error {r.status_code}: {r.text}"
    return r.json().get("issues", []), None


def analyze_with_ai(user_name, issues):
    if not issues:
        return "No issues found for this user."

    issue_list = "\n".join([
        f"- [{i['key']}] {i['fields']['issuetype']['name']} | "
        f"{i['fields']['summary']} | Status: {i['fields']['status']['name']}"
        for i in issues
    ])

    prompt = f"""You are an AI assistant helping with employee offboarding and knowledge transfer.

The following Jira issues are assigned to {user_name} who is leaving the team:

{issue_list}

Provide a concise analysis with these 4 sections:

1. PENDING ITEMS: List open/in-progress items that need immediate attention.
2. KNOWLEDGE AREAS: What modules or domains does this person own?
3. RISK ASSESSMENT: What is the impact risk if this person leaves without a handover?
4. HIRING SUGGESTION: What skills/profile should their replacement have?

Keep it short and practical."""

    return _aicore_chat(prompt)
