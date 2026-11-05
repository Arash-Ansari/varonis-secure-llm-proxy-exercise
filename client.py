"""Send one prompt directly to the OpenAI Chat Completions API."""
import argparse
import os
from pathlib import Path
import ssl
import sys

from openai import APIError, AuthenticationError, DefaultHttpx2Client, OpenAI

# A fast and affordable model good enough for this exercise.
MODEL = "gpt-6-luna"
# The client connects to NGINX, not directly to OpenAI.
BASE_URL = "https://localhost:8443/v1"
CA_CERTIFICATE = Path(__file__).with_name("certs") / "local-ca.crt"


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask OpenAI a question and print its answer.")
    parser.add_argument("prompt", help="The question or instruction to send to OpenAI.")
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit(
            "OPENAI_API_KEY is not set. In PowerShell, run: "
            '$env:OPENAI_API_KEY = "your-api-key"'
        )

    if not CA_CERTIFICATE.is_file():
        sys.exit("The local CA certificate is missing. Run: python tools/generate_local_ca.py")

    tls_context = ssl.create_default_context(cafile=CA_CERTIFICATE)
    client = OpenAI(
        api_key=api_key,
        base_url=BASE_URL,
        http_client=DefaultHttpx2Client(verify=tls_context),
    )

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": args.prompt}],
        )
    except AuthenticationError:
        sys.exit("OpenAI rejected the API key. Check OPENAI_API_KEY and try again.")
    except APIError as error:
        sys.exit(f"OpenAI request failed: {error}")

    print(completion.choices[0].message.content)


if __name__ == "__main__":
    main()
