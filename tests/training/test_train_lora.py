import subprocess
import sys


def test_module_imports_without_gpu_training_deps():
    """The whole point of deferring peft/transformers/datasets imports
    inside train() is that this module must import cleanly on a machine
    that hasn't installed them yet (e.g. this project's CI/sandbox)."""
    import training.train_lora  # noqa: F401 - import success is the assertion


def test_help_output_runs_without_gpu_training_deps():
    result = subprocess.run(
        [sys.executable, "-m", "training.train_lora", "--help"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0
    assert "--base-model" in result.stdout
    assert "--target" in result.stdout


def test_missing_required_args_fails_cleanly():
    result = subprocess.run(
        [sys.executable, "-m", "training.train_lora"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "required" in result.stderr.lower()
