# Veklom SDK for Python

Official Python client for the [Veklom](https://veklom.com) governed inference platform.

## Install

```bash
pip install veklom
```

## Quick Start

```python
from veklom import VeklomClient

client = VeklomClient(api_key="your-api-key")

response = client.complete(
    prompt="Summarize this contract clause:",
    model="qwen2.5:1.5b"
)

print(response.text)
print(response.audit_log_id)   # tamper-evident audit chain entry
print(response.provider)       # ollama | groq
print(response.tokens_used)
```

## Async

```python
import asyncio
from veklom import VeklomClient

client = VeklomClient(api_key="your-api-key")

async def main():
    response = await client.complete_async(
        prompt="What are the key risks in this SLA?",
    )
    print(response.text)

asyncio.run(main())
```

## Auth

Get your API key from [app.veklom.com/vault](https://app.veklom.com/vault).

You can also use a JWT access token directly:

```python
client = VeklomClient(access_token="eyJ...")
```

## What is Veklom?

Veklom is a governed AI inference platform. Every request is:
- **Routed** — primary model (Ollama/Hetzner) with Groq fallback
- **Audited** — tamper-evident HMAC audit log chain
- **Budget-guarded** — wallet balance checked before execution
- **Compliant** — policy packs, PHI/PII redaction, content safety

## Requirements

- Python 3.9+
- `httpx>=0.27`
- `pydantic>=2.0`
