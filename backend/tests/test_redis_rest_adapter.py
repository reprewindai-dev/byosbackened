from core.redis_pool import RestRedisAdapter


class FakeRestRedis:
    def __init__(self):
        self.values = {}
        self.expirations = {}

    def incr(self, key):
        self.values[key] = int(self.values.get(key, 0)) + 1
        return self.values[key]

    def expire(self, key, seconds):
        self.expirations[key] = seconds
        return True

    def set(self, key, value, ex=None):
        self.values[key] = value
        if ex:
            self.expirations[key] = ex
        return True

    def get(self, key):
        return self.values.get(key)


def test_rest_redis_adapter_pipeline_matches_needed_rate_limit_api():
    client = RestRedisAdapter(FakeRestRedis())
    pipe = client.pipeline()
    pipe.incr("@upstash/ratelimit:ip:test")
    pipe.expire("@upstash/ratelimit:ip:test", 60)

    assert pipe.execute() == [1, True]
