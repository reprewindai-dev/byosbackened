# Veklom Developer Tools Catalog

Veklom supports the languages and tools your team already uses. Every SDK wraps the same governed inference engine — your prompts, your audit trail, your compliance — from any language.

---

## By Language

### 🐍 Python

| Tool | Type | Install | Description |
|---|---|---|---|
| Veklom SDK for Python | SDK | `pip install veklom` | Official Python client for governed inference, audit logging, model routing, and compliance via the Veklom API |
| Veklom Toolkit for VS Code | IDE Plugin | [coming soon] | Prompt testing, audit log inspector, deployment manager inside VS Code |
| Veklom Toolkit for PyCharm | IDE Plugin | [coming soon] | Same as VS Code toolkit — for PyCharm and all JetBrains IDEs |
| Veklom Powertools for Python | Framework | `pip install veklom-powertools` | Lambda-style utilities: structured logging, tracing, audit chain, budget guard |

### 🟨 JavaScript / TypeScript

| Tool | Type | Install | Description |
|---|---|---|---|
| Veklom SDK for JavaScript | SDK | `npm install @veklom/sdk` | Official JS/TS client — works in Node.js and browser. Full type safety with TypeScript. |
| Veklom Toolkit for VS Code | IDE Plugin | [coming soon] | Shared with Python toolkit — covers JS/TS projects too |

### ☕ Java

| Tool | Type | Install | Description |
|---|---|---|---|
| Veklom SDK for Java | SDK | Maven/Gradle [coming soon] | Official Java client for governed inference and audit logging |
| Veklom Toolkit for IntelliJ IDEA | IDE Plugin | [coming soon] | Prompt testing and audit inspection inside IntelliJ |

### 🔷 .NET / C#

| Tool | Type | Install | Description |
|---|---|---|---|
| Veklom SDK for .NET | SDK | NuGet [coming soon] | Official .NET client — full async/await support |
| Veklom Toolkit for Visual Studio | IDE Plugin | [coming soon] | Governed inference testing inside Visual Studio |

### 🐹 Go

| Tool | Type | Install | Description |
|---|---|---|---|
| Veklom SDK for Go | SDK | `go get github.com/veklom/sdk-go` [coming soon] | Idiomatic Go client for governed inference and audit |

---

## API Base

All SDKs point to: `https://api.veklom.com/api/v1`

Auth: JWT (access token 60min, refresh 7d) or API key via `Authorization: Bearer <token>`

---

## Quick Start (Python)

```python
from veklom import VeklomClient

client = VeklomClient(api_key="your-api-key")

response = client.complete(
    prompt="Summarize this contract clause:",
    model="qwen2.5:1.5b"
)

print(response.text)
print(response.audit_log_id)  # tamper-evident log entry
print(response.provider)      # ollama | groq
```

---

## Quick Start (JavaScript)

```typescript
import { VeklomClient } from '@veklom/sdk';

const client = new VeklomClient({ apiKey: 'your-api-key' });

const response = await client.complete({
  prompt: 'Summarize this contract clause:',
  model: 'qwen2.5:1.5b',
});

console.log(response.text);
console.log(response.auditLogId);
console.log(response.provider);
```
