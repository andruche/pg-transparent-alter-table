import argparse
import asyncio

from .tat import TAT


def main():
    arg_parser = argparse.ArgumentParser(conflict_handler='resolve')
    # TODO show defaults in help
    arg_parser.add_argument('-c', '--command', action='append', help='alter table ...', default=[])
    arg_parser.add_argument('-h', '--host')
    arg_parser.add_argument('-p', '--port')
    arg_parser.add_argument('-d', '--dbname')
    arg_parser.add_argument('-U', '--user')
    arg_parser.add_argument('-W', '--password')
    arg_parser.add_argument('-p', '--port')
    arg_parser.add_argument('--work-mem', type=str, default='128MB')
    arg_parser.add_argument('--maintenance-work-mem', type=str, default='4GB')
    arg_parser.add_argument('--max-parallel-maintenance-workers', type=int, default=0)
    arg_parser.add_argument('--copy-data-jobs', type=int, default=1)
    arg_parser.add_argument('--batch-size', type=int, default=0)
    arg_parser.add_argument('--copy-progress-interval', type=int, default=60,
                            help='print copying statistics each N sec, 0 - disable')
    arg_parser.add_argument('--create-index-jobs', type=int, default=2)
    arg_parser.add_argument('--lock-timeout', type=int, default=5)
    arg_parser.add_argument('--time-between-locks', type=int, default=10)
    arg_parser.add_argument('--min-delta-rows', type=int, default=100000)
    arg_parser.add_argument('--cleanup', action='store_true')
    arg_parser.add_argument('--continue-create-indexes', action='store_true')
    arg_parser.add_argument('--no-switch-table', action='store_true')
    arg_parser.add_argument('--continue-switch-table', action='store_true')
    arg_parser.add_argument('--skip-fk-validation', action='store_true')
    arg_parser.add_argument('--dry-run', action='store_true')
    arg_parser.add_argument('--echo-queries', action='store_true')
    args = arg_parser.parse_args()

    t = TAT(args)
    asyncio.run(t.run())
