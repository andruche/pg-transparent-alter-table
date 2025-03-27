create table regress.directory (
  id serial,
  val integer
);

grant select, update on table regress.directory to user1;

alter table regress.directory add constraint pk_directory
  primary key (id);

alter table regress.directory replica identity full;
