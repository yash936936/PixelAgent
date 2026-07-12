from src.gui import style


def test_colors_match_tokens_json():
    assert style.INK_BLACK == "#17191c"
    assert style.BLUSH_PEACH == "#fbe1d1"
    assert style.SIENNA_BROWN == "#5d2a1a"


def test_spacing_scale_has_expected_values():
    assert style.SPACING[4] == 4
    assert style.SPACING[24] == 24
    assert style.SPACING[80] == 80


def test_build_stylesheet_contains_all_risk_colors():
    qss = style.build_stylesheet()
    assert style.INK_BLACK in qss
    assert isinstance(qss, str) and len(qss) > 0


def test_risk_card_qss_local():
    qss = style.risk_card_qss("local")
    assert style.MIST_GRAY in qss
    assert style.INK_BLACK in qss


def test_risk_card_qss_external_uses_peach_and_ink_black():
    qss = style.risk_card_qss("external")
    assert style.BLUSH_PEACH in qss
    assert style.INK_BLACK in qss


def test_risk_card_qss_destructive_uses_peach_and_sienna():
    qss = style.risk_card_qss("destructive")
    assert style.BLUSH_PEACH in qss
    assert style.SIENNA_BROWN in qss


def test_risk_card_qss_unknown_falls_back_to_local():
    assert style.risk_card_qss("bogus") == style.risk_card_qss("local")


def test_external_and_destructive_share_background_but_differ_in_ink():
    external = style.RISK_STYLE["external"]
    destructive = style.RISK_STYLE["destructive"]
    assert external["bg"] == destructive["bg"] == style.BLUSH_PEACH
    assert external["ink"] != destructive["ink"]
