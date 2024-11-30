import time
from abc import ABC, abstractmethod

import redis
from redis_conf import *


class AbsCacheProxy(ABC):

    @abstractmethod
    def set(self, name: str, value: str | bytes, ex: int | None = None):
        raise NotImplementedError

    @abstractmethod
    def get(self, name: str) -> bytes | None:
        raise NotImplementedError


class MemoryCacheProxy(AbsCacheProxy):
    def __init__(self):
        self.cache: dict[str, bytes] = dict()
        self.ex: dict[str, (int, int)] = dict()

    def set(self, name: str, value: str | bytes, ex: int | None = None):
        if type(value) is str:
            self.cache[name] = value.encode('utf-8')
        elif type(value) is bytes:
            self.cache[name] = value
        else:
            raise TypeError(f'Value type not str or bytes.')
        if ex:
            self.ex[name] = int(time.time()), ex

    def get(self, name: str) -> bytes | None:
        if name not in self.cache:
            return None
        if name not in self.ex:
            return self.cache[name]
        st, ex = self.ex[name]
        now = int(time.time())
        if now - st >= ex:
            del self.cache[name]
            del self.ex[name]
            return None
        else:
            return self.cache[name]


class RedisCacheProxy(AbsCacheProxy):

    def __init__(self):
        super().__init__()
        self.redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

    def set(self, name: str, value: str | bytes, ex: int | None = None):
        self.redis_conn.set(name, value, ex=ex)

    def get(self, name: str) -> bytes | None:
        return self.redis_conn.get(name)
