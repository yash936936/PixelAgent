from PIL import Image

from src.perception.screen_diff import compare, matches_expected


def _solid_image(color, size=(100, 100)):
    return Image.new("RGB", size, color)


def test_identical_images_not_changed():
    img_a = _solid_image((10, 10, 10))
    img_b = _solid_image((10, 10, 10))
    result = compare(img_a, img_b)
    assert result.changed is False
    assert result.change_ratio == 0.0


def test_completely_different_images_changed():
    img_a = _solid_image((0, 0, 0))
    img_b = _solid_image((255, 255, 255))
    result = compare(img_a, img_b)
    assert result.changed is True
    assert result.change_ratio > 0.5


def test_different_sizes_always_changed():
    img_a = _solid_image((0, 0, 0), size=(100, 100))
    img_b = _solid_image((0, 0, 0), size=(200, 200))
    result = compare(img_a, img_b)
    assert result.changed is True
    assert result.change_ratio == 1.0


def test_matches_expected_true_case():
    img_a = _solid_image((0, 0, 0))
    img_b = _solid_image((255, 255, 255))
    assert matches_expected(img_a, img_b, expect_change=True) is True


def test_matches_expected_false_case_mismatch():
    # Screen changed but step expected NO change -> mismatch -> False
    img_a = _solid_image((0, 0, 0))
    img_b = _solid_image((255, 255, 255))
    assert matches_expected(img_a, img_b, expect_change=False) is False


def test_matches_expected_no_change_when_expected_none():
    img_a = _solid_image((10, 10, 10))
    img_b = _solid_image((10, 10, 10))
    assert matches_expected(img_a, img_b, expect_change=False) is True
