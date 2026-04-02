# Backend API Server

A Node.js/Express backend API server.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create a `.env` file (already created) with:
```
PORT=3001
NODE_ENV=development
```

3. Start the server:
```bash
npm start
```

For development with auto-reload:
```bash
npm run dev
```

## API Endpoints

- `GET /` - Welcome message
- `GET /api/health` - Health check endpoint
- `GET /api/users` - Get all users
- `POST /api/users` - Create a new user

## Configuration

The server runs on port 3001 by default (configurable via PORT environment variable).
