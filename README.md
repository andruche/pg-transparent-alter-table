pg_tat
======================

PostgreSQL tool for alter table without locks.

# Installation

$ pip install pg-transparent-alter-table 

# Dependency

* python3.8+

# Usage

    usage: pg_tat [--help] -c COMMAND [-h HOST] [-d DBNAME] [-U USER] [-W PASSWORD] [-p PORT] [--version]
                  [--maintenance-work-mem SIZE] [--max-parallel-maintenance-workers PG_WORKERS]
                  [--copy-data-jobs JOBS] [--batch-size ROWS] [--copy-progress-interval SEC]
                  [--create-index-jobs JOBS] [--lock-timeout SEC] [--time-between-locks SEC] [--min-delta-rows ROWS]
                  [--cleanup] [--continue-create-indexes] [--no-switch-table] [--continue-switch-table]
                  [--skip-fk-validation] [--dry-run] [--echo-queries] [--partial-mode]
                  [--command-before-switch COMMAND] [--command-after-switch COMMAND]

    options:
      --help                show this help message and exit
      -c COMMAND, --command COMMAND
                            "alter table mytable ...", least at one required
      -h HOST, --host HOST
      -d DBNAME, --dbname DBNAME
      -U USER, --user USER
      -W PASSWORD, --password PASSWORD
      -p PORT, --port PORT
      --version             show program's version number and exit
      --maintenance-work-mem SIZE
                            PostgreSQL parameter (default: 2GB)
      --max-parallel-maintenance-workers PG_WORKERS
                            PostgreSQL parameter (default: 0)
      --copy-data-jobs JOBS
                            run JOBS parallel "insert into" commands (default: 1)
      --batch-size ROWS     copying data by ROWS, when 0 all data will copied at once (default: 0)
      --copy-progress-interval SEC
                            print copying statistics each SEC seconds, 0 - disable (default: 60)
      --create-index-jobs JOBS
                            run JOBS parallel "create index" commands (default: 2)
      --lock-timeout SEC    try to get lock table SEC seconds before lock timeout error (default: 5)
      --time-between-locks SEC
                            wait SEC seconds between attempts to lock table (default: 10)
      --min-delta-rows ROWS
                            switch table when last applied delta less than ROWS (default: 100000)
      --cleanup             drop all temp objects and exit
      --continue-create-indexes
                            use only when break after coping data done!
      --no-switch-table     copy data and create index only
      --continue-switch-table
                            use only when break after all create index done!
      --skip-fk-validation  print validation commands instead execute
      --dry-run             test run without real changes
      --echo-queries        echo commands sent to server
      --partial-mode        allow alter part of partitioned table
      --command-before-switch COMMAND
                            execute COMMAND (or "\i file_path") before switch table (in the same transaction)
      --command-after-switch COMMAND
                            execute COMMAND (or "\i file_path") after switch table (in the same transaction)

# How it works

1. create new tables TABLE_NAME__tat_new (like original) and TABLE_NAME__tat_delta (for changes)
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
