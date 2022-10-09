import pytest
from datetime import datetime

from simple_ami_cleaner.ami_cleaner import sort_images_by_creation_date_asc, \
    filter_images_by_age, filter_images_by_excluded, filter_images_by_keep, filter_images, format_date

__author__ = "Dan Washusen"
__license__ = "MIT"

def find_index(image_id, images):
    for index, image in enumerate(images):
        if image['ImageId'] == image_id:
            return index

def test_sort_images_by_creation_date_asc():
    now = datetime.now()
    images = [
        {
            "ImageId": "abc124",
            "CreationDate": format_date(datetime(2021, 1, 21))
        },
        {
            "ImageId": "abc125",
            "CreationDate": format_date(datetime(now.year, now.month, now.day))
        },
        {
            "ImageId": "abc123",
            "CreationDate": format_date(datetime(2021, 1, 20))
        },
    ]

    images = sort_images_by_creation_date_asc(images)

    assert find_index(image_id="abc123", images=images) == 0
    assert find_index(image_id="abc124", images=images) == 1
    assert find_index(image_id="abc125", images=images) == 2


def test_filter_images_by_age():
    now = datetime.now()
    images = sort_images_by_creation_date_asc([
        {
            "ImageId": "abc123",
            "CreationDate": format_date(datetime(2021, 1, 20))
        },
        {
            "ImageId": "abc124",
            "CreationDate": format_date(datetime(2021, 1, 20))
        },
        {
            "ImageId": "abc125",
            "CreationDate": format_date(datetime(now.year, now.month, now.day))
        },
    ])

    filtered_images, filter_count = filter_images_by_age(images=images, min_age_days=3)

    assert len(filtered_images) == 2

    assert sum(1 for image in filtered_images if image['ImageId'] == "abc123") == 1
    assert sum(1 for image in filtered_images if image['ImageId'] == "abc124") == 1


def test_filter_images_by_excluded():
    now = datetime.now()
    images = sort_images_by_creation_date_asc([
        {
            "ImageId": "abc123",
            "CreationDate": format_date(datetime(2021, 1, 20))
        },
        {
            "ImageId": "abc124",
            "CreationDate": format_date(datetime(2021, 1, 20))
        },
        {
            "ImageId": "abc125",
            "CreationDate": format_date(datetime(now.year, now.month, now.day))
        },
    ])

    filtered_images, filter_count = filter_images_by_excluded(images=images, excluded_image_ids=["abc125"])

    assert len(filtered_images) == 2

    assert sum(1 for image in filtered_images if image['ImageId'] == "abc123") == 1
    assert sum(1 for image in filtered_images if image['ImageId'] == "abc124") == 1


def test_filter_images_by_keep():
    now = datetime.now()
    images = sort_images_by_creation_date_asc([
        {
            "ImageId": "abc123",
            "CreationDate": format_date(datetime(2021, 1, 20))
        },
        {
            "ImageId": "abc124",
            "CreationDate": format_date(datetime(2021, 1, 21))
        },
        {
            "ImageId": "abc125",
            "CreationDate": format_date(datetime(now.year, now.month, now.day))
        },
    ])

    keep = 2
    filtered_images = filter_images_by_keep(images=images, keep=keep)

    assert len(filtered_images) == (len(images) - keep)

    assert sum(1 for image in filtered_images if image['ImageId'] == "abc123") == 1


def test_filter_images_by_keep_honours_negative_value():
    now = datetime.now()
    images = sort_images_by_creation_date_asc([
        {
            "ImageId": "abc123",
            "CreationDate": format_date(datetime(2021, 1, 20))
        },
        {
            "ImageId": "abc124",
            "CreationDate": format_date(datetime(2021, 1, 21))
        },
        {
            "ImageId": "abc125",
            "CreationDate": format_date(datetime(now.year, now.month, now.day))
        },
    ])

    filtered_images = filter_images_by_keep(images=images, keep=-1)

    assert len(filtered_images) == len(images)


def test_filter_images_with_all_three_filters():
    now = datetime.now()
    images = [
        {
            "ImageId": "abc128",
            "CreationDate": format_date(datetime(now.year, now.month, now.day))
        },
        {
            "ImageId": "abc124",
            "CreationDate": format_date(datetime(2021, 1, 21))
        },
        {
            "ImageId": "abc125",
            "CreationDate": format_date(datetime(2021, 1, 22))
        },
        {
            "ImageId": "abc126",
            "CreationDate": format_date(datetime(2021, 1, 23))
        },
        {
            "ImageId": "abc123",
            "CreationDate": format_date(datetime(2021, 1, 20))
        },
        {
            "ImageId": "abc127",
            "CreationDate": format_date(datetime(2021, 1, 24))
        },
    ]

    remaining_images = filter_images(images=images, min_age_days=2, excluded_image_ids=["abc124"], keep=3)

    assert len(remaining_images) == 2

    assert sum(1 for image in remaining_images if image['ImageId'] == "abc124") == 0
    assert sum(1 for image in remaining_images if image['ImageId'] == "abc126") == 0
    assert sum(1 for image in remaining_images if image['ImageId'] == "abc127") == 0
    assert sum(1 for image in remaining_images if image['ImageId'] == "abc128") == 0


def test_filter_images_with_no_keep():
    now = datetime.now()
    images = [
        {
            "ImageId": "abc128",
            "CreationDate": format_date(datetime(now.year, now.month, now.day))
        },
        {
            "ImageId": "abc124",
            "CreationDate": format_date(datetime(2021, 1, 21))
        },
        {
            "ImageId": "abc125",
            "CreationDate": format_date(datetime(2021, 1, 22))
        },
        {
            "ImageId": "abc126",
            "CreationDate": format_date(datetime(2021, 1, 23))
        },
        {
            "ImageId": "abc123",
            "CreationDate": format_date(datetime(2021, 1, 20))
        },
        {
            "ImageId": "abc127",
            "CreationDate": format_date(datetime(2021, 1, 24))
        },
    ]

    remaining_images = filter_images(images=images, min_age_days=2, excluded_image_ids=["abc124"], keep=-1)

    assert len(remaining_images) == 4

    assert sum(1 for image in remaining_images if image['ImageId'] == "abc124") == 0
    assert sum(1 for image in remaining_images if image['ImageId'] == "abc128") == 0
