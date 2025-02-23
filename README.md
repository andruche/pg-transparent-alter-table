pg_tat
======================

PostgreSQL tool for alter table without locks.

# Installation

$ pip install pg-transparent-alter-table 

# Dependency

* python3.8+

# Usage

    usage: pg_tat [--help] [-c COMMAND] [-h HOST] [-d DBNAME] [-U USER] [-W PASSWORD] [-p PORT] [--work-mem WORK_MEM] [--maintenance-work-mem MAINTENANCE_WORK_MEM]
                  [--max-parallel-maintenance-workers MAX_PARALLEL_MAINTENANCE_WORKERS] [--copy-data-jobs COPY_DATA_JOBS] [--create-index-jobs CREATE_INDEX_JOBS] [--cleanup] [--continue-create-indexes]
                  [--no-switch-table] [--continue-switch-table] [--lock-timeout LOCK_TIMEOUT] [--time-between-locks TIME_BETWEEN_LOCKS] [--min-delta-rows MIN_DELTA_ROWS] [--skip-fk-validation]
                  [--show-queries] [--batch-size BATCH_SIZE]
      
    options:
     --help                show this help message and exit
     -c COMMAND, --command COMMAND
                           alter table ...
     -h HOST, --host HOST
     -d DBNAME, --dbname DBNAME
     -U USER, --user USER
     -W PASSWORD, --password PASSWORD
     -p PORT, --port PORT
     --work-mem WORK_MEM
     --maintenance-work-mem MAINTENANCE_WORK_MEM
     --max-parallel-maintenance-workers MAX_PARALLEL_MAINTENANCE_WORKERS
     --copy-data-jobs COPY_DATA_JOBS
     --create-index-jobs CREATE_INDEX_JOBS
     --cleanup
     --continue-create-indexes
     --no-switch-table
     --continue-switch-table
     --lock-timeout LOCK_TIMEOUT
     --time-between-locks TIME_BETWEEN_LOCKS
     --min-delta-rows MIN_DELTA_ROWS
     --skip-fk-validation
     --show-queries
     --batch-size BATCH_SIZE

# How it works

1. create new tables TABLE_NAME__tat_new (like original) and TABLE_NAME__tat_delta
1. apply alter table commands
1. create trigger replicate__tat_delta which fixing all changes on TABLE_NAME to TABLE_NAME__tat_delta
1. copy data from TABLE_NAME to TABLE_NAME__tat_new
1. create indexes for TABLE_NAME__tat_new (in parallel mode on JOBS)
1. analyze TABLE_NAME__tat_new
1. apply delta from TABLE_NAME__tat_delta to TABLE_NAME__tat_new (in loop while last rows > MIN_DELTA_ROWS)
1. begin;\
   drop dependent functions, views, constraints;\
   link sequences to TABLE_NAME__tat_new\
   drop table TABLE_NAME;\
   apply delta;\
   rename table TABLE_NAME__tat_new to TABLE_NAME;\
   create dependent functions, views, constraints (not valid);\
   commit;
1. validate constraints

# Quick examples

    $ pg_tat -h 127.0.0.1 -p 5432 -d mydb -c "alter table mytable alter column id type bigint" 
    $ pg_tat -h 127.0.0.1 -p 5432 -d mydb -c "alter table mytable move column a before b"
    $ pg_tat -h 127.0.0.1 -p 5432 -d mydb -c "alter table mytable set tablespace new_tablespace"
