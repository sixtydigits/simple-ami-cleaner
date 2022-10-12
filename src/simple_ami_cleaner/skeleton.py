import argparse
import logging
import sys
import os

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
        "--region",
        type=str,
        help="The AWS region, defaults to standard boto3 functionality.",
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
        help="A comma separated list of AMI Ids OR the path to a file with a new line separated AMI Ids OR 'USED' "
             "which will query for AMIs that are associated with running EC2 instances and launch templates (on the "
             "current account).",
    )
    parser.add_argument(
        "--print_used_image_ids_and_exit",
        type=str,
        help="Prints a comma separated list of excluded AMI Ids to the specified path and exits.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Actually deregister AMIs and delete snapshots.",
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


def create_ec2_client(region):
    if region is None:
        return boto3.client("ec2", config=Config(
                retries={"max_attempts": 3}
            )
        )
    else:
        return boto3.client("ec2", config=Config(
                region_name=region,
                retries={"max_attempts": 3},
            ),
        )


def print_used_image_ids(args, used_image_ids):
    if len(used_image_ids) == 0:
        return

    output = os.linesep.join(used_image_ids)

    _logger.info(f"Printing {len(used_image_ids)} in use AMI to '{args.print_used_image_ids_and_exit}")
    if "/dev/stdout" == args.print_used_image_ids_and_exit:  # cross-platform support
        print(output)
    else:
        with open(args.print_used_image_ids_and_exit, "a") as output_file:
            # Append 'hello' at the end of file
            output_file.write(output)
            output_file.write(os.linesep)


def fetch_and_print_used_image_ids(ec2_client, args):
    used_image_ids = fetch_image_ids_in_use(
        ec2_client=ec2_client,
        name_pattern=args.name_pattern
    )

    print_used_image_ids(args=args, used_image_ids=used_image_ids)


def load_excluded_image_ids(ec2_client, args):
    excluded_image_ids = set()

    if args.exclude_image_ids == "USED":
        excluded_image_ids = fetch_image_ids_in_use(
            ec2_client=ec2_client, name_pattern=args.name_pattern
        )
    else:
        if os.path.exists(args.exclude_image_ids):
            with open(args.exclude_image_ids) as f:
                excluded_image_ids.update(
                    [line.rstrip() for line in f]
                )
        else:
            excluded_image_ids.update(
                args.exclude_image_ids.replace(" ", "").split(",")
            )

        print(excluded_image_ids)

        _logger.info(f"Loaded {len(excluded_image_ids)} unique AMIs, which will be excluded")

    return excluded_image_ids


def main(args):
    args = parse_args(args)

    setup_logging(args.loglevel)

    ec2_client = create_ec2_client(args.region)

    if args.print_used_image_ids_and_exit:
        try:
            fetch_and_print_used_image_ids(
                ec2_client=ec2_client,
                args=args,
            )
            sys.exit(0)
        except OSError:
            _logger.exception(msg=f"An error occurred while attempting to append to file "
                                  f"{args.print_used_image_ids_and_exit}", exc_info=True)
            sys.exit(0)

    if args.exclude_image_ids is not None:
        excluded_image_ids = load_excluded_image_ids(ec2_client=ec2_client, args=args)

    clean_images(
        ec2_client=ec2_client,
        name_pattern=args.name_pattern,
        keep=args.keep,
        min_age_days=args.min_age_days,
        excluded_image_ids=excluded_image_ids,
        dry_run=not args.clean,
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
