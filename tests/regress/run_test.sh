#!/bin/bash

export PGPASSWORD=123456
export PGUSER=postgres
export PGHOST=0.0.0.0
export PGPORT=15432
export PGDATABASE=tat_test
PG_VERSION=15
container_name=pg_tat_test

docker rm -f $container_name

set -e

if [ $# -eq 1 ]; then
    PG_VERSION=$1
fi

docker run --name $container_name -p $PGPORT:5432 -e POSTGRES_PASSWORD=$PGPASSWORD -d postgres:$PG_VERSION
sleep 1.5
docker exec -u postgres $container_name mkdir /var/lib/postgresql/archive_data

echo "build src database"
psql -c "create role user1;" -d postgres
psql -c "create role user2;" -d postgres
psql -c "create database $PGDATABASE;" -d postgres
psql -c "create tablespace archive location '/var/lib/postgresql/archive_data';"
pg_import source_database -d $PGDATABASE


echo "======================================================="
psql -c "insert into regress.composite_pk(id, type, val)
         select i, type, i % 100
           from generate_series(1, 1000000) i
          cross join unnest(enum_range(null::regress.entity_type)) as type"

# batch mode multi column primary key
pg_tat -c "alter table regress.composite_pk alter column id type bigint;" --copy-data-jobs 2 --create-index-jobs 4 --batch-size 100000 &

sleep 1.1  # the following 3 commands will be executed in parallel with transparent_alter_type
psql -c "update regress.composite_pk
            set val = val + 20
          where id between 20 and 30"
psql -c "delete from regress.composite_pk
          where id > 200"
psql -c "insert into regress.composite_pk(id, type, val)
         select i, type, i % 100
           from generate_series(1000001, 1000100) i
          cross join unnest(enum_range(null::regress.entity_type)) as type"
wait


echo "======================================================="
psql -c "insert into regress.directory(val)
         select generate_series(1, 1000000)"

# batch mode single column primary key
pg_tat -c "alter table regress.directory alter column id type bigint;" \
       --copy-data-jobs 2 --create-index-jobs 4 --batch-size 100000 &

sleep 1.1  # the following 3 commands will be executed in parallel with transparent_alter_type
psql -c "update regress.directory
            set val = val + 20
          where id between 20 and 30"
psql -c "delete from regress.directory
          where id > 200"
psql -c "insert into regress.directory(val)
         select generate_series(1, 100)"
wait

echo "======================================================="
psql -c "insert into regress.multi_level_partitioning(directory_id, ts, is_loaded, duration)
         select i % 200 + 1, '2024-01-01'::date + (random() * 58)::int, random() < 0.1, i % 10
           from generate_series(1, 1000000) i"

# declarative multi level partitioning
pg_tat -c "alter table regress.multi_level_partitioning alter column id type bigint using id::bigint" \
       -c "alter table regress.multi_level_partitioning alter column directory_id type bigint using directory_id::bigint" \
       --copy-data-jobs 2 --create-index-jobs 4 &

sleep 1  # the following 3 commands will be executed in parallel with transparent_alter_type
psql -c "update regress.multi_level_partitioning
            set duration = duration + 20
          where id < 1000"
psql -c "delete from regress.multi_level_partitioning
          where id > 2000"
psql -c "insert into regress.multi_level_partitioning(directory_id, ts, is_loaded, duration)
         select i % 200 + 1, '2024-01-01'::date + (random() * 58)::int, random() < 0.1, i % 10
           from generate_series(1, 1000) i"
psql -c "insert into regress.multi_level_partitioning(directory_id, ts, is_loaded, duration)
         select i % 200 + 1, '2023-12-01'::date + (random() * 20)::int, false, i % 10
           from generate_series(1, 100) i"
wait


echo "======================================================="
psql -c "insert into regress.inheritance_partitioning_2024_01(ts, val)
         select '2024-01-01'::date + (random() * 20)::int,  i % 10
           from generate_series(1, 1000000) i"

# old style inheritance partitioning
pg_tat -c "alter table regress.inheritance_partitioning alter column id type bigint" --copy-data-jobs 2 --create-index-jobs 4 &

sleep 1  # the following 3 commands will be executed in parallel with transparent_alter_type
psql -c "update regress.inheritance_partitioning
            set val = val + 20
          where id < 1000"
psql -c "delete from regress.inheritance_partitioning
          where id > 2000"
psql -c "insert into regress.inheritance_partitioning_2024_02(ts, val)
         select '2024-02-01'::date + (random() * 20)::int,  i % 10
           from generate_series(1, 1000) i"
psql -c "insert into regress.inheritance_partitioning_2023_12(ts, val)
         select '2023-12-01'::date + (random() * 20)::int,  i % 10
           from generate_series(1, 100) i"
wait


echo "================ alter partition table ======================="
pg_tat -c "alter table regress.multi_level_partitioning_noloaded set tablespace archive" --partial-mode


echo "================ alter child table ======================="
pg_tat -c "alter table regress.inheritance_partitioning_2024_02 set tablespace archive" --partial-mode


echo "==================== tests result ==========================="
echo "diff table structure:"
pg_export $PGDATABASE /tmp/exp_tat_test
diff -x "public.sql" -qr /tmp/exp_tat_test/schemas/ final_database/schemas && echo " all tables: ok"
diff -qr /tmp/exp_tat_test/publications final_database/publications && echo " publications: ok"
echo
echo "check sum:"
psql -t -c "select 'regress.composite_pk: ' ||
                   case
                     when count(1) = 900 and sum(val) = 45210
                       then 'ok'
                     else 'FAILED'
                   end
              from regress.composite_pk" | grep -v "^$"

psql -t -c "select 'regress.directory: ' ||
                   case
                     when count(1) = 300 and sum(val) = 25370
                       then 'ok'
                     else 'FAILED'
                   end
              from regress.directory" | grep -v "^$"

psql -t -c "select 'regress.multi_level_partitioning: ' ||
                   case
                     when count(1) = 3100 and sum(duration) = 33930
                       then 'ok'
                     else 'FAILED'
                   end
              from regress.multi_level_partitioning" | grep -v "^$"

psql -t -c "select 'regress.inheritance_partitioning: ' ||
                   case
                     when count(1) = 3100 and sum(val) = 33930
                       then 'ok'
                     else 'FAILED'
                   end
              from regress.inheritance_partitioning"
