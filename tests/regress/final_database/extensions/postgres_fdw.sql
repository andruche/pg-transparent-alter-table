create extension postgres_fdw
  with schema pg_catalog
       version '1.1';

comment on extension postgres_fdw is 'foreign-data wrapper for remote PostgreSQL servers';
