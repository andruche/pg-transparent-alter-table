import asyncio
import os
import datetime
import time

from .pg_pool import PgPool


class Helper:
    db: PgPool
    table_name: str
    children: list

    async def pretty_size(self, size):
        return await self.db.fetchval('select pg_size_pretty($1::bigint)', size, readonly=True)

    @staticmethod
    def duration(start_time):
        return str(datetime.timedelta(seconds=int(time.time() - start_time)))

    def log(self, message):
        print(f'{self.table_name}: {message}')

    @staticmethod
    def log_border():
        print('-' * 50)

    async def cancel_autovacuum(self, con=None):
        if con is None:
            con = self.db
        tables_name = '|'.join(table.table_name for table in [self] + self.children)
        if await con.fetch(
            f'''
            select pg_cancel_backend(pid)
              from pg_stat_activity
             where state = 'active' and
                   backend_type = 'autovacuum worker' and
                   query ~ '{tables_name}';
            '''.replace('            ', '')
        ):
            self.log('autovacuum canceled')

    async def cancel_all_autovacuum(self, con):
        if await con.fetch(
            '''
            select pg_cancel_backend(pid)
              from pg_stat_activity
             where state = 'active' and
                   backend_type = 'autovacuum worker';
            '''.replace('            ', '')
        ):
            self.log('autovacuum canceled')

    @staticmethod
    def get_query(query_file_name):
        full_file_name = os.path.join(os.path.dirname(__file__), 'queries', query_file_name)
        return open(full_file_name).read()

    @staticmethod
    async def run_parallel(tasks, worker_count):
        async def worker():
            while tasks:
                task = tasks.pop(0)
                await task
        workers = [worker() for _ in range(worker_count)]
        await asyncio.gather(*workers)
