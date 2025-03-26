import json
from contextlib import asynccontextmanager

import asyncpg


def print_query(query, args, executed):
    if args:
        args = f', {args=}'
    else:
        args = ''
    print(f'\033[33mQUERY{executed}: {query}{args}\033[0m\n')


class ConnectWrapper:
    def __init__(self, con, args):
        self.con = con
        self.args = args

    def show_query(self, query, args, readonly):
        if not self.args.echo_queries:
            return
        if readonly:
            return
        executed = ' (not executed)' if self.args.dry_run and not readonly else ''
        print_query(query, args, executed)

    async def execute(self, query, *args, readonly=False):
        if not query:
            return
        self.show_query(query, args, readonly)
        if not self.args.dry_run or readonly:
            return await self.con.execute(query, *args)

    async def fetch(self, query, *args, readonly=False):
        self.show_query(query, args, readonly)
        if not self.args.dry_run or readonly:
            return await self.con.fetch(query, *args)

    async def fetchrow(self, query, *args, readonly=False):
        self.show_query(query, args, readonly)
        if not self.args.dry_run or readonly:
            return await self.con.fetchrow(query, *args)

    async def fetchval(self, query, *args, readonly=False):
        res = await self.fetchrow(query, *args, readonly=readonly)
        if res:
            return res[0]


class PgPool:
    pool: asyncpg.Pool

    def __init__(self, args):
        self.args = args

    async def init_pool(self) -> None:
        async def init_connection(con):
            con._reset_query = ''
            await con.set_type_codec(
                typename="json",
                schema="pg_catalog",
                encoder=lambda x: x,
                decoder=json.loads,
            )
            await con.execute(f"set lock_timeout = '{self.args.lock_timeout}s';")
            await con.execute(f"set maintenance_work_mem = '{self.args.maintenance_work_mem}';")
            if self.args.max_parallel_maintenance_workers is not None:
                await con.execute(f"set max_parallel_maintenance_workers = "
                                  f"'{self.args.max_parallel_maintenance_workers}';")

        self.pool = await asyncpg.create_pool(
            database=self.args.dbname,
            user=self.args.user,
            password=self.args.password,
            host=self.args.host,
            port=self.args.port,
            min_size=max(self.args.copy_data_jobs, self.args.create_index_jobs),
            max_size=max(self.args.copy_data_jobs, self.args.create_index_jobs),
            statement_cache_size=0,
            init=init_connection
        )

    def show_query(self, query, args, readonly):
        if not self.args.echo_queries:
            return
        if readonly:
            return
        executed = ' (not executed)' if self.args.dry_run and not readonly else ''
        print_query(query, args, executed)

    async def execute(self, query, *args, readonly=False):
        if not query:
            return
        async with self.pool.acquire() as con:
            self.show_query(query, args, readonly)
            if not self.args.dry_run or readonly:
                return await con.execute(query, *args)

    async def fetch(self, query, *args, readonly=False):
        async with self.pool.acquire() as con:
            self.show_query(query, args, readonly)
            if not self.args.dry_run or readonly:
                return await con.fetch(query, *args)

    async def fetchrow(self, query, *args, readonly=False):
        async with self.pool.acquire() as con:
            self.show_query(query, args, readonly)
            if not self.args.dry_run or readonly:
                return await con.fetchrow(query, *args)

    async def fetchval(self, query, *args, readonly=False):
        res = await self.fetchrow(query, *args, readonly=readonly)
        if res:
            return res[0]

    @asynccontextmanager
    async def transaction(self) -> asyncpg.Connection:
        async with self.pool.acquire() as con:
            async with con.transaction():
                yield ConnectWrapper(con, self.args)
