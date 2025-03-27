create table regress.inheritance_partitioning_2024_01 (
  id integer not null default nextval('regress.inheritance_partitioning_id_seq'::regclass),
  ts timestamp without time zone not null,
  val integer
)
inherits (regress.inheritance_partitioning);

alter table regress.inheritance_partitioning_2024_01 add constraint pk_inheritance_partitioning_2024_01
  primary key (id);

alter table regress.inheritance_partitioning_2024_01 add constraint chk_inheritance_partitioning_ts
  check (ts >= '2024-01-01 00:00:00'::timestamp without time zone AND ts < '2024-02-01 00:00:00'::timestamp without time zone);

create index idx_inheritance_partitioning_2024_01__ts on regress.inheritance_partitioning_2024_01(ts);
