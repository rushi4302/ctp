from collections import Counter
from io import BytesIO

from PIL import Image

from scripts.seed_demo_data import (
    DEMO_PREFIX,
    LOCALITIES,
    SCENARIOS,
    STATUS_VALUES,
    build_cases,
    render_demo_image,
)


def test_demo_cases_have_expected_counts_and_supported_distribution():
    cases = build_cases()
    assert len(cases) == 36
    assert len({case.title for case in cases}) == 36
    assert all(case.title.startswith(DEMO_PREFIX) for case in cases)
    assert set(case.category for case in cases) == set(SCENARIOS)
    assert Counter(case.status for case in cases) == Counter(STATUS_VALUES)
    assert set(case.locality for case in cases) == set(LOCALITIES)
    assert all(18.25 <= case.latitude <= 18.75 for case in cases)
    assert all(73.65 <= case.longitude <= 74.15 for case in cases)
    assert all("not a citizen submission" in case.description for case in cases)


def test_demo_images_are_distinct_valid_jpegs_and_resolution_visuals_are_marked():
    cases = build_cases()
    issue_image = render_demo_image(cases[0])
    another_image = render_demo_image(cases[1])
    resolution_image = render_demo_image(cases[0], resolution=True)

    assert issue_image.startswith(b"\xff\xd8")
    assert issue_image != another_image
    assert resolution_image != issue_image
    with Image.open(BytesIO(issue_image)) as image:
        assert image.format == "JPEG"
        assert image.size == (960, 640)
