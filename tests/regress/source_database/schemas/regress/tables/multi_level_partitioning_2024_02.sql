create table regress.multi_level_partitioning_2024_02 (
  id integer not null default nextval('regress.multi_level_partitioning_id_seq'::regclass),
  directory_id integer,
  ts timestamp without time zone not null,
  is_loaded boolean not null,
  duration integer
);

alter table only regress.multi_level_partitioning_noloaded attach partition regress.multi_level_partitioning_2024_02 for values from ('2024-02-01 00:00:00') to ('2024-03-01 00:00:00');

alter table regress.multi_level_partitioning_2024_02 add constraint pk_multi_level_partitioning_2024_02
  primary key (id);

alter table regress.multi_level_partitioning_2024_02 add constraint fk_multi_level_partitioning__directory
  foreign key (directory_id) references regress.directory(id);

create index idx_multi_level_partitioning_2024_02 on regress.multi_level_partitioning_2024_02(ts);

alter table regress.multi_level_partitioning_2024_02 replica identity using index pk_multi_level_partitioning_2024_02;
