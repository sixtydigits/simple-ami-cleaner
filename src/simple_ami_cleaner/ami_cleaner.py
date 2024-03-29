import sys

import logging
import fnmatch
from datetime import datetime

from botocore.exceptions import ClientError

_logger = logging.getLogger(__name__)


def fetch_images(ec2_client, name_pattern):
    images_response = ec2_client.describe_images(
        Owners=["self"],
        Filters=[
            {
                "Name": "name",
                "Values": [
                    name_pattern,
                ]
            },
        ],
    )

    available_images = images_response.get("Images")

    return available_images


class ImageNotFoundException(Exception):
    pass


def fetch_image(ec2_client, image_id):
    try:
        images_response = ec2_client.describe_images(
            ImageIds=[
                image_id,
            ],
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidAMIID.NotFound':
            raise ImageNotFoundException(f'Could not find AMI for {image_id}')
        else:
            raise e
        

    available_images = images_response.get("Images")

    if len(available_images) != 1:
        raise ImageNotFoundException(f'Could not find AMI for {image_id}')

    return available_images[0]


def fetch_image_ids_in_use_by_instances(ec2_client):
    paginator = ec2_client.get_paginator("describe_instances")
    page_iterator = paginator.paginate(
        Filters=[
            {
                "Name": "instance-state-name",
                "Values": [
                    "pending",
                    "running",
                    "shutting-down",
                    "stopping",
                    "stopped"
                ]
            }
        ]
    )

    images = set()
    for page in page_iterator:
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                _logger.info(
                    f"Found AMI {instance['ImageId']} currently in use by reserved instance {instance['InstanceId']}")
                images.add(instance["ImageId"])

    _logger.info(f"Found {len(images)} AMIs currently in use by instances...")

    return images


def fetch_image_ids_in_use_by_launch_templates(ec2_client):
    paginator = ec2_client.get_paginator("describe_launch_template_versions")
    page_iterator = paginator.paginate(Versions=["$Latest", "$Default"])

    images = set()
    for page in page_iterator:
        for launch_template_version in page["LaunchTemplateVersions"]:
            if "LaunchTemplateData" in launch_template_version and \
                    "ImageId" in launch_template_version["LaunchTemplateData"]:
                _logger.info(
                    f"Found AMI {launch_template_version['LaunchTemplateData']['ImageId']} currently in use by "
                    f"launch template "
                    f"({launch_template_version['LaunchTemplateId']}:{launch_template_version['VersionNumber']})")
                images.add(launch_template_version["LaunchTemplateData"]["ImageId"])

    _logger.info(f"Found {len(images)} AMIs currently in use by $Latest and $Default launch template versions...")

    return images


def check_name_match(image_name, name_pattern):
    return fnmatch.fnmatch(image_name, name_pattern)


def fetch_image_ids_in_use(ec2_client, name_pattern):
    all_image_ids = set()
    all_image_ids.update(
        fetch_image_ids_in_use_by_instances(ec2_client=ec2_client)
    )
    all_image_ids.update(
        fetch_image_ids_in_use_by_launch_templates(ec2_client=ec2_client)
    )

    matching_image_ids = set()
    for image_id in all_image_ids:
        try:
            image = fetch_image(ec2_client=ec2_client, image_id=image_id)
            if check_name_match(image['Name'], name_pattern):
                matching_image_ids.add(image_id)
        except ImageNotFoundException:
            _logger.warning(
                f"Unable to find AMI {image_id}, you have resources pointing to an AMI that no longer exists")

    _logger.info(f"After name filtering {len(matching_image_ids)} AMIs are currently in use by instances and "
                 f"launch templates...")

    return matching_image_ids


def delete_snapshot(ec2_client, snapshot_id, dry_run):
    _logger.info(f"Deleting snapshot {snapshot_id}")

    if dry_run:
        _logger.info(f"Skipping deleting snapshot in dry-run mode")
        return

    try:
        ec2_client.delete_snapshot(
            SnapshotId=snapshot_id
        )
        _logger.info(f"Done deleting snapshot")
    except ClientError:
        _logger.critical(msg=f"Error raised while attempting to delete snapshot {snapshot_id}", exc_info=True)
        raise Exception(f"Failed deleting snapshot {snapshot_id}")


def deregister_image(ec2_client, image, dry_run):
    _logger.info(f"Deregistering AMI: {image_to_string(image)}")

    if dry_run:
        _logger.info(f"Skipping deregistering AMI in dry-run mode")
        return

    try:
        ec2_client.deregister_image(ImageId=image["ImageId"])
        _logger.info(f"Done deregistering AMI")
    except ClientError:
        _logger.critical(msg=f"Error raised while attempting to deregister AMI {image['ImageId']}", exc_info=True)
        raise Exception(f"Failed deleting AMI {image['ImageId']}")


def image_to_string(image):
    return f"ImageId: {image['ImageId']}, Name: {image['Name']}, CreationDate: {image['CreationDate']}"


def parse_date(date_as_string):
    return datetime.strptime(date_as_string, "%Y-%m-%dT%H:%M:%S.%fZ")


def format_date(date):
    return date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def filter_images_by_age(images, min_age_days=-1):
    filtered_images = []
    filtered_count = 0
    for image in images:
        if min_age_days > 0:
            present = datetime.now()
            delta = present - parse_date(image["CreationDate"])
            if delta.days > min_age_days:
                filtered_images.append(image)
            else:
                _logger.info(f"AMI does not meet age threshold, filtering: {image['ImageId']}")
                filtered_count = filtered_count + 1
        else:
            filtered_images.append(image)

    return filtered_images, filtered_count


def filter_images_by_excluded(images, excluded_image_ids):
    def is_ami_in_use(image_id, used_ami_ids):
        return image_id in used_ami_ids

    filtered_images = []
    filtered_count = 0
    for image in images:
        if is_ami_in_use(image_id=image["ImageId"], used_ami_ids=excluded_image_ids):
            _logger.info(f"AMI has been excluded, filtering: {image['ImageId']}")
            filtered_count = filtered_count + 1
        else:
            filtered_images.append(image)

    return filtered_images, filtered_count


def filter_images_by_keep(images, keep):
    # noinspection PyChainedComparisons
    if keep >= 0 and len(images) > keep:
        _logger.info(f"Excluding {keep} most recent matching AMIs...")
        return images[0:(len(images) - keep)]
    else:
        return images


def sort_images_by_creation_date_asc(images):
    def sorter(element):
        return element["CreationDate"]

    images.sort(key=sorter)

    return images


def filter_images(images, keep=-1, min_age_days=-1, excluded_image_ids=None):
    if excluded_image_ids is None:
        excluded_image_ids = []

    images = sort_images_by_creation_date_asc(images)

    images = filter_images_by_keep(images=images, keep=keep)

    images, filtered_by_age_count = filter_images_by_age(
        images=images, min_age_days=min_age_days
    )

    images, filtered_by_excluded = filter_images_by_excluded(
        images=images, excluded_image_ids=excluded_image_ids
    )

    _logger.info(
        f"{len(images)} AMIs remain after filtering, {filtered_by_age_count} were excluded because of age "
        f"and {filtered_by_excluded} were filtered because they are in the excludes list..."
    )

    return images


def deregister_images_and_snapshots(ec2_client, images, dry_run):
    images = images or []
    for image in images:
        deregister_image(ec2_client=ec2_client, image=image, dry_run=dry_run)

        for block_device in image["BlockDeviceMappings"]:
            if "Ebs" in block_device and "SnapshotId" in block_device["Ebs"]:
                snapshot_id = block_device["Ebs"]["SnapshotId"]
                delete_snapshot(ec2_client=ec2_client, snapshot_id=snapshot_id, dry_run=dry_run)


def clean_images(
        ec2_client,
        name_pattern,
        min_age_days=90, keep=3,
        excluded_image_ids=None,
        force=False,
        dry_run=True,
):
    _logger.info(f"Fetching AMIs matching name '{name_pattern}' with a min age of {min_age_days} days...")

    images = fetch_images(ec2_client=ec2_client, name_pattern=name_pattern)

    _logger.info(
        f"Found {len(images)} AMIs matching '{name_pattern}'..."
    )

    images = filter_images(images=images, keep=keep, min_age_days=min_age_days, excluded_image_ids=excluded_image_ids)

    if len(images) == 0:
        _logger.info(f"No AMIs found for removal...")
        sys.exit(0)

    _logger.info(f"The following AMIs are going to be removed:")
    for image in images:
        _logger.info(image_to_string(image=image))

    if not force:
        confirmation_input = input(f"Proceed with the removal of {len(images)} AMIs (Y/N)? ")
        if "Y" == confirmation_input or "y" == confirmation_input:
            deregister_images_and_snapshots(ec2_client=ec2_client, images=images, dry_run=dry_run)
    else:
        _logger.info(f"Proceeding with forced removal of {len(images)} AMIs...")
        deregister_images_and_snapshots(ec2_client=ec2_client, images=images, dry_run=dry_run)
