import datetime
import time


class DataCopier:
    def __init__(self, tat):
        self.tat = tat
        self.args = tat.args
        self.table = tat.table
        self.db = tat.db
        self.table_name = self.table['name']
        self.pk_columns = self.table['pk_columns']
        self.pk_types = self.table['pk_types']
        self.last_pk = None
        self.percent_stat_enable = (
            len(self.pk_columns) == 1 and
            self.pk_types[0] in ('integer', 'bigint') and
            self.args.batch_size != 0
        )
        self.stat_min_pk = 0
        self.stat_max_pk = 0
        self.stat_rows_count = 0
        self.stat_previous_rows_count = 0
        self.stat_last_time = time.time()

    def log(self, message):
        print(f'{self.table_name}: {message}')

    @staticmethod
    def duration(start_time):
        return str(datetime.timedelta(seconds=int(time.time() - start_time)))

    async def copy_data(self, i):
        ts = time.time()
        await self.get_stat_min_max_id()
        min_max_pks = ''
        if self.stat_max_pk:
            min_max_pks = f', pks: {self.stat_min_pk} - {self.stat_max_pk}'
        self.log(f'copy data {i}: start ({self.table["pretty_data_size"]}{min_max_pks})')
        if self.args.batch_size == 0:
            await self.copy_data_direct()
        else:
            await self.copy_data_batches()
        self.log(f'copy data {i}: done ({self.table["pretty_data_size"]}) in {self.duration(ts)}')

    async def copy_data_direct(self):
        column_names = self.tat.get_all_column_names()
        column_values = self.tat.get_all_column_values()

        await self.db.execute(
            f'''
            insert into {self.table_name}__tat_new({column_names})
              select {column_values}
                from only {self.table_name}
            '''.replace('            ', '')
        )

    async def copy_data_batches(self):
        last_batch_size = await self.copy_next_batch()
        while last_batch_size == self.args.batch_size:
            last_batch_size = await self.copy_next_batch()

    async def copy_next_batch(self):
        column_names = self.tat.get_all_column_names()
        column_values = self.tat.get_all_column_values()
        pk_columns = ', '.join(self.pk_columns)
        predicate = self.get_predicate()
        if len(self.pk_columns) == 1:
            select_query = f'''
                select max({self.pk_columns[0]}) as {self.pk_columns[0]}, count(1)
                  from batch
            '''
        else:
            select_query = f'''
                select {pk_columns}, count
                  from (select {pk_columns}, row_number() over (), count(1) over ()
                          from batch) x
                 where x.row_number = x.count
            '''
        batch = await self.db.fetchrow(
            f'''
            with batch as (
              insert into {self.table_name}__tat_new({column_names})
                select {column_values}
                  from only {self.table_name}
                 where {predicate}
                 order by {pk_columns}
                 limit {self.args.batch_size}
              returning {pk_columns}
            )
            {select_query}
            '''.replace('            ', '')
        )

        if batch is None or batch['count'] == 0:
            return 0
        self.last_pk = [batch[column] for column in self.pk_columns]
        self.print_stat(batch['count'])
        return batch['count']

    def get_last_pk_value(self, i):
        col_type = self.pk_types[i]
        if col_type in ['integer', 'bigint']:
            return str(self.last_pk[i])
        return f"'{self.last_pk[i]}'::{col_type}"

    def get_predicate(self):
        if self.last_pk is None:
            return 'true'
        if len(self.pk_columns) == 1:
            return f"{self.pk_columns[0]} > {self.get_last_pk_value(0)}"
        else:
            pk_columns = ', '.join(self.pk_columns)
            pk_values = ', '.join(self.get_last_pk_value(i) for i in range(len(self.pk_columns)))
            return f'({pk_columns}) > ({pk_values})'

    async def get_stat_min_max_id(self):
        if self.percent_stat_enable:
            self.stat_min_pk = await self.db.fetchval(
                f'''
                select min({self.pk_columns[0]})
                  from only {self.table_name}
                ''',
                readonly=True
            )
            self.stat_max_pk = await self.db.fetchval(
                f'''
                select max({self.pk_columns[0]})
                  from only {self.table_name}
                ''',
                readonly=True
            )

    def print_stat(self, count):
        if self.args.copy_progress_interval <= 0:
            return
        self.stat_rows_count += count
        if time.time() - self.stat_last_time > self.args.copy_progress_interval:
            rows_delta = self.stat_rows_count - self.stat_previous_rows_count
            time_delta = time.time() - self.stat_last_time
            last_pk = self.last_pk[0]
            percent = '-'
            if self.percent_stat_enable:
                total_pks = self.stat_max_pk - self.stat_min_pk
                processed_pks = (last_pk - self.stat_min_pk)
                percent = round(processed_pks * 100 / total_pks)
            speed = round(rows_delta / time_delta)
            self.log(f'copy data: stat (rows copied: {self.stat_rows_count}, last_pk: {last_pk}, '
                     f'{percent}%, {speed} rows/sec)')
            self.stat_last_time = time.time()
            self.stat_previous_rows_count = self.stat_rows_count
