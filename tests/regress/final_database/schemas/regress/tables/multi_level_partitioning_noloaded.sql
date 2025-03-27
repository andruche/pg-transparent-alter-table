create table regress.multi_level_partitioning_noloaded (
  id bigint not null default nextval('regress.multi_level_partitioning_id_seq'::regclass),
  directory_id bigint,
  ts timestamp without time zone not null,
  is_loaded boolean not null,
  duration integer
)
partition by range (ts)
tablespace archive;

alter table only regress.multi_level_partitioning attach partition regress.multi_level_partitioning_noloaded for values in (false, NULL);
