# API Rate Limiter

A FastAPI application implementing multiple rate limiting strategies with Redis backend storage.

## Overview

This project provides a flexible rate limiting system for REST APIs with three different algorithms:

- **Fixed Window**: Limits requests within fixed time windows
- **Sliding Window**: Smooths traffic by weighing current and previous windows
- **Token Bucket**: Allows burst traffic with token-based refilling

## Features

- Multiple rate limiting algorithms
- Redis-backed storage for distributed systems
- Easy integration with FastAPI dependencies
- IP-based client identification
- Configurable rate limits per endpoint

## Requirements

- Python 3.7+
- Redis server running on localhost:6379

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
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

### Basic Example

The application includes a rate-limited endpoint:

```python
@app.get("/word", dependencies=[Depends(rate_limit_dependency)])
def word_of_the_day():
    return {"word": "Galaxy"}
```

This endpoint allows 10 requests per 60-second window per client IP.

### Rate Limiting Strategies

**Fixed Window**
```python
from limiter import FixedWindowRateLimiter, WindowRateLimit

limiter = FixedWindowRateLimiter()
rate_limit = WindowRateLimit(window_size=60, max_requests=10)

if limiter.is_allowed(client_id, rate_limit):
    # Process request
```

**Sliding Window**
```python
from limiter import SlidingWindowRateLimiter, WindowRateLimit

limiter = SlidingWindowRateLimiter()
rate_limit = WindowRateLimit(window_size=60, max_requests=10)

if limiter.is_allowed(client_id, rate_limit):
    # Process request
```

**Token Bucket**
```python
from limiter import TokenBucketRateLimiter, TokenRateLimit

limiter = TokenBucketRateLimiter()
rate_limit = TokenRateLimit(max_token_capacity=100, refill_rate=10)

if limiter.is_allowed(client_id, rate_limit, token_cost=1):
    # Process request
```

## API Endpoints

- `GET /word` - Rate limited endpoint (10 requests/minute)
- `GET /public` - Public endpoint without rate limiting

## Configuration

Modify rate limits in `main.py`:

```python
rate_limit = WindowRateLimit(
    window_size=60,      # Time window in seconds
    max_requests=10      # Maximum requests per window
)
```

For token bucket:

```python
rate_limit = TokenRateLimit(
    max_token_capacity=100,  # Maximum tokens in bucket
    refill_rate=10           # Tokens added per second
)
```

## Response Codes

- `200 OK` - Request successful
- `429 Too Many Requests` - Rate limit exceeded
