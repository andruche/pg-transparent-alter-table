create table regress.multi_level_partitioning (
  id serial,
  directory_id integer,
  ts timestamp without time zone not null,
  is_loaded boolean not null,
  duration integer
)
partition by list (is_loaded);
