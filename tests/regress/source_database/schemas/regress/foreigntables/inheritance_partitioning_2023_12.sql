create foreign table regress.inheritance_partitioning_2023_12 (
  id integer not null default nextval('regress.inheritance_partitioning_id_seq'::regclass),
  ts timestamp without time zone not null,
  val integer
)
inherits (regress.inheritance_partitioning)
server archive
options (schema_name 'archive_db', table_name 'inheritance_partitioning_2023_12');
