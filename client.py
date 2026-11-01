"""Send one prompt directly to the OpenAI Chat Completions API."""
import argparse
import os
import sys

from openai import APIError, AuthenticationError, OpenAI

# A fast and affordable model good enough for this exercise.
MODEL = "gpt-6-luna"


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

    client = OpenAI(api_key=api_key)

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
