"""Wait until the local Guardian model can complete one inference request."""

import json
import os
import sys
import urllib.request


GUARDIAN_URL = os.environ["GUARDIAN_URL"]
GUARDIAN_MODEL = os.environ["GUARDIAN_MODEL"]


def main() -> None:
    payload = json.dumps(
        {
            "model": GUARDIAN_MODEL,
            "messages": [{"role": "user", "content": "Reply with exactly: READY"}],
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
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.load(response)
        content = result["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, OSError, ValueError) as error:
        sys.exit(f"Guardian warm-up failed: {error}")

    if not content:
        sys.exit("Guardian warm-up failed: no response content.")
    print("Guardian warm-up completed.")


if __name__ == "__main__":
    main()
