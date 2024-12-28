import os
import time
from enum import Enum
from abc import ABC, abstractmethod
from threading import Lock

import redis
from redis_conf import *
from sqlalchemy import create_engine, text


class CacheLib(Enum):
    CONFIG = 'Config'
    RUNTIME = 'Runtime'


class AbsCacheProxy(ABC):

    @abstractmethod
    def set(self, name: str, value: str | bytes, ex: int | None = None, lib: CacheLib = CacheLib.CONFIG):
        raise NotImplementedError

    @abstractmethod
    def get(self, name: str, lib: CacheLib = CacheLib.CONFIG) -> bytes | None:
        raise NotImplementedError

    @abstractmethod
    def list_all(self, lib: CacheLib = CacheLib.CONFIG) -> list[tuple[str, str]]:
        raise NotImplementedError


def LockWrapper(func):
    def inner(self, *args, **kwargs):
        lock = self.lock
        lock.acquire()
        try:
            ret = func(self, *args, **kwargs)
            return ret
        finally:
            lock.release()
    return inner


class MemoryCacheProxy(AbsCacheProxy):
    def __init__(self):
        self.config_cache: dict[str, bytes] = dict()
        self.config_ex: dict[str, (int, int)] = dict()

        self.runtime_cache: dict[str, bytes] = dict()
        self.runtime_ex: dict[str, (int, int)] = dict()

        self.lock = Lock()

    @LockWrapper
    def set(self, name: str, value: str | bytes, ex: int | None = None, lib: CacheLib = CacheLib.CONFIG):
        cache = self.config_cache if lib == CacheLib.CONFIG else self.runtime_cache
        dex = self.config_ex if lib == CacheLib.CONFIG else self.runtime_ex

        if type(value) is str:
            cache[name] = value.encode('utf-8')
        elif type(value) is bytes:
            cache[name] = value
        else:
            raise TypeError(f'Value type not str or bytes.')

        if ex:
            dex[name] = int(time.time()), ex

    @LockWrapper
    def get(self, name: str, lib: CacheLib = CacheLib.CONFIG) -> bytes | None:
        cache = self.config_cache if lib == CacheLib.CONFIG else self.runtime_cache
        dex = self.config_ex if lib == CacheLib.CONFIG else self.runtime_ex

        if name not in cache:
            return None
        if name not in dex:
            return cache[name]
        st, ex = dex[name]
        now = int(time.time())
        if now - st >= ex:
            del cache[name]
            del dex[name]
            return None
        else:
            return cache[name]

    @LockWrapper
    def list_all(self, lib: CacheLib = CacheLib.CONFIG) -> list[tuple[str, str]]:
        cache = self.config_cache if lib == CacheLib.CONFIG else self.runtime_cache
        return [(k, v.decode()) for k, v in cache.items()]


class SQLiteCacheProxy(AbsCacheProxy):
    def __init__(self):
        # self.engine = create_engine("sqlite:///SQLite3CacheDb.db", connect_args={"check_same_thread": False})
        os.makedirs('./db', exist_ok=True)
        self.engine = create_engine("sqlite:///./db/SQLite3CacheDb.db")
        with self.engine.connect() as conn:
            conn.execute(text("CREATE TABLE if not exists config_cache(key TEXT PRIMARY KEY, value BLOB, set_time INTEGER, exp_time INTEGER)"))
            conn.execute(text("CREATE TABLE if not exists runtime_cache(key TEXT PRIMARY KEY, value BLOB, set_time INTEGER, exp_time INTEGER)"))

    def set(self, name: str, value: str | bytes, ex: int | None = None, lib: CacheLib = CacheLib.CONFIG):
        table_name = 'config_cache' if lib == CacheLib.CONFIG else 'runtime_cache'

        if type(value) is str:
            value = value.encode('utf-8')
        elif type(value) is bytes:
            pass
        else:
            raise TypeError(f'Value type not str or bytes.')

        now = int(time.time())
        if ex:
            ext = now + ex
        else:
            ext = 0

        with self.engine.connect() as conn:
            sql = f'INSERT OR REPLACE INTO {table_name} (key, value, set_time, exp_time) VALUES (:name, :value, :set_time, :exp_time);'
            conn.execute(text(sql), [{'name': name, 'value': value, 'set_time': now, 'exp_time': ext}])
            conn.commit()

    def get(self, name: str, lib: CacheLib = CacheLib.CONFIG) -> bytes | None:
        table_name = 'config_cache' if lib == CacheLib.CONFIG else 'runtime_cache'

        with self.engine.connect() as conn:
            fetch_result = conn.execute(text(f'select key from {table_name}'))
            keys = [row[0] for row in fetch_result.all()]
            if name not in keys:
                return None
            fetch_result = conn.execute(text(f'select * from {table_name} where key = :name'), [{'name': name}])
            key, value, _, ext = fetch_result.all()[0]
            if ext == 0:
                return value
            else:
                now = int(time.time())
                if now >= ext:
                    return None
                else:
                    return value

    def list_all(self, lib: CacheLib = CacheLib.CONFIG) -> list[tuple[str, str]]:
        table_name = 'config_cache' if lib == CacheLib.CONFIG else 'runtime_cache'

        with self.engine.connect() as conn:
            fetch_result = conn.execute(text(f'select * from {table_name}'))
            rows = fetch_result.all()
            ret = []
            now = int(time.time())
            for key, value, _, ext in rows:
                if ext == 0:
                    ret.append((key, value))
                else:
                    if now >= ext:
                        pass
                    else:
                        ret.append((key, value))
        return ret

    def close(self):
        self.engine.dispose()

    @LockWrapper
    def clear_expired_data(self) -> None:
        with self.engine.connect() as conn:
            fetch_result = conn.execute(text('select * from runtime_cache'))
            rows = fetch_result.all()
            expired = []
            now = int(time.time())
            for key, value, _, ext in rows:
                if ext == 0:
                    pass
                else:
                    if now >= ext:
                        expired.append(key)
                    else:
                        pass

            batch_size = 1000
            for i in range(0, len(expired), batch_size):
                batch = [{'key': key} for key in expired[i:i + batch_size]]
                conn.execute(text("delete from runtime_cache where key = :key;"), batch)
            conn.commit()


class RedisCacheProxy(AbsCacheProxy):

    def __init__(self):
        super().__init__()
        self.redis_conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

    def set(self, name: str, value: str | bytes, ex: int | None = None, lib: CacheLib = CacheLib.CONFIG):
        self.redis_conn.set(name, value, ex=ex)

    def get(self, name: str, lib: CacheLib = CacheLib.CONFIG) -> bytes | None:
        return self.redis_conn.get(name)

    def list_all(self, lib: CacheLib = CacheLib.CONFIG) -> list[tuple[str, str]]:
        return [(k, self.redis_conn.get(k).decode()) for k in self.redis_conn.keys()]  # maybe have better command ?
