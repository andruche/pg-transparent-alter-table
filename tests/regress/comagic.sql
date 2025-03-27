set check_function_bodies=off;
create extension postgres_fdw
  with schema pg_catalog;


create server archive
    foreign data wrapper postgres_fdw
    options (dbname 'tat_test',
             host '0.0.0.0',
             port '5432');

create user mapping
  for public
  server archive
  options ("user" 'postgres', "password" '123456');


create schema archive_db;

comment on schema archive_db is 'It''s like a separate database';


create schema regress;


create type regress.entity_type as enum (
  'a',
  'b',
  'c'
);


create table archive_db.inheritance_partitioning_2023_12 (
  id integer not null ,
  ts timestamp without time zone not null,
  val integer
);



create table archive_db.multi_level_partitioning_2023_12 (
  id integer not null ,
  directory_id integer,
  ts timestamp without time zone not null,
  is_loaded boolean not null,
  duration integer
);



create table regress.composite_pk (
  id integer not null,
  type regress.entity_type not null,
  val integer
);



create table regress.directory (
  id serial,
  val integer
);



create table regress.inheritance_partitioning (
  id serial,
  ts timestamp without time zone not null,
  val integer
);



create table regress.inheritance_partitioning_2024_01 (
  id integer not null ,
  ts timestamp without time zone not null,
  val integer
)
inherits (regress.inheritance_partitioning);



create table regress.inheritance_partitioning_2024_02 (
  id integer not null ,
  ts timestamp without time zone not null,
  val integer
)
inherits (regress.inheritance_partitioning);



create table regress.multi_level_partitioning (
  id serial,
  page_id integer,
  ts timestamp without time zone not null,
  is_loaded boolean not null,
  duration integer
)
partition by list (is_loaded);
;



create table regress.multi_level_partitioning_2024_01 (
  id integer not null ,
  directory_id integer,
  ts timestamp without time zone not null,
  is_loaded boolean not null,
  duration integer
);



create table regress.multi_level_partitioning_2024_02 (
  id integer not null ,
  directory_id integer,
  ts timestamp without time zone not null,
  is_loaded boolean not null,
  duration integer
);



create table analytics.session_loaded (
  id integer not null ,
  page_id integer,
  ts timestamp without time zone not null,
  is_loaded boolean not null,
  duration integer
);



create table regress.multi_level_partitioning_noloaded (
  id integer not null ,
  directory_id integer,
  ts timestamp without time zone not null,
  is_loaded boolean not null,
  duration integer
)
partition by range (ts);



create foreign table regress.inheritance_partitioning_2023_12 (
  id integer not null ,
  ts timestamp without time zone not null,
  val integer
)
inherits (regress.inheritance_partitioning)
server archive
options (schema_name 'archive_db', table_name 'inheritance_partitioning_2023_12');
;



create foreign table regress.multi_level_partitioning_2023_12 (
  id integer not null ,
  directory_id integer,
  ts timestamp without time zone not null,
  is_loaded boolean not null,
  duration integer
)
server tat_test_freeze
options (schema_name 'archive_db', table_name 'multi_level_partitioning_2023_12');



create publication logical_replica;

-- alter publication logical_replica add table analytics.hit_2024_01;
-- alter publication logical_replica add table analytics.hit_2024_02;
-- alter publication logical_replica add table analytics.page;


alter table archive_db.inheritance_partitioning_2023_12 add constraint pk_inheritance_partitioning_2023_12
  primary key (id);


alter table archive_db.multi_level_partitioning_2023_12 add constraint pk_multi_level_partitioning_2023_12
  primary key (id);


alter table regress.composite_pk add constraint pk_composite_pk
  primary key (id, type);


alter table regress.directory add constraint pk_directory
  primary key (id);


alter table regress.inheritance_partitioning add constraint pk_inheritance_partitioning
  primary key (id);


alter table regress.inheritance_partitioning_2024_01 add constraint pk_inheritance_partitioning_2024_01
  primary key (id);


alter table regress.inheritance_partitioning_2024_02 add constraint pk_inheritance_partitioning_2024_02
  primary key (id);




alter table regress.multi_level_partitioning_2024_01 add constraint pk_multi_level_partitioning_2024_01
  primary key (id);


