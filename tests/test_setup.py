"""Tests for ngpb4py-setup script and Apptainer installation."""

import subprocess
import sys


def test_ngpb4py_setup_installs_apptainer():
    """Run ngpb4py-setup and verify Apptainer is installed."""
    result = subprocess.run(
        [sys.executable, "-m", "ngpb4py.setup"], check=True, capture_output=True, text=True
    )
    assert result.returncode == 0, f"ngpb4py-setup failed: {result.stderr}"
    apptainer_check = subprocess.run(
        ["apptainer", "--version"], check=True, capture_output=True, text=True
    )
    assert apptainer_check.returncode == 0, "Apptainer not installed after running ngpb4py-setup"
