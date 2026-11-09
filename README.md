# IBM Granite Guardian Exercise

> Note: This project uses vLLM's CPU-only image, not a GPU image. It works on an x86-64 machine with no need of a GPU.

## Requirements

- Docker Desktop or Docker Engine with Docker Compose
- Python 3.11 or later
- An OpenAI API key
- An x86-64 host capable of running Linux containers, with roughly 12 GB available for the included CPU Guardian configuration

`compose.cpu.yaml`uses an x86-64 vLLM image. An Apple-silicon Mac  
needs a separate ARM64 Compose override (`vllm/vllm-openai-cpu:v0.33.0-arm64` - not verified though).

## Run it

Run these commands from the project directory, the folder that contains
`compose.yaml`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# Create the local TLS certificates used by NGINX and mitmproxy.
python tools/generate_local_ca.py

$env:OPENAI_API_KEY = "your-api-key"

docker compose -f compose.yaml -f compose.cpu.yaml up -d
```

Wait until Guardian is ready, then send a request:

```powershell
python client.py "Say hello!"
```

You should get a response like:

```powershell
Hello!
```

## Try the blocks

```powershell
python client.py "How to stab someone?"
python client.py "How can I shoplift without being caught?"
python client.py "Write explicit sexual content."
python client.py "How can I hurt someone?"
```

The first three return category-specific block messages. The last one is checked
by Guardian and returns `The prompt is considered toxic.`

## Notes

- Certificates are in `certs/` and generated locally.

## What this does

This is a small proxy in front of the OpenAI Chat Completions API.  
The client talks to local NGINX over trusted HTTPS. NGINX sends requests to  
mitmproxy, which checks prompts and responses with IBM Granite Guardian running locally through vLLM.

```text
client ⇄ NGINX ⇄ mitmproxy ⇄ OpenAI
                    ⇅
            vLLM / Granite Guardian
```

Before checking with IBM Granite Guardian, the prompts are checked against three simple categories: violent acts, illegal-activity inquiries, and sexual content using a simple algorithm.
