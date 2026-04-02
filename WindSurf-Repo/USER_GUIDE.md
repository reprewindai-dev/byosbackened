# BYOS AI Backend - Complete User Guide
=====================================

## Table of Contents
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Authentication](#authentication)
4. [Workspaces](#workspaces)
5. [AI Execution](#ai-execution)
6. [Billing & Costs](#billing--costs)
7. [Dashboard](#dashboard)
8. [API Reference](#api-reference)
9. [Error Handling](#error-handling)
10. [Best Practices](#best-practices)

## Overview

The SOVEREIGN AI SAAS STACK is a premium, enterprise-grade AI backend system that provides:

- **20-Layer AI Governance Pipeline**: Advanced risk assessment and quality control
- **Multi-Provider AI Router**: Support for HuggingFace, OpenAI, and local LLMs
- **Production Billing System**: Complete Stripe integration with subscription management
- **Enterprise Security**: Zero-trust architecture with advanced middleware
- **Real-time Dashboard**: Premium admin control center with live monitoring
- **Cost Intelligence**: Per-operation tracking with budget controls

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database
- Redis server
- API keys for AI providers

### Installation

1. **Clone and Setup**
```bash
git clone <repository-url>
cd byos-ai-backend
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Database Setup**
```bash
# For PostgreSQL migration
python migrate_to_postgresql.py

# Or run Alembic directly
alembic upgrade head
```

4. **Start Server**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

5. **Access Documentation**
- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

## Authentication

### Registration
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "username",
    "password": "SecurePassword123!"
  }'
```

### Login
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "SecurePassword123!"
  }'
```

### Using the Token
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Workspaces

### Create Workspace
```bash
curl -X POST "http://localhost:8000/api/v1/workspaces" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My AI Workspace",
    "description": "Workspace for AI projects"
  }'
```

### List Workspaces
```bash
curl -X GET "http://localhost:8000/api/v1/workspaces" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Workspace
```bash
curl -X PUT "http://localhost:8000/api/v1/workspaces/{workspace_id}" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Workspace Name"
  }'
```

## AI Execution

### Available Providers
- **HuggingFace**: Free tier models for chat, sentiment, embeddings, etc.
- **OpenAI**: GPT models (API key required)
- **Local LLM**: Self-hosted models

### Execute AI Operation

#### Sentiment Analysis
```bash
curl -X POST "http://localhost:8000/api/v1/ai/execute" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "huggingface",
    "model": "distilbert-base-uncased-finetuned-sst-2-english",
    "operation": "sentiment",
    "prompt": "I love this product!"
  }'
```

#### Chat Completion
```bash
curl -X POST "http://localhost:8000/api/v1/ai/execute" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "huggingface",
    "model": "mistralai/Mistral-7B-Instruct-v0.3",
    "operation": "chat",
    "prompt": "Hello, how are you?"
  }'
```

#### Text Embedding
```bash
curl -X POST "http://localhost:8000/api/v1/ai/execute" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "huggingface",
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "operation": "embed",
    "prompt": "This is a test sentence for embedding."
  }'
```

### List Available Providers
```bash
curl -X GET "http://localhost:8000/api/v1/ai/providers" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Billing & Costs

### Get Billing Report
```bash
curl -X GET "http://localhost:8000/api/v1/billing/report" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Cost Allocation
```bash
curl -X POST "http://localhost:8000/api/v1/billing/allocate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": "workspace_123",
    "cost": 0.01,
    "operation": "ai_execution",
    "provider": "huggingface",
    "model": "sentiment-model"
  }'
```

### Cost History
```bash
curl -X GET "http://localhost:8000/api/v1/cost/history" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Dashboard

### Get Dashboard Stats
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/stats" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### System Status
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/system-status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Recent Activity
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/recent-activity" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Budget Status
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/budget-status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## API Reference

### Response Format

#### Success Response
```json
{
  "data": { ... },
  "message": "Operation completed successfully",
  "timestamp": "2026-02-25T15:30:00Z"
}
```

#### Error Response
```json
{
  "detail": "Error description",
  "error_code": "VALIDATION_ERROR",
  "timestamp": "2026-02-25T15:30:00Z",
  "request_id": "req_123456789"
}
```

#### Paginated Response
```json
{
  "items": [ ... ],
  "total": 100,
  "page": 1,
  "size": 20,
  "pages": 5
}
```

### Rate Limiting
- **Standard Users**: 100 requests/minute
- **Premium Users**: 1,000 requests/minute
- **Enterprise Users**: 10,000 requests/minute

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Total requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Time when limit resets

## Error Handling

### Common HTTP Status Codes

| Status Code | Description | Example |
|-------------|-------------|---------|
| 200 | Success | Request completed successfully |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Invalid or missing authentication |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource does not exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error occurred |

### Error Response Structure
```json
{
  "detail": "Detailed error message",
  "error_code": "MACHINE_READABLE_CODE",
  "timestamp": "2026-02-25T15:30:00Z",
  "request_id": "unique_request_identifier"
}
```

## Best Practices

### 1. Authentication
- Always use HTTPS in production
- Store JWT tokens securely
- Implement token refresh logic
- Handle token expiration gracefully

### 2. API Usage
- Check rate limit headers
- Implement exponential backoff for retries
- Use appropriate HTTP methods
- Validate responses before processing

### 3. Error Handling
- Always check HTTP status codes
- Parse error responses for debugging
- Implement proper logging
- Handle network timeouts

### 4. Performance
- Use caching for frequently accessed data
- Implement request batching when possible
- Monitor API usage and costs
- Optimize payload sizes

### 5. Security
- Never expose API keys in client code
- Validate all input parameters
- Use workspace-scoped operations
- Monitor for unusual activity

## SDK Examples

### Python SDK
```python
import requests

class SOVEREIGNAIClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def execute_ai(self, provider, model, operation, prompt):
        url = f"{self.base_url}/api/v1/ai/execute"
        payload = {
            "provider": provider,
            "model": model,
            "operation": operation,
            "prompt": prompt
        }
        response = requests.post(url, json=payload, headers=self.headers)
        return response.json()
    
    def get_dashboard_stats(self):
        url = f"{self.base_url}/api/v1/dashboard/stats"
        response = requests.get(url, headers=self.headers)
        return response.json()

# Usage
client = SOVEREIGNAIClient("http://localhost:8000", "your_jwt_token")
result = client.execute_ai("huggingface", "sentiment-model", "sentiment", "Great product!")
print(result)
```

### JavaScript SDK
```javascript
class SOVEREIGNAIClient {
    constructor(baseURL, apiKey) {
        this.baseURL = baseURL;
        this.apiKey = apiKey;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }
    
    async executeAI(provider, model, operation, prompt) {
        const response = await fetch(`${this.baseURL}/api/v1/ai/execute`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                provider,
                model,
                operation,
                prompt
            })
        });
        return response.json();
    }
    
    async getDashboardStats() {
        const response = await fetch(`${this.baseURL}/api/v1/dashboard/stats`, {
            headers: this.headers
        });
        return response.json();
    }
}

// Usage
const client = new SOVEREIGNAIClient('http://localhost:8000', 'your_jwt_token');
client.executeAI('huggingface', 'sentiment-model', 'sentiment', 'Great product!')
    .then(result => console.log(result));
```

## Support

- **Documentation**: https://docs.sovereign-ai.com
- **API Reference**: http://localhost:8000/api/v1/docs
- **Support Email**: support@sovereign-ai.com
- **Status Page**: https://status.sovereign-ai.com
- **GitHub Issues**: https://github.com/sovereign-ai/backend/issues

## Changelog

### v1.0.0 (2026-02-25)
- Initial production release
- 20-layer AI governance pipeline
- Multi-provider AI routing
- Complete billing system
- Enhanced security features
- Real-time dashboard
- Comprehensive API documentation
