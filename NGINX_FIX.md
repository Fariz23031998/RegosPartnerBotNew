# Nginx Configuration Fix for Authentication

## Problem
After successful login, subsequent API requests return 401 Unauthorized because nginx is not forwarding the `Authorization` header to the backend.

## Solution

Add the `Authorization` header forwarding to your nginx configuration for the API location block.

### Update Your Nginx Configuration

In your nginx configuration file (usually `/etc/nginx/sites-available/your-site` or in your server block), update the `/regos-partner-bot/api` location block:

```nginx
# Regos Partner Bot - API
location /regos-partner-bot/api {
    proxy_pass http://localhost:8000;  # Or your FastAPI backend URL
    proxy_http_version 1.1;
    
    # CRITICAL: Forward Authorization header
    proxy_set_header Authorization $http_authorization;
    
    # Forward other headers
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Script-Name /regos-partner-bot/api;  # Important for FastAPI root_path
    
    # CORS headers (if needed)
    proxy_set_header Access-Control-Request-Method $request_method;
    proxy_set_header Access-Control-Request-Headers $http_access_control_request_headers;
    
    proxy_cache_bypass $http_upgrade;
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
}
```

### Alternative: Forward All Headers

If you want to forward all headers (simpler but less secure), you can use:

```nginx
location /regos-partner-bot/api {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    
    # Forward all headers
    proxy_pass_request_headers on;
    
    # Explicitly forward Authorization
    proxy_set_header Authorization $http_authorization;
    
    # Standard proxy headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Script-Name /regos-partner-bot/api;
    
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
}
```

## Additional CORS Configuration

Make sure your FastAPI backend has the correct CORS origins set. In your production environment, set the `CORS_ORIGINS` environment variable:

```bash
# In your .env file or systemd service file
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

Or if you're using systemd, add it to your service file:

```ini
[Service]
Environment="CORS_ORIGINS=https://yourdomain.com"
```

## Steps to Apply

1. **Edit your nginx configuration:**
   ```bash
   sudo nano /etc/nginx/sites-available/your-site
   # or
   sudo nano /etc/nginx/nginx.conf
   ```

2. **Add the Authorization header forwarding** to the `/regos-partner-bot/api` location block as shown above.

3. **Test the configuration:**
   ```bash
   sudo nginx -t
   ```

4. **Reload nginx:**
   ```bash
   sudo systemctl reload nginx
   # or
   sudo service nginx reload
   ```

5. **Restart your FastAPI application** to ensure CORS settings are loaded:
   ```bash
   sudo systemctl restart your-fastapi-service
   ```

## Verify It's Working

After applying the fix, check the nginx error logs to see if requests are being forwarded correctly:

```bash
sudo tail -f /var/log/nginx/error.log
```

And check your FastAPI logs to see if the Authorization header is being received:

```bash
# Check your uvicorn/systemd logs
sudo journalctl -u your-fastapi-service -f
```

## Common Issues

1. **Still getting 401 errors:**
   - Verify the Authorization header is being sent from the browser (check Network tab in DevTools)
   - Check that `proxy_set_header Authorization $http_authorization;` is in the correct location block
   - Ensure there are no other nginx rules overriding this

2. **CORS errors:**
   - Make sure `CORS_ORIGINS` environment variable includes your domain
   - Check that `allow_credentials=True` is set in FastAPI CORS middleware
   - Verify the origin in the browser matches what's in CORS_ORIGINS

3. **Headers not being forwarded:**
   - Some nginx configurations have `underscores_in_headers off;` which can cause issues
   - Add `underscores_in_headers on;` to your http block if needed
