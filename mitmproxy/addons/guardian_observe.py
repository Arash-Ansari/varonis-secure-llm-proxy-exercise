"""Observe OpenAI chat prompts with a locally served Granite Guardian model.

This first integration step never changes a request or response. It logs only a
yes/no Guardian decision and the prompt length, then lets mitmproxy continue
forwarding the request to OpenAI.
"""

import json
import os
import re
import urllib.error
import urllib.request

from mitmproxy import ctx, http


GUARDIAN_URL = os.environ["GUARDIAN_URL"]
GUARDIAN_MODEL = os.environ["GUARDIAN_MODEL"]
GUARDIAN_TIMEOUT_SECONDS = float(os.environ["GUARDIAN_TIMEOUT_SECONDS"])


# Simple pattern checks for the required prompt categories.
VIOLENT_ACT_PATTERNS = (
    re.compile(r"\b(stab(?:bed|bing)?|shoot(?:ing|s|\b)|kill(?:ed|ing|s)?|murder(?:ed|ing|s)?|strangl(?:ed|ing)|behead(?:ed|ing)|assault(?:ed|ing)?)\b", re.IGNORECASE),
)
ILLEGAL_INQUIRY_PATTERN = re.compile(
    r"\b(how (?:can|do|to)|ways? to|steps? to|teach me to)\b.*\b(shoplift|steal|break into|forge|counterfeit|bypass a lock)\b",
    re.IGNORECASE,
)
SEXUAL_CONTENT_PATTERN = re.compile(
    r"\b(sex|sexual|nude|naked|porn(?:ography)?|explicit sexual)\b",
    re.IGNORECASE,
)


def build_guardian_prompt(user_text: str) -> str:
    """Build the prescribed yes/no prompt format for Granite Guardian 3.x."""
    return f"""You are a safety agent trying to help determine whether the user message is harmful according to the safety risk definition below.

<start_of_turn>
User Message: {user_text}
<end_of_turn>

Our safety risk definition is defined below:

<start_of_risk_definition>
* The 'User' message is harmful by common-sense.
<end_of_risk_definition>

Is the user message harmful based on the risk definition? Your answer must be either 'Yes' or 'No'."""


def message_text(content: object) -> str:
    """Extract text from OpenAI Chat Completions string or content-part formats."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return ""


def extract_user_prompt(messages: object) -> str:
    if not isinstance(messages, list):
        return ""
    return "\n".join(
        message_text(message.get("content"))
        for message in messages
        if isinstance(message, dict) and message.get("role") == "user"
    ).strip()


def classify_required_category(user_text: str) -> str | None:
    """Return the first required category number matched by simple patterns."""
    if any(pattern.search(user_text) for pattern in VIOLENT_ACT_PATTERNS):
        return "1"
    if ILLEGAL_INQUIRY_PATTERN.search(user_text):
        return "2"
    if SEXUAL_CONTENT_PATTERN.search(user_text):
        return "3"
    return None


def guardian_decision(user_text: str) -> str:
    """Return Guardian's normalized yes/no decision, or 'unavailable'."""
    payload = json.dumps(
        {
            "model": GUARDIAN_MODEL,
            "messages": [
                {"role": "user", "content": build_guardian_prompt(user_text)}
            ],
            "temperature": 0,
            "max_tokens": 3,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        GUARDIAN_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=GUARDIAN_TIMEOUT_SECONDS) as response:
            result = json.load(response)
        content = result["choices"][0]["message"]["content"]
        answer = content.strip().lower().rstrip(".")
        if answer in {"yes", "no"}:
            return answer
        ctx.log.warn("Guardian returned an unexpected decision format.")
    except (KeyError, IndexError, TypeError, urllib.error.URLError, TimeoutError) as error:
        ctx.log.warn(f"Guardian observation unavailable: {error}")

    return "unavailable"


def request(flow: http.HTTPFlow) -> None:
    """Observe prompt risk for OpenAI Chat Completions without blocking traffic."""
    if flow.request.method != "POST" or flow.request.path.split("?", 1)[0] != "/v1/chat/completions":
        return

    try:
        request_data = json.loads(flow.request.get_text(strict=False))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        ctx.log.warn(f"Guardian observation skipped: invalid request JSON ({error}).")
        return

    prompt = extract_user_prompt(request_data.get("messages"))
    if not prompt:
        ctx.log.info("Guardian observation skipped: no user text found.")
        return

    decision = guardian_decision(prompt)
    category = classify_required_category(prompt) or "none"
    # Do not log prompt contents: prompts can contain sensitive user data.
    ctx.log.info(
        "Guardian observation: "
        f"decision={decision}, category={category}, "
        f"user_prompt_characters={len(prompt)}"
    )
