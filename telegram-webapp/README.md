# Telegram Web App - Partner Documents

A React + TypeScript Telegram Web App that allows partners to view their purchase, wholesale, and payment documents.

## Features

- 🔐 Authentication via Telegram user ID (checked against `partner.oked` field)
- 📄 View purchase documents
- 📄 View purchase return documents
- 📄 View wholesale documents
- 📄 View wholesale return documents
- 💰 View payment documents (income and outcome)

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start development server:
```bash
npm run dev
```

The app will run on `http://localhost:5175` (different port from admin panel which runs on 5173)

## Building for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Backend API

The app requires the FastAPI backend to be running on `http://localhost:8000`.

### API Endpoints Used

- `GET /api/telegram-webapp/auth` - Authenticate Telegram user
- `GET /api/telegram-webapp/documents/purchase` - Get purchase documents
- `GET /api/telegram-webapp/documents/purchase-return` - Get purchase return documents
- `GET /api/telegram-webapp/documents/wholesale` - Get wholesale documents
- `GET /api/telegram-webapp/documents/wholesale-return` - Get wholesale return documents
- `GET /api/telegram-webapp/documents/payment` - Get payment documents

## Telegram Web App Setup

To use this as a Telegram Web App:

1. Build the app: `npm run build`
2. Deploy the `dist` folder to a web server
3. Set the web app URL in your Telegram bot using BotFather:
   - Use `/newapp` command
   - Provide the URL where your app is hosted

## Authentication

Users can only access the app if their Telegram user ID is stored in the `partner.oked` field in REGOS. The app automatically:

1. Gets the Telegram user ID from the Web App init data
2. Searches for a partner with matching Telegram ID in the `oked` field
3. If found, displays their documents
4. If not found, prompts for Partner ID (which will be verified)
