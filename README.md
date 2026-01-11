# Telegram Bot Webhook Engine

A webhook-based Telegram bot engine using FastAPI that can operate multiple bots asynchronously. Features an admin panel built with React, TypeScript, and Vite for managing users and bot tokens.

## Features

- **Multi-bot support**: Operate multiple Telegram bots asynchronously
- **Webhook-based**: Uses Telegram webhooks for real-time updates
- **Database**: SQLAlchemy ORM with aiosqlite for token and user management
- **Admin Panel**: React-based admin interface for managing users and tokens
- **Authentication**: JWT-based authentication with admin login

## Tech Stack

### Backend
- FastAPI
- SQLAlchemy (async ORM)
- aiosqlite
- JWT authentication
- Python 3.8+

### Frontend
- React 18
- TypeScript
- Vite
- React Router
- Axios

## Setup

### Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the backend server:
```bash
python main.py
```

The backend will run on `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will run on `http://localhost:5173`

## Default Admin Credentials

- **Username**: `admin`
- **Password**: `masterkey`

## Database Schema

### Users Table
- `user_id` (Primary Key, Auto-increment)
- `username` (Unique, Optional)
- `email` (Unique, Optional)
- `created_at` (DateTime)

### Telegram Tokens Table
- `token_id` (Primary Key, Auto-increment)
- `user_id` (Foreign Key → users.user_id, CASCADE DELETE)
- `token` (Unique, Required)
- `bot_name` (Optional)
- `is_active` (Boolean, Default: True)
- `created_at` (DateTime)

## API Endpoints

### Authentication
- `POST /api/auth/login` - Admin login
- `GET /api/auth/me` - Get current user info

### Users (Protected)
- `GET /api/users` - Get all users
- `GET /api/users/{user_id}` - Get user by ID
- `POST /api/users` - Create user
- `DELETE /api/users/{user_id}` - Delete user

### Tokens (Protected)
- `GET /api/tokens` - Get all tokens
- `GET /api/tokens/{token_id}` - Get token by ID
- `GET /api/users/{user_id}/tokens` - Get tokens for a user
- `POST /api/tokens` - Create token
- `PATCH /api/tokens/{token_id}` - Update token
- `DELETE /api/tokens/{token_id}` - Delete token

### Webhooks (Public)
- `POST /webhook/{token_prefix}` - Telegram webhook endpoint

### Other
- `GET /api/bots` - Get registered bots info
- `GET /health` - Health check

## Configuration

Set environment variables for configuration:

- `WEBHOOK_BASE_URL` - Base URL for webhooks (default: "https://your-domain.com")
- `PORT` - Backend server port (default: 8000)
- `HOST` - Backend server host (default: "0.0.0.0")

## Development

### Backend
```bash
python main.py
```

### Frontend
```bash
cd frontend
npm run dev
```

## Building for Production

### Frontend
```bash
cd frontend
npm run build
```

The build output will be in `frontend/dist/`.

## Project Structure

```
.
├── database/
│   ├── __init__.py
│   ├── models.py          # SQLAlchemy ORM models
│   └── database.py        # Database operations
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── contexts/      # React contexts (Auth)
│   │   ├── pages/         # Page components
│   │   ├── services/      # API services
│   │   └── App.tsx        # Main app component
│   ├── package.json
│   └── vite.config.ts
├── auth.py                # Authentication logic
├── bot_manager.py         # Bot management
├── main.py                # FastAPI application
└── requirements.txt       # Python dependencies
```

## License

MIT

