import asyncio
import os
import sys
import re
from contextlib import asynccontextmanager
import time
from enum import Enum
from typing import List

import asyncpg
from .acl import acl_to_grants

from .helper import Helper
from .data_copier import DataCopier
from .pg_pool import PgPool


class TableKind(Enum):
    regular = 'r'
    foreign = 'f'
    partitioned = 'p'


class TAT(Helper):
    children: List["TAT"]
    table_kind: TableKind

    def __init__(self, args, is_sub_table=False, pool=None, child_table_name=None):
        self.args = args
        self.is_sub_table = is_sub_table
        self.table = None
        self.sum_total_size_pretty = 0
        self.children = []
        self.commands = [
            command.strip('; \t')
            for command in self.args.command
            if ' move column ' not in command
        ]
        self.move_column_commands = [
            command.strip('; \t')
            for command in self.args.command
            if ' move column ' in command
        ]
        self.using_expr = self.get_alter_type_using_expr()

        self.db = pool or PgPool(args)
        self.child_table_name = child_table_name
        self.table_locked = False

    async def run(self):
        ts = time.time()
        await self.db.init_pool()
        await self.get_table_info()

        if self.args.cleanup:
            await self.cancel_autovacuum()
            await self.cleanup()
            return

        self.log(f'start ({self.sum_total_size_pretty})')
        self.check_sub_table()
        if not self.args.continue_switch_table:
            if not self.args.continue_create_indexes:
                await self.create_new_tables()
                await self.create_delta_tables()
                await self.copy_data()
            await self.create_indexes()
            await self.analyze()
        if self.args.no_switch_table:
            self.log('ready to --continue-switch-table')
            return
        await self.switch_table()
        await self.validate_constraints()
        self.log(f'done in {self.duration(ts)}\n')

    def get_table_name(self):
        command = (self.commands or self.move_column_commands)[0]
        match = re.match('alter table ([^ ]+) ', command)
        if not match:
            raise Exception(f'Table name cannot be extracted from the command: {command}')
        return match.group(1)

    def get_alter_type_using_expr(self):
        return {
            match.group(1): match.group(2)
            for command in self.commands
            if (match := re.match('.* alter column ([^ ]+) type .* using (.*);?', command))
        }

    async def get_table_info(self, table=None):
        children = []
        tables_data = {}
        if table:
            self.table = table
        else:
            command_table_name = self.get_table_name()
            db_table_name = await self.db.fetchval('select $1::regclass::text', command_table_name, readonly=True)
            children = await self.db.fetchval(
                self.get_query('get_child_tables.sql'),
                db_table_name,
                readonly=True
            )
            table_names = [db_table_name] + children
            tables_data = {
                table['name']: table
                for table in await self.db.fetch(
                    self.get_query('get_table_info.sql'),
                    table_names,
                    readonly=True
                )
            }
            self.table = tables_data[db_table_name]

        self.table_kind = TableKind(self.table['kind'])
        self.table_name = self.table['name']

        if not self.table['pk_columns'] and self.table_kind == TableKind.regular:
            print(f'table {self.table_name} does not have primary key or not null unique constraint', file=sys.stderr)
            exit(1)

        if not self.is_sub_table:  # all children are processing on root level
            self.children = [
                TAT(self.args, True, self.db, child_table_name=child)
                for child in children
            ]
            sum_size = self.table['total_size']
            for child in self.children:
                await child.get_table_info(tables_data[child.child_table_name])
                sum_size += child.table['total_size']
            self.sum_total_size_pretty = await self.pretty_size(sum_size)

    async def create_new_tables(self):
        self.log(f'create {self.table_name}__tat_new')
        query = f'\n\n'.join(
            table.create_new_table_query()
            for table in [self] + self.children
            if table.table_kind != TableKind.foreign
        )
        await self.db.execute(query)

    def get_alter_table_commands(self, postfix=''):
        for command in self.commands:
            command = re.sub('alter table [^ ]+ ', f'alter table {self.table_name}{postfix} ', command) + ';'
            if self.table_kind == TableKind.foreign:
                if ' set tablespace ' in command:
                    continue
                command = re.sub(f' using .*', '', command) + ';'
            yield command

    def apply_move_column_commands(self, columns):
        def parse_command(move_command):
            match = re.match('.* move column (.+) (before|after) ([^ ;]+)', move_command)
            if match:
                return match.groups()
            else:
                print(f"wrong format of command: {cmd}", file=sys.stderr)
                exit(1)

        columns = list(columns)
        for cmd in self.move_column_commands:
            target, placement, placeholder = parse_command(cmd)
            if target not in columns:
                print(f'moving column "{target}" not found in columns list: {columns}', file=sys.stderr)
                exit(1)
            if placeholder not in columns:
                print(f'placeholder column "{placeholder}" not found in columns list: {columns}', file=sys.stderr)
                exit(1)
            columns.remove(target)
            offset = 0 if placement == 'before' else 1
            columns.insert(columns.index(placeholder) + offset, target)
        return columns

    def create_new_table_query(self):
        column_names = self.apply_move_column_commands(self.table['all_columns'].keys())
        attr = self.table['all_columns']
        columns = ',\n              '.join(
            f'{col} {attr[col]["type"]}{attr[col]["collate"]}{attr[col]["not_null"]}{attr[col]["default"]}'
            for col in column_names
        )
        commands = [
            f'''
            create table {self.table_name}__tat_new(
              {columns}
            ){self.table['partition_expr'] or ''};
            '''.replace('            ', '')
        ]
        commands.extend(self.get_alter_table_commands('__tat_new'))
        commands.extend(self.table['create_check_constraints'])
        commands.extend(self.table['grant_privileges'])
        commands.append(self.table['comment'])
        for column in self.table['all_columns'].values():
            if column['comment']:
                commands.append(column['comment'])
        if self.table_kind == TableKind.regular:
            commands.append(f'alter table {self.table_name}__tat_new set (autovacuum_enabled = false);')
        if self.is_sub_table:
            parent = self.table['inherits'][0]
            if self.table['attach_expr']:
                expr = self.table["attach_expr"]
                commands.append(
                    f'alter table {parent}__tat_new attach partition {self.table_name}__tat_new {expr};'
                )
            else:
                commands.append(
                    f'alter table {self.table_name}__tat_new inherit {parent}__tat_new;'
                )
        return '\n'.join(command for command in commands if command)

    async def create_delta_tables(self):
        self.log(f'create {self.table_name}__tat_delta')
        query = f'\n\n'.join(
            table.create_delta_table_query()
            for table in [self] + self.children
            if table.table_kind == TableKind.regular
        )
        await self.db.execute(query)

        query = f'\n'.join(
            table.create_delta_trigger_query()
            for table in [self] + self.children
            if table.table_kind == TableKind.regular
        )
        await self.cancel_autovacuum()
        await self.db.execute(query)

    def create_delta_table_query(self):
        def apply_using_exp(column):
            if column in self.using_expr:
                return re.sub(f'\\b{column}\\b', f'r.{column}', self.using_expr[column])
            return f'r."{column}"'

        commands = [f'''
            create unlogged table {self.table_name}__tat_delta(
              like {self.table_name} excluding all
            );

            alter table {self.table_name}__tat_delta
              add column tat_delta_id serial,
              add column tat_delta_op "char";
        '''.replace('            ', '')]

        query = self.get_query('store_delta.plpgsql')
        commands.append(query.format(**self.table))

        columns = ', '.join(
            f'"{column}"'
            for column in self.table['all_columns']
        )
        val_columns = ', '.join(
            apply_using_exp(column)
            for column in self.table['all_columns']
        )
        where = ' and '.join(
            f't."{column}" = {apply_using_exp(column)}'
            for column in self.table['pk_columns']
        )
        set_columns = ', '.join(
            f'"{column}" = {apply_using_exp(column)}'
            for column in self.table['all_columns']
            if column not in self.table['pk_columns']
        )

        query = self.get_query('apply_delta.plpgsql')
        commands.append(query.format(**self.table, **locals()))
        return '\n'.join(commands)

    def create_delta_trigger_query(self):
        return f'''
            create trigger store__tat_delta
              after insert or update or delete on {self.table_name}
              for each row execute procedure "{self.table_name}__store_delta"();
        '''.replace('            ', '')

    def get_all_column_names(self):
        return ', '.join(f'"{column}"' for column in self.table['all_columns'])

    def get_all_column_values(self):
        return ', '.join(
            self.using_expr.get(column, f'"{column}"')
            for column in self.table['all_columns']
        )

    async def copy_data(self):
        ts = time.time()
        i = 0
        size = 0
        tasks = []
        if self.table_kind == TableKind.regular:
            i += 1
            size += self.table['data_size']
            copier = DataCopier(self)
            tasks.append(copier.copy_data(i))
        for child in self.children:
            if child.table_kind == TableKind.regular:
                i += 1
                size += child.table['data_size']
                copier = DataCopier(child)
                tasks.append(copier.copy_data(i))
        pretty_size = await self.pretty_size(size)
        self.log_border()
        self.log(f'copy data: start ({len(tasks)} tables on {self.args.copy_data_jobs} jobs, size: {pretty_size})')
        await self.run_parallel(tasks, self.args.copy_data_jobs)
        self.log(f'copy data: done in {self.duration(ts)}')

    async def create_indexes(self):
        ts = time.time()
        i = 0
        tasks = []
        for index_def in self.table['create_indexes']:
            i += 1
            tasks.append(self.create_index(index_def, i))
        for child in self.children:
            for index_def in child.table['create_indexes']:
                i += 1
                tasks.append(child.create_index(index_def, i))
        if not tasks:
            return
        self.log_border()
        self.log(f'create indexes: start ({len(tasks)} indexes on {self.args.create_index_jobs} jobs)')
        await self.run_parallel(tasks, self.args.create_index_jobs)
        self.log(f'create indexes: done in {self.duration(ts)}')

    async def create_index(self, index_def, i):
        ts = time.time()
        index_name = re.sub('CREATE U?N?I?Q?U?E? ?INDEX (.*) ON .*', '\\1', index_def)
        self.log(f'create index {i}: {index_name}: start')
        try:
            await self.db.execute(index_def)
        except asyncpg.exceptions.DuplicateTableError as e:
            if self.args.continue_create_indexes:
                self.log(f'create index {i}: {index_name}: skip: {str(e)}')
                return
            else:
                raise e
        self.log(f'create index {i}: {index_name}: done in {self.duration(ts)}')

    async def apply_all_delta(self, con=None):
        ts = time.time()
        self.log('apply_delta: start')
        rows = await self.apply_table_delta(con) or 0
        for child in self.children:
            rows += await child.apply_table_delta(con) or 0
        self.log(f'apply_delta: done: {rows} rows in {self.duration(ts)}')
        return rows

    async def apply_table_delta(self, con=None):
        if self.table_kind != TableKind.regular:
            return 0
        if con is None:
            con = self.db
        return await con.fetchval(f'select "{self.table_name}__apply_delta"();')

    async def analyze(self):
        ts = time.time()
        self.log('analyze: start')
        sys.stdout.flush()
        await self.db.execute(f'analyze {self.table_name}__tat_new')
        self.log(f'analyze: done in {self.duration(ts)}')

    @asynccontextmanager
    async def exclusive_lock_table(self):
        while True:
            async with self.db.transaction() as con:
                await self.cancel_autovacuum(con)
                self.log('lock table: start')
                parent = ''
                if self.table['inherits'] and not self.is_sub_table:
                    parent = f'{self.table["inherits"][0]}, '
                try:
                    await con.execute(f'lock table {parent}{self.table_name} in access exclusive mode;')
                    self.log('lock table: done')
                    self.table_locked = True
                    yield con
                    break
                except (
                    asyncpg.exceptions.LockNotAvailableError,
                    asyncpg.exceptions.DeadlockDetectedError
                ) as e:
                    if self.table_locked:
                        await con.execute('rollback;')
                        raise e
                    self.log(f'lock table: failed: {e}')
                    await con.execute('rollback;')
            await asyncio.sleep(self.args.time_between_locks)

    async def drop_depend_objects(self, con):
        await con.execute('\n'.join(self.table['drop_views']))
        await con.execute('\n'.join(self.table['drop_functions']))
        if self.table['drop_constraints']:
            await self.cancel_all_autovacuum(con)
        await con.execute('\n'.join(self.table['drop_constraints']))
        await con.execute('\n'.join(self.table['alter_sequences']))
        for child in self.children:
            await child.drop_depend_objects(con)

    async def detach_foreign_tables(self, con):
        if self.table_kind == TableKind.foreign:
            parent = self.table["inherits"][0]
            if self.table['attach_expr']:  # declarative partitioning
                self.log('detach foreign table')
                await con.execute(
                    f'alter table only {parent} detach partition {self.table_name};'
                )
            else:   # old style inherits partitioning
                self.log('no inherit foreign table')
                await con.execute(
                    f'alter table {self.table_name} no inherit {parent};'
                )
        for child in self.children:
            await child.detach_foreign_tables(con)

    async def attach_foreign_tables(self, con):
        if self.table_kind == TableKind.foreign:
            if self.commands:
                await con.execute('\n'.join(self.get_alter_table_commands()))
            parent = self.table['inherits'][0]
            if self.table['attach_expr']:  # declarative partitioning
                self.log('attach foreign table')
                expr = self.table["attach_expr"]
                await con.execute(
                    f'alter table {parent} attach partition {self.table_name} {expr}'
                )
            else:  # old style inherits partitioning
                self.log('inherit foreign table')
                await con.execute(
                    f'alter table {self.table_name} inherit {parent}'
                )
        for child in self.children:
            await child.attach_foreign_tables(con)

    async def drop_original_table(self, con):
        self.log('drop original table')
        if self.table_kind == TableKind.regular and self.children:  # old style inherits partitioning
            for child in reversed(self.children):
                if child.table_kind == TableKind.regular:
                    await con.execute(f'drop table {child.table_name};')
        await con.execute(f'drop table {self.table_name};')

    async def rename_tables(self, con):
        self.log(f'rename table {self.table_name}__tat_new -> {self.table_name}')
        query = f'\n\n'.join(
            table.rename_table_query()
            for table in [self] + self.children
            if table.table_kind != TableKind.foreign
        )
        await con.execute(query)

    async def attach_to_parent(self, con):
        if self.table['inherits'] and not self.is_sub_table:
            parent = self.table["inherits"][0]
            if self.table['attach_expr']:
                expr = self.table["attach_expr"]
                await con.execute(
                    f'alter table {parent} attach partition {self.table_name} {expr};'
                )
            else:
                await con.execute(
                    f'alter table {self.table_name} inherit {parent};'
                )

    def rename_table_query(self):
        commands = [f'alter table {self.table_name}__tat_new rename to {self.table["name_without_schema"]};']
        commands.extend(self.table['rename_indexes'])
        commands.extend(self.table['create_constraints'])
        commands.extend(self.table['create_triggers'])
        commands.append(self.table['replica_identity'])
        commands.extend(self.table['publications'])
        commands.append(f'alter table {self.table_name} reset (autovacuum_enabled);')
        commands.extend(self.table['storage_parameters'])
        return '\n'.join(command for command in commands if command)

    async def recreate_depend_objects(self, con):
        await con.execute('\n'.join(self.table['create_functions']))
        await con.execute('\n'.join(
            acl_to_grants(params['acl'],
                          params['obj_type'],
                          params['obj_name'])
            for params in self.table['function_acl_to_grants_params']
        ))
        await con.execute('\n'.join(self.table['create_views']))
        await con.execute('\n'.join(
            acl_to_grants(params['acl'],
                          params['obj_type'],
                          params['obj_name'])
            for params in self.table['view_acl_to_grants_params']
        ))
        await con.execute('\n'.join(self.table['comment_views']))
        for child in self.children:
            await child.recreate_depend_objects(con)

    async def run_command_around_switch(self, con, place):
        if place == 'before':
            commands = self.args.command_before_switch
        else:
            commands = self.args.command_after_switch
        if commands:
            self.log(f'run command {place} switch')
            for command in commands:
                if command.startswith('\\i '):  # \i - like psql include command
                    file_path = command[3:]
                    if file_path.startswith('~'):
                        file_path = os.path.expanduser(file_path)
                    with open(file_path) as f:
                        command = f.read()
                await con.execute(command)

    async def switch_table(self):
        self.log_border()
        self.log('switch table: start')

        while True:
            rows = await self.apply_all_delta()
            if rows <= self.args.min_delta_rows:
                break

        async with self.exclusive_lock_table() as con:  # start transaction
            await self.apply_all_delta(con)
            await self.run_command_around_switch(con, 'before')
            await self.drop_depend_objects(con)
            await self.cleanup(con, with_tat_new=False)
            await self.detach_foreign_tables(con)
            await self.drop_original_table(con)
            await self.rename_tables(con)
            await self.attach_to_parent(con)
            await self.attach_foreign_tables(con)
            await self.recreate_depend_objects(con)
            await self.run_command_around_switch(con, 'after')
        self.log('switch table: done')

    async def validate_constraints(self):
        for child in self.children:
            self.table['validate_constraints'].extend(child.table['validate_constraints'])
        if not self.table['validate_constraints']:
            return
        self.log_border()
        if self.args.skip_fk_validation:
            for constraint in self.table['validate_constraints']:
                self.log(f'skip constraint validation: {constraint}')
            return
        ts = time.time()
        constraints_count = len(self.table["validate_constraints"])
        self.log(f'validate constraints: start ({constraints_count})')
        for constraint in self.table['validate_constraints']:
            loop_ts = time.time()
            constraint_name = re.sub('alter table (.*) validate constraint (.*);', '\\1: \\2', constraint)
            self.log(f'validate constraint: {constraint_name}: start')
            try:
                await self.db.execute(constraint)
            except asyncpg.exceptions.ForeignKeyViolationError as e:
                self.log(f'ERROR: {str(e)}\nCONSTRAINT: {constraint}')
            self.log(f'validate constraint: {constraint_name}: done in {self.duration(loop_ts)}')
        self.log(f'validate constraints: done in {self.duration(ts)}')

    async def cleanup(self, db=None, with_tat_new=True):
        if not db:
            db = self.db
        for child in reversed(self.children):
            await child.cleanup(db, with_tat_new)
        await db.execute(
            f'''
            drop trigger if exists store__tat_delta on {self.table_name};
            drop function if exists "{self.table_name}__store_delta"();
            drop function if exists "{self.table_name}__apply_delta"();
            drop table if exists {self.table_name}__tat_delta;
            '''.replace('            ', '')
        )
        if with_tat_new:
            await db.execute(f'drop table if exists {self.table_name}__tat_new;')

    def check_sub_table(self):
        if self.table['inherits'] and not self.is_sub_table and not self.args.partial_mode:
            parent = self.table['inherits'][0]
            print(f'table {self.table_name} is partition of table {parent}, '
                  f'you need to alter {parent} or use key --partial-mode',
                  file=sys.stderr)
            exit(1)
        if self.table['inherits'] and len(self.table['inherits']) > 1:
            print('Multi inherits not supported', file=sys.stderr)
            exit(1)
