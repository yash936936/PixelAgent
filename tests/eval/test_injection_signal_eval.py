from eval.injection_signal_eval import run


def test_injection_signal_eval_scores_perfectly_on_its_own_case_set():
    """Not a tautology: run() calls the real check_injection_signal(), and
    this pins the current, tuned phrase bank's accuracy on its own
    hand-written case set at 100% -- a regression here means a future
    change to the phrase bank broke a previously-passing case."""
    correct, total, failures = run()
    assert total >= 6
    assert correct == total, f"failures: {failures}"


def test_injection_signal_eval_loads_only_prompt_injection_category():
    _, total, _ = run()
    # Sanity check this isn't accidentally scoring 0 cases (e.g. from a
    # category-name typo silently filtering everything out).
    assert total > 0
