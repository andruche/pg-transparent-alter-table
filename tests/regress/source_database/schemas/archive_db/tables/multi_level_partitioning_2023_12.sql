create table archive_db.multi_level_partitioning_2023_12 (
  id integer not null default nextval('regress.multi_level_partitioning_id_seq'::regclass),
  directory_id integer,
  ts timestamp without time zone not null,
  is_loaded boolean not null,
  duration integer
);

alter table archive_db.multi_level_partitioning_2023_12 add constraint pk_multi_level_partitioning_2023_12
  primary key (id);
