from src.perception.element_detector import detect_regions, find_relevant_regions
from src.perception.ocr import OCRWord


def test_detect_regions_classifies_button_by_keyword():
    words = [OCRWord(text="Submit", bbox=(10, 20, 60, 15), confidence=95.0)]
    regions = detect_regions(words)
    assert len(regions) == 1
    assert regions[0].kind == "button"
    assert regions[0].center == (10 + 30, 20 + 7)


def test_detect_regions_classifies_field_by_colon():
    words = [OCRWord(text="Username:", bbox=(0, 0, 80, 15), confidence=90.0)]
    regions = detect_regions(words)
    assert regions[0].kind == "field"


def test_detect_regions_classifies_plain_text():
    words = [OCRWord(text="Welcome", bbox=(0, 0, 80, 15), confidence=90.0)]
    regions = detect_regions(words)
    assert regions[0].kind == "text"


def test_find_relevant_regions_filters_by_keyword():
    words = [
        OCRWord(text="Star", bbox=(0, 0, 30, 10), confidence=90.0),
        OCRWord(text="Fork", bbox=(40, 0, 30, 10), confidence=90.0),
        OCRWord(text="Watch", bbox=(80, 0, 30, 10), confidence=90.0),
    ]
    regions = detect_regions(words)
    matches = find_relevant_regions(regions, ["star"])
    assert len(matches) == 1
    assert matches[0].text == "Star"


def test_find_relevant_regions_no_keywords_returns_empty():
    words = [OCRWord(text="Star", bbox=(0, 0, 30, 10), confidence=90.0)]
    regions = detect_regions(words)
    assert find_relevant_regions(regions, []) == []


def test_find_relevant_regions_no_match_returns_empty():
    words = [OCRWord(text="Star", bbox=(0, 0, 30, 10), confidence=90.0)]
    regions = detect_regions(words)
    assert find_relevant_regions(regions, ["nonexistent"]) == []
