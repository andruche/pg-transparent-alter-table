create foreign table regress.multi_level_partitioning_2023_12 (
  id integer not null default nextval('regress.multi_level_partitioning_id_seq'::regclass),
  directory_id integer,
  ts timestamp without time zone not null,
  is_loaded boolean not null,
  duration integer
)
server archive
options (schema_name 'archive_db', table_name 'multi_level_partitioning_2023_12');

alter table only regress.multi_level_partitioning_noloaded attach partition regress.multi_level_partitioning_2023_12 for values from ('2023-12-01 00:00:00') to ('2024-01-01 00:00:00');
