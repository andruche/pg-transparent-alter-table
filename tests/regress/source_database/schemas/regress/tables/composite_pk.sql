create table regress.composite_pk (
  id integer not null,
  type regress.entity_type not null,
  val integer
);

alter table regress.composite_pk add constraint pk_composite_pk
  primary key (id, type);
