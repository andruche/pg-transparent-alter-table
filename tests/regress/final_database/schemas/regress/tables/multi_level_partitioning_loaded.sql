create table regress.multi_level_partitioning_loaded (
  id bigint not null default nextval('regress.multi_level_partitioning_id_seq'::regclass),
  directory_id bigint,
  ts timestamp without time zone not null,
  is_loaded boolean not null,
  duration integer
);

alter table only regress.multi_level_partitioning attach partition regress.multi_level_partitioning_loaded for values in (true);

alter table regress.multi_level_partitioning_loaded add constraint pk_multi_level_partitioning_loaded
  primary key (id);

alter table regress.multi_level_partitioning_loaded add constraint fk_multi_level_partitioning__directory
  foreign key (directory_id) references regress.directory(id);

create index idx_multi_level_partitioning_loaded on regress.multi_level_partitioning_loaded(ts);

alter table regress.multi_level_partitioning_loaded replica identity nothing;
