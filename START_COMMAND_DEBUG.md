# /start Command Debugging Guide

## Issue
The `/start` command doesn't work in the Telegram bot.

## Fixes Applied

### 1. Enhanced Error Handling
- Added try-catch blocks around `/start` command handling
- Added detailed logging at each step of the process
- Added error messages sent to users when something fails

### 2. Improved Logging
- Added logging for:
  - When `/start` command is received
  - When partner search is performed
  - When welcome message is sent
  - Any errors that occur during processing

### 3. Better Validation
- Added check for missing `chat_id` in messages
- Added validation for webhook processing

## How to Debug

### 1. Check Backend Logs
Look for these log messages when `/start` is sent:

```
INFO: Received webhook update for token prefix: ...
INFO: Processing update for bot: ...
INFO: Received message from chat ...: text='/start' ...
INFO: Handling /start command for chat ...
INFO: handle_start_command called: chat_id=..., has_regos_token=...
```

### 2. Check if Webhook is Receiving Updates
- Verify webhook URL is set correctly: Check bot settings in admin panel
- Test webhook manually: Send a test message to the bot and check logs
- Verify webhook path: Should be `/webhook/{token_prefix}` (first 10 chars of token)

### 3. Common Issues

#### Issue: Webhook not receiving updates
**Symptoms**: No logs when sending `/start`
**Solution**: 
- Check webhook URL in Telegram: `https://api.telegram.org/bot<TOKEN>/getWebhookInfo`
- Verify webhook URL matches your server: `https://your-domain.com/webhook/{token_prefix}`
- Check Nginx config routes `/webhook` to backend

#### Issue: Bot not found
**Symptoms**: "Bot not found for token prefix" in logs
**Solution**:
- Verify bot is active in database
- Check token prefix matches (first 10 characters)
- Ensure bot is registered on startup

#### Issue: REGOS token missing
**Symptoms**: "No REGOS integration token provided" in logs
**Solution**:
- Set `regos_integration_token` in bot settings via admin panel
- Verify token is valid and has access to Partner/Get endpoint

#### Issue: Message not sent
**Symptoms**: "Failed to send welcome message" in logs
**Solution**:
- Check Telegram API token is valid
- Verify bot has permission to send messages
- Check network connectivity to Telegram API

### 4. Test Steps

1. **Check webhook is set**:
   ```bash
   curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
   ```

2. **Send /start command** to the bot in Telegram

3. **Check backend logs** for:
   - Webhook received
   - Message processed
   - /start command handled
   - Welcome message sent

4. **Check for errors** in logs:
   - Any exceptions or error messages
   - Missing tokens or configuration
   - API call failures

### 5. Manual Test Endpoint

You can test the webhook endpoint manually:

```bash
curl -X POST https://your-domain.com/webhook/{token_prefix} \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 123456789,
    "message": {
      "message_id": 1,
      "from": {"id": 123456789, "first_name": "Test"},
      "chat": {"id": 123456789, "type": "private"},
      "date": 1234567890,
      "text": "/start"
    }
  }'
```

Replace `{token_prefix}` with the first 10 characters of your bot token.

## Expected Behavior

When `/start` is sent:

1. Bot receives webhook update
2. Bot checks if user is already registered (by Telegram chat ID in partner's `oked` field)
3. If registered: Sends "You are already registered" message
4. If not registered: Sends welcome message with "Share Contact" button
5. User clicks button and shares contact
6. Bot searches for partner by phone number
7. Bot updates partner's `oked` field with Telegram chat ID
8. Bot sends success message

## Files Modified

- `bot_manager.py`: Enhanced error handling and logging for `/start` command
- `main.py`: Better error handling in webhook handler

## Next Steps

1. Check backend logs when sending `/start` command
2. Verify webhook URL is correct
3. Verify bot is active and has REGOS token configured
4. Check for any error messages in logs
5. Test manually using curl if needed