alter table regress.multi_level_partitioning_2024_02 add constraint pk_multi_level_partitioning_2024_02
  primary key (id);


alter table analytics.session_loaded add constraint pk_session_loaded
  primary key (id);








alter table archive_db.inheritance_partitioning_2023_12 alter column id set default nextval('regress.inheritance_partitioning_id_seq'::regclass);





alter table archive_db.multi_level_partitioning_2023_12 alter column id set default nextval('regress.multi_level_partitioning_id_seq'::regclass);





grant select, update on table regress.directory to user1;


alter table regress.directory replica identity full;




grant insert, delete on table regress.inheritance_partitioning to user2;


create index idx_inheritance_partitioning__ts on regress.inheritance_partitioning(ts);





alter table regress.inheritance_partitioning_2024_01 add constraint chk_inheritance_partitioning_ts
  check (ts >= '2024-01-01 00:00:00'::timestamp without time zone AND ts < '2024-02-01 00:00:00'::timestamp without time zone);

create index idx_inheritance_partitioning_2024_01__ts on regress.inheritance_partitioning_2024_01(ts);




alter table regress.inheritance_partitioning_2024_01 alter column id set default nextval('regress.inheritance_partitioning_id_seq'::regclass);


alter table regress.inheritance_partitioning_2024_02 add constraint chk_inheritance_partitioning_ts
  check (ts >= '2024-02-01 00:00:00'::timestamp without time zone AND ts < '2024-03-01 00:00:00'::timestamp without time zone);

create index idx_inheritance_partitioning_2024_02__ts on regress.inheritance_partitioning_2024_02(ts);




alter table regress.inheritance_partitioning_2024_02 alter column id set default nextval('regress.inheritance_partitioning_id_seq'::regclass);





alter table only regress.multi_level_partitioning_noloaded attach partition regress.multi_level_partitioning_2024_01 for values from ('2024-01-01 00:00:00') to ('2024-02-01 00:00:00');


alter table regress.multi_level_partitioning_2024_01 add constraint fk_multi_level_partitioning__directory
  foreign key (directory_id) references regress.directory(id);

create index idx_multi_level_partitioning_2024_01 on regress.multi_level_partitioning_2024_01(ts);

alter table regress.multi_level_partitioning_2024_01 replica identity using index pk_multi_level_partitioning_2024_01;




alter table regress.multi_level_partitioning_2024_01 alter column id set default nextval('regress.multi_level_partitioning_id_seq'::regclass);

alter table only regress.multi_level_partitioning_noloaded attach partition regress.multi_level_partitioning_2024_02 for values from ('2024-02-01 00:00:00') to ('2024-03-01 00:00:00');


alter table regress.multi_level_partitioning_2024_02 add constraint fk_multi_level_partitioning__directory
  foreign key (directory_id) references regress.directory(id);

create index idx_multi_level_partitioning_2024_02 on regress.multi_level_partitioning_2024_02(ts);

alter table regress.multi_level_partitioning_2024_02 replica identity using index pk_multi_level_partitioning_2024_02;




alter table regress.multi_level_partitioning_2024_02 alter column id set default nextval('regress.multi_level_partitioning_id_seq'::regclass);

alter table only analytics.session attach partition analytics.session_loaded for values in (true);


alter table analytics.session_loaded add constraint fk_session__page
  foreign key (page_id) references analytics.page(id);

create index idx_session_loaded on analytics.session_loaded(ts);

alter table analytics.session_loaded replica identity nothing;




alter table analytics.session_loaded alter column id set default nextval('analytics.session_id_seq'::regclass);

alter table only regress.multi_level_partitioning attach partition regress.multi_level_partitioning_noloaded for values in (false, NULL);




alter table regress.multi_level_partitioning_noloaded alter column id set default nextval('regress.multi_level_partitioning_id_seq'::regclass);





alter foreign table regress.inheritance_partitioning_2023_12 alter column id set default nextval('regress.inheritance_partitioning_id_seq'::regclass);

alter table only regress.multi_level_partitioning_noloaded attach partition regress.multi_level_partitioning_2023_12 for values from ('2023-12-01 00:00:00') to ('2024-01-01 00:00:00');




alter foreign table regress.multi_level_partitioning_2023_12 alter column id set default nextval('regress.multi_level_partitioning_id_seq'::regclass);

