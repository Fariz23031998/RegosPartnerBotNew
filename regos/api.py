from typing import Any, Dict

import aiohttp
import json
import asyncio

import requests
from fastapi import HTTPException
import logging

from config import APP_NAME
from regos.regos_rate_limiter import RegosRateLimiter

logger = logging.getLogger(APP_NAME)

# Example global registry
regos_limiters: Dict[str, RegosRateLimiter] = {}

def get_regos_limiter(token: str) -> RegosRateLimiter:
    if token not in regos_limiters:
        regos_limiters[token] = RegosRateLimiter(rate=2, burst=50)
    return regos_limiters[token]


async def regos_async_api_request(
    endpoint: str,
    request_data: dict | list,
    token: str,
    timeout_seconds: int = 30,
) -> dict:
    """
    Make an asynchronous request to the REGOS API with built-in rate-limit handling.
    Args:
        endpoint: REGOS API endpoint path.
        request_data: Request payload.
        token: Integration token.
        timeout_seconds: Request timeout.
    Returns:
        dict[str, Any]: Parsed JSON response from REGOS.
    Raises:
        HTTPException: For client/network/API errors.
    """

    limiter = get_regos_limiter(token)
    await limiter.acquire()  # Wait for token before making request

    full_url = f"https://integration.regos.uz/gateway/out/{token}/v1/{endpoint}"
    headers = {"Content-Type": "application/json;charset=utf-8"}
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(full_url, headers=headers, data=json.dumps(request_data)) as response:
            if response.status == 429:
                # Safety: still retry with exponential backoff
                await asyncio.sleep(1)
                return await regos_async_api_request(endpoint, request_data, token, timeout_seconds)
            if response.status == 200:
                data = await response.json()
                if not data.get("ok"):
                    raise HTTPException(400, f"REGOS API error: {data}")
                return data
            raise HTTPException(502, f"REGOS API returned {response.status}")


def regos_api_request(endpoint: str, request_data: dict | list, token: str):
    """
       Make a synchronous request to the REGOS API.

       Parameters:
           endpoint (str): The specific API endpoint to call.
           request_data (dict | list): The data to send in the request body.
           token (str): Integration token.
           timeout_seconds (int): Timeout in seconds (default: 30).

       Returns:
           dict: The API response.

       Raises:
           HTTPException: For various API errors including timeouts, client errors, and non-200 status codes.
       """

    # Base endpoint URL
    full_url = f"https://integration.regos.uz/gateway/out/{token}/v1/{endpoint}"

    # Required headers
    headers = {
        "Content-Type": "application/json;charset=utf-8"
    }

    # Make the POST request
    response = requests.post(
        full_url,
        headers=headers,
        data=json.dumps(request_data)
    )

    # Check if response is successful (code 200)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Error: API returned status code {response.status_code}")
        return None

