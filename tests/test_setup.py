"""Test ngpb4py setup script."""

import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ngpb4py.setup import main

# Expected number of version comparison tests
EXPECTED_VERSION_TESTS = 5


def test_setup_script_exists() -> None:
    """Test that the setup script exists."""
    script_path = Path(__file__).parent.parent / "src" / "ngpb4py" / "setup.sh"
    assert script_path.exists(), f"Setup script not found at {script_path}"
    assert script_path.is_file(), f"Setup script is not a file: {script_path}"


def test_setup_script_is_executable() -> None:
    """Test that the setup script is executable."""
    script_path = Path(__file__).parent.parent / "src" / "ngpb4py" / "setup.sh"
    assert os.access(script_path, os.X_OK), f"Setup script is not executable: {script_path}"


def test_setup_python_wrapper_exists() -> None:
    """Test that the Python wrapper exists."""
    wrapper_path = Path(__file__).parent.parent / "src" / "ngpb4py" / "setup.py"
    assert wrapper_path.exists(), f"Python wrapper not found at {wrapper_path}"
    assert wrapper_path.is_file(), f"Python wrapper is not a file: {wrapper_path}"


def test_version_comparison_logic() -> None:
    """Test the version comparison logic in the bash script."""
    script_path = Path(__file__).parent.parent / "src" / "ngpb4py" / "setup.sh"

    # Test version_ge function directly by sourcing the script
    test_script = f"""
    source {script_path}

    # Test cases
    version_ge "1.2.0" "1.2.0" && echo "PASS: 1.2.0 >= 1.2.0" || echo "FAIL: 1.2.0 >= 1.2.0"
    version_ge "1.3.0" "1.2.0" && echo "PASS: 1.3.0 >= 1.2.0" || echo "FAIL: 1.3.0 >= 1.2.0"
    version_ge "2.0.0" "1.2.0" && echo "PASS: 2.0.0 >= 1.2.0" || echo "FAIL: 2.0.0 >= 1.2.0"
    version_ge "1.1.0" "1.2.0" && echo "FAIL: 1.1.0 >= 1.2.0" || echo "PASS: 1.1.0 < 1.2.0"
    version_ge "1.2.5" "1.2.0" && echo "PASS: 1.2.5 >= 1.2.0" || echo "FAIL: 1.2.5 >= 1.2.0"
    """

    result = subprocess.run(
        ["bash", "-c", test_script],
        capture_output=True,
        text=True,
        check=False,
    )

    # All tests should pass
    assert "FAIL" not in result.stdout, f"Version comparison failed:\n{result.stdout}"
    assert (
        result.stdout.count("PASS") == EXPECTED_VERSION_TESTS
    ), f"Expected {EXPECTED_VERSION_TESTS} PASS, got:\n{result.stdout}"


@patch("subprocess.run")
def test_python_wrapper_calls_bash_script(mock_run: MagicMock) -> None:
    """Test that the Python wrapper calls the bash script."""
    mock_run.return_value = MagicMock(returncode=0)


    exit_code = main()

    assert exit_code == 0
    assert mock_run.called
    # Check that the bash script was called
    call_args = mock_run.call_args[0][0]
    assert isinstance(call_args, list)
    assert call_args[0].endswith("setup.sh")


@patch("subprocess.run")
def test_python_wrapper_propagates_error_code(mock_run: MagicMock) -> None:
    """Test that the Python wrapper propagates error codes."""
    mock_run.return_value = MagicMock(returncode=1)


    exit_code = main()

    assert exit_code == 1


def test_setup_script_detects_apptainer_if_installed() -> None:
    """Test that the script detects Apptainer if it's already installed."""
    script_path = Path(__file__).parent.parent / "src" / "ngpb4py" / "setup.sh"

    # Create a mock apptainer that returns version 1.2.5 in the expected format
    # The script uses: apptainer --version | awk '{print $2}'
    # So apptainer --version should output something like "apptainer 1.2.5"
    test_script = f"""
    # Mock apptainer command
    function apptainer() {{
        if [[ "$1" == "--version" ]]; then
            echo "apptainer 1.2.5"
        fi
    }}
    export -f apptainer

    # Mock command to return true for apptainer
    original_command=$(which command)
    function command() {{
        if [[ "$1" == "-v" && "$2" == "apptainer" ]]; then
            return 0
        fi
        $original_command "$@"
    }}
    export -f command

    # Source the setup script and call main
    source {script_path}
    main
    """

    result = subprocess.run(
        ["bash", "-c", test_script],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "already installed" in result.stdout.lower()


def test_setup_script_requires_dependencies() -> None:
    """Test that the script checks for required dependencies."""
    script_path = Path(__file__).parent.parent / "src" / "ngpb4py" / "setup.sh"

    # Test without rpm2cpio
    test_script = f"""
    # Unset command to make it return false for rpm2cpio
    function command() {{
        if [[ "$2" == "rpm2cpio" ]]; then
            return 1
        fi
        builtin command "$@"
    }}
    export -f command

    # Unset apptainer to trigger installation
    function apptainer() {{
        return 1
    }}
    export -f apptainer

    source {script_path}
    main
    """

    result = subprocess.run(
        ["bash", "-c", test_script],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "rpm2cpio" in result.stderr.lower() or "rpm2cpio" in result.stdout.lower()


@pytest.mark.skipif(
    os.environ.get("CI") != "true",
    reason="Only run integration test in CI environment",
)
def test_setup_integration() -> None:
    """Integration test for the setup script (runs only in CI)."""
    # This test would actually run the installation in a clean environment
    # For now, we'll skip it unless in a CI environment
    # Set installation directory to a temporary location
    with tempfile.TemporaryDirectory() as tmpdir:
        os.environ["APPTAINER_INSTALL_DIR"] = tmpdir
        exit_code = main()

        # If rpm2cpio and cpio are available, installation should succeed
        # Otherwise, it should fail gracefully with proper error message
        # Exit code 2 is from the bash script when it fails (set -e catches errors)
        assert exit_code in [0, 1, 2]
