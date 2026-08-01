from src.brain.risk_classifier import Risk
from src.brain.risk_model_backend import (
    RiskModelBackend,
    SemanticRiskJudge,
    semantic_boundary_match,
)


def test_semantic_risk_judge_is_a_risk_model_backend():
    assert issubclass(SemanticRiskJudge, RiskModelBackend)


def test_semantic_risk_judge_catches_destructive_paraphrase_without_keyword():
    judge = SemanticRiskJudge()
    # Deliberately avoids every literal keyword in risk_classifier.py's
    # _DESTRUCTIVE_KEYWORDS list -- the exact gap this module exists to close.
    result = judge.judge({"action": "click", "description": "make this go away for good"})
    assert result == Risk.DESTRUCTIVE


def test_semantic_risk_judge_catches_external_paraphrase_without_keyword():
    judge = SemanticRiskJudge()
    result = judge.judge({"action": "click", "description": "let everyone else see this now"})
    assert result == Risk.EXTERNAL


def test_semantic_risk_judge_returns_none_below_threshold():
    judge = SemanticRiskJudge(threshold=0.9)
    result = judge.judge({"action": "click", "description": "scroll down a little"})
    assert result is None


def test_semantic_risk_judge_returns_none_on_empty_step():
    judge = SemanticRiskJudge()
    assert judge.judge({}) is None


def test_semantic_risk_judge_respects_read_only_framing_guard():
    judge = SemanticRiskJudge()
    # Mirrors risk_classifier's own read-only guard case (adv_016-style):
    # inspecting whether something exists must not escalate.
    result = judge.judge(
        {"action": "click", "description": "check if the delete button exists on this page"}
    )
    assert result is None


def test_semantic_risk_judge_read_only_guard_does_not_suppress_trailing_real_action():
    judge = SemanticRiskJudge()
    result = judge.judge(
        {
            "action": "click",
            "description": "check if delete works, then click delete to destroy this data",
        }
    )
    assert result == Risk.DESTRUCTIVE


def test_semantic_boundary_match_catches_captcha_euphemism():
    match = semantic_boundary_match(
        {"action": "click", "description": "please solve the little puzzle so the site lets us through"}
    )
    assert match is not None
    label, score, exemplar = match
    assert label == "captcha_bot_detection_bypass"
    assert score > 0.0


def test_semantic_boundary_match_returns_none_for_unrelated_text():
    match = semantic_boundary_match({"action": "click", "description": "scroll down to see more results"})
    assert match is None


def test_semantic_boundary_match_returns_none_on_empty_step():
    assert semantic_boundary_match({}) is None
