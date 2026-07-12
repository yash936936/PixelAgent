from src.gui.widgets.task_composer import TaskComposer


def test_run_requested_emitted_on_button_click(qapp):
    composer = TaskComposer()
    captured = []
    composer.run_requested.connect(captured.append)

    composer._input.setText("open github and star repo X")
    composer._emit_run()

    assert captured == ["open github and star repo X"]


def test_empty_input_does_not_emit(qapp):
    composer = TaskComposer()
    captured = []
    composer.run_requested.connect(captured.append)

    composer._input.setText("   ")
    composer._emit_run()

    assert captured == []


def test_set_running_disables_input_and_button(qapp):
    composer = TaskComposer()
    composer.set_running(True)
    assert composer._run_btn.isEnabled() is False
    assert composer._input.isEnabled() is False
    assert composer._run_btn.text() == "Running…"

    composer.set_running(False)
    assert composer._run_btn.isEnabled() is True
    assert composer._input.isEnabled() is True
