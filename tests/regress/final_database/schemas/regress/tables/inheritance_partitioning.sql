create table regress.inheritance_partitioning (
  id bigserial,
  ts timestamp without time zone not null,
  val integer
);

grant insert, delete on table regress.inheritance_partitioning to user2;

alter table regress.inheritance_partitioning add constraint pk_inheritance_partitioning
  primary key (id);

create index idx_inheritance_partitioning__ts on regress.inheritance_partitioning(ts);
