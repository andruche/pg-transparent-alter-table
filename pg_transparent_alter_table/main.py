import argparse
import asyncio

from .tat import TAT
from . import __version__


def main():
    arg_parser = argparse.ArgumentParser(
        conflict_handler='resolve'
    )
    # TODO show defaults in help
    arg_parser.add_argument('-c', '--command', required=True, action='append', default=argparse.SUPPRESS,
                            help='"alter table mytable ...", least at one required')
    arg_parser.add_argument('-h', '--host')
    arg_parser.add_argument('-p', '--port')
    arg_parser.add_argument('-d', '--dbname')
    arg_parser.add_argument('-U', '--user')
    arg_parser.add_argument('-W', '--password')
    arg_parser.add_argument('-p', '--port')
    arg_parser.add_argument('--version', action='version', version=__version__)
    arg_parser.add_argument('--maintenance-work-mem', type=str, default='2GB',
                            metavar='SIZE',
                            help='PostgreSQL parameter (default: %(default)s)')
    arg_parser.add_argument('--max-parallel-maintenance-workers', type=int, default=0,
                            metavar='PG_WORKERS',
                            help='PostgreSQL parameter (default: %(default)s)')
    arg_parser.add_argument('--copy-data-jobs', type=int, default=1,
                            metavar='JOBS',
                            help='run JOBS parallel "insert into" commands (default: %(default)s)')
    arg_parser.add_argument('--batch-size', type=int, default=0,
                            metavar='ROWS',
                            help='copying data by ROWS, when 0 all data will copied at once (default: %(default)s)')
    arg_parser.add_argument('--copy-progress-interval', type=int, default=60,
                            metavar='SEC',
                            help='print copying statistics each SEC seconds, 0 - disable (default: %(default)s)')
    arg_parser.add_argument('--create-index-jobs', type=int, default=2,
                            metavar='JOBS',
                            help='run JOBS parallel "create index" commands (default: %(default)s)')
    arg_parser.add_argument('--lock-timeout', type=int, default=5,
                            metavar='SEC',
                            help="try to get lock table SEC seconds before lock timeout error (default: %(default)s)")
    arg_parser.add_argument('--time-between-locks', type=int, default=10,
                            metavar='SEC',
                            help='wait SEC seconds between attempts to lock table (default: %(default)s)')
    arg_parser.add_argument('--min-delta-rows', type=int, default=100000,
                            metavar='ROWS',
                            help='switch table when last applied delta less than ROWS (default: %(default)s)')
    arg_parser.add_argument('--cleanup', action='store_true',
                            help='drop all temp objects and exit')
    arg_parser.add_argument('--continue-create-indexes', action='store_true',
                            help='use only when break after coping data done!')
    arg_parser.add_argument('--no-switch-table', action='store_true',
                            help='copy data and create index only')
    arg_parser.add_argument('--continue-switch-table', action='store_true',
                            help='use only when break after all create index done!')
    arg_parser.add_argument('--skip-fk-validation', action='store_true',
                            help='print validation commands instead execute')
    arg_parser.add_argument('--dry-run', action='store_true',
                            help='test run without real changes')
    arg_parser.add_argument('--echo-queries', action='store_true',
                            help='echo commands sent to server')
    arg_parser.add_argument('--partial-mode', action='store_true',
                            help='allow alter part of partitioned table')
    arg_parser.add_argument('--command-before-switch', action='append',
                            metavar='COMMAND',
                            default=[],
                            help='execute COMMAND (or "\\i file_path") before switch table (in the same transaction)')
    arg_parser.add_argument('--command-after-switch', action='append',
                            metavar='COMMAND',
                            default=[],
                            help='execute COMMAND (or "\\i file_path") after switch table (in the same transaction)')
    args = arg_parser.parse_args()

    t = TAT(args)
    asyncio.run(t.run())
