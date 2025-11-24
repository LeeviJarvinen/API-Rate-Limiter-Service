from fastapi import FastAPI, Depends, HTTPException, Request
from limiter import TokenBucketRateLimiter

app = FastAPI()
limiter = TokenBucketRateLimiter()


@app.get("/word")
@limiter.limit(max_token_capacity=100, refill_rate=10, token_cost=1)
def word_of_the_day():
    return {"word": "Galaxy"}

@app.get("/public")
def public_endpoint():
    return {"message": "no rate limit here"}
