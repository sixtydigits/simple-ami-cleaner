# A Simple AWS EC2 Cleaner

## Summary
Removing AMIs via the EC2 UI is a time-consuming joke, this script aims to provide an 
easy-to-understand tool with plenty of safeguards (deleting AMIs can be scary) that can
quickly and easily 'deregister' AMIs and delete their associated snapshots.

This tool is inspired by https://github.com/bonclay7/aws-amicleaner which offers more
complex functionality.

## Using the tool
By default the tool will run in dry run mode (`--dry-run=true`) showing you what actions it would take
if executed. 

```shell
$ simple-ami-cleaner -h
usage: simple-ami-cleaner [-h] [--min_age_days MIN_AGE_DAYS] [--keep KEEP] [--exclude_images EXCLUDE_IMAGES] [--dry-run DRY_RUN] [--force FORCE] [--version] [-v] name_pattern

A tool to clean EC2 AMIs and associated snapshots

positional arguments:
  name_pattern          The AMI name patterns (e.g. some*name*amd64*).

options:
  -h, --help            show this help message and exit
  --min_age_days MIN_AGE_DAYS
                        The min age of an AMI to considered for cleanup (default 90), use '-1' to disable age based checks.
  --keep KEEP           The number of recent AMIs to keep excluding them from the list of candidate AMIs, use '-1' (default) to consider all AMIs.
  --exclude_images EXCLUDE_IMAGES
                        A comma separated list of AMI ImageIds to exclude OR a special value of 'USED' which will query for AMIs that are associated with running EC2 instances (on the current account, this does *NOT* work in cross-account scenarios).
  --dry-run DRY_RUN     Simulate a clean without actually deleting anything (default True).
  --force FORCE         Skips user prompts to confirm destructive actions.
  --version             show program's version number and exit
  -v, --verbose         Set loglevel to DEBUG
```

### Examples

#### Remove AMI more than 90 days old, keeping the last 2 no matter their age
```shell
$ aws-vault exec Operations -- \
    simple-ami-cleaner --keep=2 --min_age_days=90 --exclude_images=USED 'my-bastion*'
[2022-10-09 14:12:31] INFO:botocore.credentials:Found credentials in environment variables.
[2022-10-09 14:12:32] INFO:simple_ami_cleaner.ami_cleaner:Found 5 AMIs currently in use...
[2022-10-09 14:12:32] INFO:simple_ami_cleaner.ami_cleaner:Found 4 AMIs matching 'my-bastion*'...
[2022-10-09 14:12:32] INFO:simple_ami_cleaner.ami_cleaner:Excluding 2 most recent matching AMIs...
[2022-10-09 14:12:32] INFO:simple_ami_cleaner.ami_cleaner:2 AMIs remain after filtering, 0 were excluded because of age and 0 were filtered because they are in the excludes list...
[2022-10-09 14:12:32] INFO:simple_ami_cleaner.ami_cleaner:The following AMIs are going to be removed:
[2022-10-09 14:12:32] INFO:simple_ami_cleaner.ami_cleaner:ImageId: ami-345a3d2b453452354, Name: my-bastion-amd64-next-20220607, CreationDate: 2022-06-07T04:07:34.000Z
[2022-10-09 14:12:32] INFO:simple_ami_cleaner.ami_cleaner:ImageId: ami-399a3d2b453452551, Name: my-bastion-amd64-next-20220607, CreationDate: 2022-06-07T05:08:43.000Z
Proceed with the removal of 2 AMIs (Y/N)? y
[2022-10-09 14:17:30] INFO:simple_ami_cleaner.ami_cleaner:Deregistering AMI: ImageId: ami-345a3d2b453452354, Name: my-bastion-amd64-next-20220607, CreationDate: 2022-06-07T04:07:34.000Z
[2022-10-09 14:17:30] INFO:simple_ami_cleaner.ami_cleaner:Skipping deregistering AMI in dry-run mode
[2022-10-09 14:17:30] INFO:simple_ami_cleaner.ami_cleaner:Deleting snapshot snap-038efa4496b9a2dfa
[2022-10-09 14:17:30] INFO:simple_ami_cleaner.ami_cleaner:Skipping deleting snapshot in dry-run mode
[2022-10-09 14:17:30] INFO:simple_ami_cleaner.ami_cleaner:Deregistering AMI: ImageId: ami-399a3d2b453452551, Name: my-bastion-amd64-next-20220607, CreationDate: 2022-06-07T05:08:43.000Z
[2022-10-09 14:17:30] INFO:simple_ami_cleaner.ami_cleaner:Skipping deregistering AMI in dry-run mode
[2022-10-09 14:17:30] INFO:simple_ami_cleaner.ami_cleaner:Deleting snapshot snap-021bf89b915af6337
[2022-10-09 14:17:30] INFO:simple_ami_cleaner.ami_cleaner:Skipping deleting snapshot in dry-run mode
```

## Build and Test
The tool builds using [TOX](https://tox.wiki/en/latest/) (e.g. `pip3 install tox`).

### Executing the tests
```shell
$ tox
...
================================ 7 passed in 0.05s ================================
_____________________________________ summary _____________________________________
  default: commands succeeded
  congratulations :)

```

### Build and install locally
```shell
$ tox -e build && pip3 install .
...
Successfully installed simple-ami-cleaner-0.0.post1.dev2+gb19da5a.d20221009

$ simple-ami-cleaner
usage: simple-ami-cleaner [-h] [--min_age_days MIN_AGE_DAYS] [--keep KEEP] [--exclude_images EXCLUDE_IMAGES] [--dry-run DRY_RUN] [--force FORCE] [--version] [-v] name_pattern
```