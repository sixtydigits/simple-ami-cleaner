import argparse
import logging
import sys

import boto3
from botocore.config import Config

from simple_ami_cleaner import __version__
from .ami_cleaner import clean_images, fetch_image_ids_in_use

__author__ = "Dan Washusen"
__license__ = "MIT"

_logger = logging.getLogger(__name__)


def parse_args(args):
    parser = argparse.ArgumentParser(description="A tool to clean EC2 AMIs and associated snapshots")

    parser.add_argument(
        "name_pattern",
        help="The AMI name patterns (e.g. some*name*amd64*)."
    )
    parser.add_argument(
        "--min_age_days",
        type=int,
        default=90,
        help="The min age of an AMI to considered for cleanup (default 90), use '-1' to disable age based checks.",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=-1,
        help="The number of recent AMIs to keep excluding them from the list of candidate AMIs, "
             "use '-1' (default) to consider all AMIs.",
    )
    parser.add_argument(
        "--exclude_image_ids",
        type=str,
        default="USED",
        help="A comma separated list of AMI Ids to exclude OR a special value of 'USED' which will query "
             "for AMIs that are associated with running EC2 instances and launch templates (on the current account).,",
    )
    parser.add_argument(
        "--print_excluded_image_ids_and_exit",
        action="store_true",
        help="Prints a comma separated list of excluded AMI Ids and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate a clean without actually deleting anything (default True).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skips user prompts to confirm destructive actions.",
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
        help="Set loglevel to DEBUG",
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
        level=loglevel, stream=sys.stderr, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )


def main(args):
    args = parse_args(args)
    setup_logging(args.loglevel)

    ec2_client = boto3.client("ec2", config=Config(retries={"max_attempts": 3}))

    if args.exclude_image_ids == "USED":
        excluded_image_ids = fetch_image_ids_in_use(ec2_client=ec2_client, name_pattern=args.name_pattern)
        if args.print_excluded_image_ids_and_exit:
            print(", ".join(excluded_image_ids))
            sys.exit(0)
    else:
        excluded_image_ids = args.exclude_image_ids.replace(" ", "").split(",")

    clean_images(
        ec2_client=ec2_client,
        name_pattern=args.name_pattern,
        keep=args.keep,
        min_age_days=args.min_age_days,
        excluded_image_ids=excluded_image_ids,
        dry_run=args.dry_run,
        force=args.force,
    )
    sys.exit(0)


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
