import argparse
import logging
import sys

from simple_ami_cleaner import __version__
from .ami_cleaner import clean_images

__author__ = "Dan Washusen"
__license__ = "MIT"

_logger = logging.getLogger(__name__)


def parse_args(args):
    parser = argparse.ArgumentParser(description="A tool to clean EC2 AMIs and associated snapshots")

    parser.add_argument(
        "name_pattern",
        help="The AMI name patterns (e.g. some*name*amd64*)"
    )
    parser.add_argument(
        "--min_age_days",
        type=int,
        default=90,
        help="The min age of an AMI to considered for cleanup, use '-1' to include all AMIs",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=-1,
        help="The number of recent AMIs to keep, use '-1' to include all AMIs",
    )
    parser.add_argument(
        "--exclude_images",
        type=str,
        default="USED",
        help="A comma separated list of AMI ImageIds to exclude OR a special value of 'USED' which will query "
             "for AMIs that are associated with running EC2 instances "
             "(on the current account, this does *NOT* work in cross-account scenarios)",
    )
    parser.add_argument(
        "--dry-run",
        type=bool,
        default=True,
        help="Simulate a clean without actually deleting anything",
    )
    parser.add_argument(
        "--force",
        type=bool,
        default=False,
        help="Skips the user prompts",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="simple-ami-cleaner {ver}".format(ver=__version__),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG,
    )
    return parser.parse_args(args)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    if loglevel is None:
        loglevel = logging.INFO

    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )


def main(args):
    args = parse_args(args)
    setup_logging(args.loglevel)
    clean_images(
        name_pattern=args.name_pattern,
        keep=args.keep,
        min_age_days=args.min_age_days,
        exclude_images=args.exclude_images,
        dry_run=args.dry_run,
        force=args.force,
    )


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
