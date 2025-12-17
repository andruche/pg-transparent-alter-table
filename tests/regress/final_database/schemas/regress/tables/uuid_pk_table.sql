create table regress.uuid_pk_table (
  id uuid,
  val bigint
);

grant select, update, delete on table regress.uuid_pk_table to user1;

alter table regress.uuid_pk_table add constraint pk_uuid_pk_table
  primary key (id);

alter table regress.uuid_pk_table replica identity full;
