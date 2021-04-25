import asyncio
import functools
from typing import Dict, String

import asyncpg
from asyncpg.pool import Pool
from discord.ext import commands

from ..objects import DottedDict


class Database:
    def connect(coroutine):
        @functools.wraps(coroutine)
        async def predicate(self, *args, **kwargs):
            async with self.pool.acquire() as conn:
                return await coroutine(self, conn, *args, **kwargs)
        return predicate

    def __init__(self,
                 *, bot: commands.Bot,
                 config: Dict,
                 init_statement: String,
                 ):
        self.bot = bot
        self.config = config.get("database", config)
        self.init_statement = init_statement

        self._loop = asyncio.get_event_loop()
        self._cache_ready = asyncio.Event()
        self.cache = DottedDict()
        self.pool: Pool = None

        self._loop.create_task(self.__core_ainit__())

    async def __core_ainit__(self):
        self.pool = await asyncpg.create_pool(**self.config)

        async with self.pool.acquire() as conn:
            await conn.execute(self.init_statement)
        await self.bot.wait_until_ready()
        await self.init_cache()

    async def wait_until_ready(self):
        return await self._cache_ready.wait()

    @connect
    async def init_cache(self, conn):
        raise NotImplementedError(f"{self.__class__.__name__}.init_cache")

    @connect
    async def save_cache(self, conn):
        raise NotImplementedError(f"{self.__class__.__name__}.save_cache")

    async def close(self):
        await self.wait_until_ready()
        await self.save_cache()
        await self.pool.close()


def create(*args, **kwargs):
    return Database(*args, **kwargs)
