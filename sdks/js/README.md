# @veklom/sdk

Official JavaScript/TypeScript SDK for the [Veklom](https://veklom.com) governed inference platform.

## Install

```bash
npm install @veklom/sdk
# or
yarn add @veklom/sdk
```

## Quick Start

```typescript
import { VeklomClient } from '@veklom/sdk';

const client = new VeklomClient({ apiKey: 'your-api-key' });

const response = await client.complete({
  prompt: 'Summarize this contract clause:',
  model: 'qwen2.5:1.5b',
});

console.log(response.text);
console.log(response.auditLogId);  // tamper-evident audit chain entry
console.log(response.provider);    // 'ollama' | 'groq'
console.log(response.tokensUsed);
```

## Auth

Get your API key from [app.veklom.com/vault](https://app.veklom.com/vault).

## Requirements

- Node.js 18+ (uses native `fetch`)
- Works in modern browsers too
