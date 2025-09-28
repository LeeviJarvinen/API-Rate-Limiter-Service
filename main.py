from fixed_window_limiter import RateLimit, FixedWindowRateLimiter
import time
rate_limit = RateLimit(5,5)

limiter = FixedWindowRateLimiter()
user_1 = "user_1"
user_2 = "user_2"

print(limiter.is_allowed(user_1, rate_limit))
print(limiter.is_allowed(user_1, rate_limit))
print(limiter.is_allowed(user_1, rate_limit))
print(limiter.is_allowed(user_1, rate_limit))
print(limiter.is_allowed(user_1, rate_limit))
print(limiter.is_allowed(user_1, rate_limit))
print(limiter.is_allowed(user_1, rate_limit))
print(limiter.is_allowed(user_1, rate_limit))
print(limiter.is_allowed(user_1, rate_limit))
print(limiter.is_allowed(user_1, rate_limit))
print(limiter.clients)
time.sleep(1)
print(limiter.is_allowed(user_2, rate_limit))
time.sleep(6)
print(limiter.is_allowed(user_1, rate_limit))
print(limiter.is_allowed(user_2, rate_limit))
print(limiter.is_allowed(user_1, rate_limit))
print(limiter.is_allowed(user_1, rate_limit))
print(limiter.is_allowed(user_1, rate_limit))
print(limiter.is_allowed(user_2, rate_limit))
print(limiter.is_allowed(user_1, rate_limit))
print(limiter.is_allowed(user_2, rate_limit))

print(limiter.clients)
