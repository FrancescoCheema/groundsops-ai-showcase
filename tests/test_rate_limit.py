from groundsops.rate_limit import SlidingWindowRateLimiter


def test_sliding_window_rate_limiter_recovers_after_window():
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=10)

    assert limiter.allow("client", now=0) == (True, 0)
    assert limiter.allow("client", now=1) == (True, 0)
    allowed, retry_after = limiter.allow("client", now=2)
    assert allowed is False
    assert retry_after > 0
    assert limiter.allow("client", now=11) == (True, 0)
