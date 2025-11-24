# API Rate Limiter

A FastAPI application implementing token bucket rate limiting with Redis backend storage and decorator support.

## Overview

This project provides a flexible token bucket rate limiting system for REST APIs with decorator-based integration, allowing you to easily add rate limiting to any endpoint.

## Features

- **Token Bucket Algorithm**: Allows burst traffic with token-based refilling
- **Decorator Support**: Simple `@limiter.limit()` decorator for endpoints
- **Redis-backed Storage**: Distributed rate limiting across multiple instances
- **Easy Integration**: Works seamlessly with FastAPI
- **IP-based Client Identification**: Automatic client identification by IP
- **Configurable Rate Limits**: Different limits per endpoint
- **Async/Sync Support**: Works with both async and sync endpoints

## Requirements

- Python 3.7+
- Redis server running on localhost:6379
- FastAPI
- Redis Python client

## Installation

1. Install dependencies:
```bash
pip install fastapi redis uvicorn
```

2. Start Redis server:
```bash
redis-server
```

3. Run the application:
```bash
uvicorn main:app --reload
```

## Usage

### Basic Decorator Example
```python
from fastapi import FastAPI, Request
from limiter import TokenBucketRateLimiter

app = FastAPI()
limiter = TokenBucketRateLimiter()

@app.get("/word")
@limiter.limit(max_token_capacity=100, refill_rate=10, token_cost=1)
async def word_of_the_day(request: Request):
    return {"word": "Galaxy"}
```

### Token Bucket Parameters

- **max_token_capacity**: Maximum number of tokens in the bucket
- **refill_rate**: Tokens added per second
- **token_cost**: Tokens consumed per request (default: 1.0)

### Multiple Endpoints with Different Limits
```python
# Light endpoint - 100 tokens, refills at 10/second
@app.get("/light")
@limiter.limit(max_token_capacity=100, refill_rate=10)
async def light_endpoint(request: Request):
    return {"status": "ok"}

# Heavy endpoint - 50 tokens, refills at 5/second, costs 5 tokens per request
@app.post("/heavy")
@limiter.limit(max_token_capacity=50, refill_rate=5, token_cost=5)
async def heavy_endpoint(request: Request):
    return {"status": "processing"}

# No rate limit
@app.get("/public")
def public_endpoint():
    return {"message": "No rate limit here"}
```

### Direct Usage (Without Decorator)

You can still use the rate limiter directly:
```python
from limiter import TokenBucketRateLimiter, TokenRateLimit

limiter = TokenBucketRateLimiter()
rate_limit = TokenRateLimit(max_token_capacity=100, refill_rate=10)

if limiter.is_allowed(client_id, rate_limit, token_cost=1.0):
    # Process request
else:
    # Return 429 Too Many Requests
```

## How Token Bucket Works

The token bucket algorithm:
1. Each client has a bucket with a maximum capacity of tokens
2. Tokens are added to the bucket at a constant rate (refill_rate per second)
3. Each request consumes tokens (token_cost)
4. If enough tokens are available, the request is allowed
5. If not enough tokens, the request is denied with 429 status

**Example**: 
- `max_token_capacity=100`, `refill_rate=10`
- Bucket starts full with 100 tokens
- Client can make 100 requests instantly (burst)
- Then limited to 10 requests per second
- Bucket refills continuously at 10 tokens/second

## API Endpoints Example
```python
from fastapi import FastAPI, Request
from limiter import TokenBucketRateLimiter

app = FastAPI()
limiter = TokenBucketRateLimiter()

# Standard rate limit
@app.get("/word")
@limiter.limit(max_token_capacity=100, refill_rate=10)
async def word_of_the_day(request: Request):
    return {"word": "Galaxy"}

# No rate limit
@app.get("/public")
def public_endpoint():
    return {"message": "No rate limit here"}
```

## Configuration

### Redis Connection

Modify Redis connection in `limiter.py`:
```python
class RedisRateLimitStorage:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, decode_responses=True)
```

### Rate Limit Parameters

- **max_token_capacity**: Maximum tokens (e.g., 100 for burst capacity)
- **refill_rate**: Tokens per second (e.g., 10 = 10 requests/sec sustained)
- **token_cost**: Cost per request (e.g., 1 for normal, 5 for expensive operations)

## Response Codes

- `200 OK` - Request successful
- `429 Too Many Requests` - Rate limit exceeded

## Important Notes

- The decorator requires a `request: Request` parameter in your endpoint function
- Client identification is based on IP address (`request.client.host`)
- Rate limit data is stored in Redis with key format: `client:{client_id}`
- Works with both async and sync FastAPI endpoints
