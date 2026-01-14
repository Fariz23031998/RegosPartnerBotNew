# Debugging Authentication Issues

## Current Problem
After login succeeds (200 OK), subsequent API requests return 401 Unauthorized.

## Debugging Steps

### 1. Check Browser Console
The updated code now logs detailed information. Open your browser's Developer Tools (F12) and check the Console tab. You should see:
- `[API Request]` logs showing what headers are being sent
- `[API 401 Error]` logs showing what went wrong

### 2. Check Network Tab (Before Redirect)
The code now delays redirect by 2 seconds on 401 errors. To inspect:
1. Open DevTools (F12)
2. Go to Network tab
3. Try to login
4. When 401 occurs, you have 2 seconds to inspect the request
5. Look for the failed request and check:
   - **Request Headers** - Is `Authorization: Bearer <token>` present?
   - **Response Headers** - What does the server return?

### 3. Check Nginx Configuration

Verify your nginx config has the Authorization header forwarding:

```bash
sudo cat /etc/nginx/sites-available/your-site | grep -A 15 "location /regos-partner-bot/api"
```

Should include:
```nginx
proxy_set_header Authorization $http_authorization;
```

### 4. Test Direct Backend Access

Bypass nginx to test if the backend works:

```bash
# On your server, test directly
curl -X GET http://localhost:8000/api/users \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

If this works, the issue is nginx. If it doesn't, the issue is backend/CORS.

### 5. Check CORS Configuration

Verify CORS_ORIGINS is set correctly:

```bash
# Check your FastAPI process environment
sudo systemctl status your-fastapi-service
# or check the logs
sudo journalctl -u your-fastapi-service | grep CORS
```

The logs should show: `CORS origins configured: ['https://yourdomain.com']`

### 6. Check Nginx Error Logs

```bash
sudo tail -f /var/log/nginx/error.log
```

Look for any errors related to proxy or headers.

### 7. Check FastAPI Logs

```bash
sudo journalctl -u your-fastapi-service -f
# or if running with uvicorn directly
# check your uvicorn logs
```

Look for:
- CORS errors
- 401 errors with details
- Missing Authorization header warnings

## Common Issues and Solutions

### Issue 1: Authorization Header Not Forwarded
**Symptom**: Request has Authorization header in browser, but backend doesn't receive it.

**Solution**: Add to nginx config:
```nginx
proxy_set_header Authorization $http_authorization;
```

### Issue 2: CORS Preflight Failing
**Symptom**: OPTIONS request fails before actual request.

**Solution**: Ensure nginx allows OPTIONS:
```nginx
location /regos-partner-bot/api {
    # Handle preflight
    if ($request_method = 'OPTIONS') {
        add_header 'Access-Control-Allow-Origin' '$http_origin' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, PATCH, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
        add_header 'Access-Control-Max-Age' 1728000;
        add_header 'Content-Type' 'text/plain; charset=utf-8';
        add_header 'Content-Length' 0;
        return 204;
    }
    
    proxy_pass http://localhost:8000;
    # ... rest of config
}
```

### Issue 3: CORS Origins Not Set
**Symptom**: CORS errors in console, requests blocked.

**Solution**: Set environment variable:
```bash
export CORS_ORIGINS="https://yourdomain.com"
# Then restart FastAPI
```

### Issue 4: Token Not Stored
**Symptom**: Token exists after login but disappears.

**Solution**: Check browser localStorage:
```javascript
// In browser console
localStorage.getItem('token')
```

### Issue 5: Token Format Wrong
**Symptom**: Token exists but format is incorrect.

**Solution**: Check token format:
```javascript
// In browser console
const token = localStorage.getItem('token')
console.log('Token:', token)
console.log('Starts with Bearer?', token?.startsWith('Bearer'))
```

The token should NOT include "Bearer" - it should just be the JWT token itself.

## Quick Test Script

Add this to your browser console after logging in:

```javascript
// Test API call with current token
const token = localStorage.getItem('token')
console.log('Token:', token)

fetch('/regos-partner-bot/api/users', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
})
.then(r => r.json())
.then(data => console.log('Success:', data))
.catch(err => console.error('Error:', err))
```

This will help identify if:
- Token is present
- Request format is correct
- Issue is with axios or fetch

## Next Steps

After checking the console logs, share:
1. What `[API Request]` shows (especially the headers)
2. What `[API 401 Error]` shows
3. Network tab request headers (if you can capture them)
4. Your nginx configuration for `/regos-partner-bot/api`
5. Your CORS_ORIGINS environment variable value
