create table archive_db.inheritance_partitioning_2023_12 (
  id integer not null default nextval('regress.inheritance_partitioning_id_seq'::regclass),
  ts timestamp without time zone not null,
  val integer
);

alter table archive_db.inheritance_partitioning_2023_12 add constraint pk_inheritance_partitioning_2023_12
  primary key (id);
