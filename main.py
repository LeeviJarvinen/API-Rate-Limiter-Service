from fastapi import FastAPI, Depends, HTTPException, Request
from limiter import FixedWindowRateLimiter, SlidingWindowRateLimiter, TokenBucketRateLimiter, WindowRateLimit, TokenRateLimit

app = FastAPI()
limiter = SlidingWindowRateLimiter()

def rate_limit_dependency(request: Request):
    """dependency to check rate_limit"""
    client_id = request.client.host
    rate_limit = WindowRateLimit(window_size=60, max_requests=10)

    if not limiter.is_allowed(client_id, rate_limit):
        raise HTTPException(status_code=429, detail="Too Many Requests")

    return True

@app.get("/word", dependencies=[Depends(rate_limit_dependency)])
def word_of_the_day():
    return {"word": "Galaxy"}

@app.get("/public")
def public_endpoint():
    return {"message": "no rate limit here"}
