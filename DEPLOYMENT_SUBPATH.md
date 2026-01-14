# Subpath Deployment Guide

This project has been configured to run under `/regos-partner-bot/` on your existing server.

## Changes Made

### 1. Frontend Build Configurations
- **`telegram-webapp/vite.config.ts`**: Added `base: '/regos-partner-bot/mini-app/'`
- **`frontend/vite.config.ts`**: Added `base: '/regos-partner-bot/admin/'`
- Updated proxy configurations to handle the subpath

### 2. API Base URLs
- **`frontend/src/services/api.ts`**: Changed base URL to `/regos-partner-bot/api`
- **`telegram-webapp/src/utils/api.ts`**: Created new API utility with base path `/regos-partner-bot/api`
- Updated all fetch calls in telegram webapp components to use the new `apiFetch` utility

### 3. FastAPI Configuration
- **`main.py`**: Added `root_path="/regos-partner-bot/api"` to FastAPI app

### 4. React Router
- **`frontend/src/App.tsx`**: Added `basename="/regos-partner-bot/admin"` to BrowserRouter

### 5. Environment Variables
- **`env.example`**: Updated with subpath-aware webhook URL

## Next Steps

### 1. Build Frontend Applications

```bash
# Build telegram webapp
cd telegram-webapp
npm install
npm run build

# Build admin panel
cd ../frontend
npm install
npm run build
```

### 2. Add Nginx Configuration

Add these location blocks to your existing nginx configuration:

```nginx
# Regos Partner Bot - Telegram WebApp
location /regos-partner-bot/mini-app {
    alias /path/to/your/project/telegram-webapp/dist;
    try_files $uri $uri/ /regos-partner-bot/mini-app/index.html;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}

# Regos Partner Bot - Admin Panel
location /regos-partner-bot/admin {
    alias /path/to/your/project/frontend/dist;
    try_files $uri $uri/ /regos-partner-bot/admin/index.html;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}

# Regos Partner Bot - API
location /regos-partner-bot/api {
    proxy_pass http://localhost:8000;  # Or your FastAPI backend URL
    proxy_http_version 1.1;
    
    # CRITICAL: Forward Authorization header for JWT authentication
    proxy_set_header Authorization $http_authorization;
    
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Script-Name /regos-partner-bot/api;  # Important for FastAPI root_path
    proxy_cache_bypass $http_upgrade;
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
}

# Regos Partner Bot - Webhooks
location /regos-partner-bot/webhook {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
}

location /regos-partner-bot/regos/webhook {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
}
```

**Important**: Replace `/path/to/your/project/` with the actual path to your project directory.

### 3. Configure Environment Variables

Create a `.env` file (or update your existing one):

```bash
WEBHOOK_BASE_URL=https://mydomain.com/regos-partner-bot
DATABASE_PATH=/path/to/your/data/telegram_bots.db
CORS_ORIGINS=https://mydomain.com
```

### 4. Start FastAPI Backend

Make sure your FastAPI backend is running on port 8000 (or update the nginx proxy_pass accordingly):

```bash
# Using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000

# Or using your existing process manager (systemd, supervisor, etc.)
```

### 5. Reload Nginx

After adding the configuration:

```bash
sudo nginx -t  # Test configuration
sudo systemctl reload nginx  # Or: sudo service nginx reload
```

## Access URLs

After deployment, your application will be accessible at:

- **Telegram WebApp**: `https://mydomain.com/regos-partner-bot/mini-app`
- **Admin Panel**: `https://mydomain.com/regos-partner-bot/admin`
- **API**: `https://mydomain.com/regos-partner-bot/api`
- **Webhooks**: `https://mydomain.com/regos-partner-bot/webhook/{token_prefix}`

## Verification

1. **Check API**: Visit `https://mydomain.com/regos-partner-bot/api/health` - should return `{"status": "healthy", ...}`
2. **Check Admin Panel**: Visit `https://mydomain.com/regos-partner-bot/admin` - should load the login page
3. **Check Telegram WebApp**: Visit `https://mydomain.com/regos-partner-bot/mini-app` - should load the app (may show error if not opened from Telegram)

## Troubleshooting

### 404 Errors
- Verify nginx configuration paths match your actual file locations
- Check that `try_files` directive includes the correct fallback path
- Ensure FastAPI `root_path` matches the nginx location path

### API Not Working
- Verify FastAPI is running and accessible
- Check nginx proxy_pass URL is correct
- Ensure `X-Script-Name` header is set in nginx config
- Check FastAPI logs for errors

### Static Files Not Loading
- Verify build outputs are in the correct directories
- Check nginx `alias` paths are correct
- Ensure file permissions allow nginx to read files

### CORS Errors
- Update `CORS_ORIGINS` in `.env` to include your domain
- Restart FastAPI after changing environment variables

## Notes

- Your existing app at `https://mydomain.com` and `https://mydomain.com/api` will remain unchanged
- The subpath configuration is completely isolated from your existing application
- All API routes are prefixed with `/regos-partner-bot/api`
- Webhook URLs will be: `https://mydomain.com/regos-partner-bot/webhook/{token_prefix}`
