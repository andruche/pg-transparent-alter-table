create table analytics.page (
  id serial,
  url integer
);

grant select, update on table analytics.page to user1;

alter table analytics.page add constraint pk_page
  primary key (id);

alter table analytics.page replica identity full;
