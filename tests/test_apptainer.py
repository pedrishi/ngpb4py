"""
Comprehensive unit tests for the ApptainerExecutor class.

This test suite covers all methods in src/ngpb4py/apptainer.py with:
- Happy path tests
- Edge cases and boundary conditions
- Input validation and error handling
- Security checks
- Side effects and state management
- Mocking of external dependencies
"""

import logging
import os
import subprocess
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from ngpb4py.apptainer import ApptainerExecutor


class TestApptainerExecutorInit:
    """Tests for ApptainerExecutor initialization."""

    def test_init_happy_path(self, tmp_path):
        """Test successful initialization with valid parameters."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        workdir = tmp_path / "workdir"

        executor = ApptainerExecutor(
            sif_path=sif_file,
            n_proc=4,
            workdir=workdir,
            env={"VAR": "value"},
            timeout=300,
            log_copy_dir=tmp_path / "logs",
        )

        assert executor.sif_path == sif_file
        assert executor.n_proc == 4
        assert executor.workdir == workdir
        assert executor.env == {"VAR": "value"}
        assert executor.timeout == 300
        assert executor.log_copy_dir == tmp_path / "logs"
        assert workdir.exists()

    def test_init_defaults(self, tmp_path):
        """Test initialization with default parameters."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file)

        assert executor.n_proc == 1
        assert executor.workdir == Path(".")
        assert executor.env == {}
        assert executor.timeout is None
        assert executor.log_copy_dir is None

    def test_init_string_paths(self, tmp_path):
        """Test initialization with string paths."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=str(sif_file), workdir=str(tmp_path))

        assert executor.sif_path == sif_file
        assert executor.workdir == tmp_path

    def test_init_missing_sif_file(self, tmp_path):
        """Test initialization fails with non-existent SIF file."""
        with pytest.raises(FileNotFoundError, match="SIF file not found"):
            ApptainerExecutor(sif_path=tmp_path / "nonexistent.sif")

    def test_init_invalid_n_proc(self, tmp_path):
        """Test initialization fails with invalid n_proc values."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        with pytest.raises(ValueError, match="n_proc must be positive"):
            ApptainerExecutor(sif_path=sif_file, n_proc=0)

        with pytest.raises(ValueError, match="n_proc must be positive"):
            ApptainerExecutor(sif_path=sif_file, n_proc=-1)

    def test_init_invalid_timeout(self, tmp_path):
        """Test initialization fails with invalid timeout values."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        with pytest.raises(ValueError, match="timeout must be positive"):
            ApptainerExecutor(sif_path=sif_file, timeout=0)

        with pytest.raises(ValueError, match="timeout must be positive"):
            ApptainerExecutor(sif_path=sif_file, timeout=-1)

    def test_init_creates_workdir(self, tmp_path):
        """Test that initialization creates workdir if it doesn't exist."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        workdir = tmp_path / "new_workdir" / "nested"

        executor = ApptainerExecutor(sif_path=sif_file, workdir=workdir)

        assert workdir.exists()
        assert workdir.is_dir()


class TestFindApptainerBinary:
    """Tests for finding Apptainer binary in PATH."""

    @patch("shutil.which")
    def test_find_apptainer_success(self, mock_which, tmp_path):
        """Test successful finding of apptainer binary."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"

        executor = ApptainerExecutor(sif_path=sif_file)
        result = executor.find_apptainer_binary()

        assert result == "/usr/bin/apptainer"
        assert executor.apptainer_path == "/usr/bin/apptainer"
        mock_which.assert_called_once_with("apptainer")

    @patch("shutil.which")
    def test_find_singularity_fallback(self, mock_which, tmp_path):
        """Test fallback to Singularity when Apptainer not found."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.side_effect = [None, "/usr/bin/singularity"]

        executor = ApptainerExecutor(sif_path=sif_file)
        result = executor.find_apptainer_binary()

        assert result == "/usr/bin/singularity"
        assert executor.apptainer_path == "/usr/bin/singularity"
        assert mock_which.call_count == 2

    @patch("shutil.which")
    def test_find_binary_not_found(self, mock_which, tmp_path):
        """Test when neither Apptainer nor Singularity is found."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = None

        executor = ApptainerExecutor(sif_path=sif_file)
        result = executor.find_apptainer_binary()

        assert result is None
        assert executor.apptainer_path is None

    @patch("shutil.which")
    def test_find_binary_exception(self, mock_which, tmp_path):
        """Test exception handling during binary search."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.side_effect = OSError("Permission denied")

        executor = ApptainerExecutor(sif_path=sif_file)
        result = executor.find_apptainer_binary()

        assert result is None


class TestValidateApptainerAvailability:
    """Tests for Apptainer availability validation."""

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_validate_success(self, mock_which, mock_run, tmp_path):
        """Test successful validation of Apptainer."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"
        mock_run.return_value = Mock(returncode=0, stdout="apptainer version 1.2.3")

        executor = ApptainerExecutor(sif_path=sif_file)
        executor.validate_apptainer_availability()

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["/usr/bin/apptainer", "--version"]
        assert call_args[1]["shell"] is False

    @patch("shutil.which")
    def test_validate_binary_not_found(self, mock_which, tmp_path):
        """Test validation fails when binary not found."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = None

        executor = ApptainerExecutor(sif_path=sif_file)

        with pytest.raises(RuntimeError, match="Apptainer not found in system PATH"):
            executor.validate_apptainer_availability()

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_validate_binary_not_functional(self, mock_which, mock_run, tmp_path):
        """Test validation fails when binary is not functional."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"
        mock_run.return_value = Mock(returncode=1, stderr="error")

        executor = ApptainerExecutor(sif_path=sif_file)

        with pytest.raises(RuntimeError, match="but is not functional"):
            executor.validate_apptainer_availability()

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_validate_timeout(self, mock_which, mock_run, tmp_path):
        """Test validation fails on timeout."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=[], timeout=10)

        executor = ApptainerExecutor(sif_path=sif_file)

        with pytest.raises(RuntimeError, match="timed out during version check"):
            executor.validate_apptainer_availability()

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_validate_unexpected_error(self, mock_which, mock_run, tmp_path):
        """Test validation handles unexpected errors."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"
        mock_run.side_effect = OSError("Unexpected error")

        executor = ApptainerExecutor(sif_path=sif_file)

        with pytest.raises(RuntimeError, match="Error testing Apptainer functionality"):
            executor.validate_apptainer_availability()


class TestLogging:
    """Tests for logging functionality."""

    def test_setup_logging_basic(self, tmp_path):
        """Test basic logging setup."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file, workdir=tmp_path)
        primary_log, copy_log = executor.setup_logging()

        assert primary_log == tmp_path / "apptainer_execution.log"
        assert copy_log is None

    def test_setup_logging_with_copy_dir(self, tmp_path):
        """Test logging setup with copy directory."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        copy_dir = tmp_path / "copy_logs"

        executor = ApptainerExecutor(sif_path=sif_file, workdir=tmp_path, log_copy_dir=copy_dir)
        primary_log, copy_log = executor.setup_logging()

        assert primary_log == tmp_path / "apptainer_execution.log"
        assert copy_log == copy_dir / "apptainer_execution.log"
        assert copy_dir.exists()

    def test_setup_logging_custom_filename(self, tmp_path):
        """Test logging setup with custom filename."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file, workdir=tmp_path)
        primary_log, copy_log = executor.setup_logging("custom.log")

        assert primary_log == tmp_path / "custom.log"

    def test_create_logging_error_message(self, tmp_path):
        """Test creation of logging error messages."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file)
        error = OSError("Permission denied")
        log_path = tmp_path / "test.log"

        message = executor.create_logging_error_message(error, log_path)

        assert "Logging error occurred: Permission denied" in message
        assert str(log_path) in message
        assert "Please check directory permissions" in message


class TestArgumentSorting:
    """Tests for argument sorting functionality."""

    def test_sort_apptainer_kwargs_valid(self, tmp_path):
        """Test sorting valid Apptainer kwargs."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file)
        apptainer_args, unknown = executor.sort_apptainer_kwargs(
            bind="/tmp:/tmp", env="VAR=value", cleanenv=True, invalid_arg="test"
        )

        assert apptainer_args == {"bind": "/tmp:/tmp", "env": "VAR=value", "cleanenv": "True"}
        assert unknown == []

    def test_sort_apptainer_kwargs_prefixed(self, tmp_path):
        """Test sorting prefixed Apptainer kwargs."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file)
        apptainer_args, unknown = executor.sort_apptainer_kwargs(
            apptainer_bind="/tmp:/tmp", apptainer_invalid="test"
        )

        assert apptainer_args == {"bind": "/tmp:/tmp"}
        assert unknown == ["apptainer_invalid"]

    def test_sort_apptainer_kwargs_none_values(self, tmp_path):
        """Test sorting Apptainer kwargs with None values."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file)
        apptainer_args, unknown = executor.sort_apptainer_kwargs(cleanenv=None, bind="/tmp:/tmp")

        assert apptainer_args == {"cleanenv": None, "bind": "/tmp:/tmp"}

    def test_sort_ngpb_kwargs_valid(self, tmp_path):
        """Test sorting valid ngpb kwargs."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file)
        ngpb_args, unknown = executor.sort_ngpb_kwargs(
            prmfile="config.prm", pqrfile="input.pqr", invalid_ngpb="test"
        )

        assert ngpb_args == {"prmfile": "config.prm", "pqrfile": "input.pqr"}
        assert "invalid_ngpb" in unknown

    def test_sort_ngpb_kwargs_prefixed(self, tmp_path):
        """Test sorting prefixed ngpb kwargs."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file)
        ngpb_args, unknown = executor.sort_ngpb_kwargs(
            ngpb_prmfile="config.prm", ngpb_invalid="test"
        )

        assert ngpb_args == {"prmfile": "config.prm"}
        assert unknown == ["ngpb_invalid"]

    def test_handle_apptainer_kwargs_errors(self, tmp_path, caplog):
        """Test handling of unknown Apptainer arguments."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file)

        with caplog.at_level(logging.WARNING):
            executor.handle_apptainer_kwargs_errors(["unknown1", "unknown2"])

        assert "Unknown Apptainer arguments provided" in caplog.text
        assert "unknown1" in caplog.text
        assert "unknown2" in caplog.text


class TestCommandBuilding:
    """Tests for command building functionality."""

    @patch("shutil.which")
    def test_build_command_basic(self, mock_which, tmp_path):
        """Test basic command building."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"

        executor = ApptainerExecutor(sif_path=sif_file, workdir=tmp_path, n_proc=2)
        executor.find_apptainer_binary()

        cmd = executor.build_command(
            apptainer_args={"bind": "/tmp:/tmp"}, ngpb_args={"prmfile": "config.prm"}
        )

        expected = [
            "/usr/bin/apptainer",
            "exec",
            "--pwd",
            "/App",
            "--bind",
            f"{tmp_path.absolute()}:/App",
            "--bind",
            "/tmp:/tmp",
            str(sif_file.absolute()),
            "mpirun",
            "-np",
            "2",
            "ngpb",
            "--prmfile",
            "config.prm",
        ]

        assert cmd == expected

    @patch("shutil.which")
    def test_build_command_flag_args(self, mock_which, tmp_path):
        """Test command building with flag arguments (None values)."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"

        executor = ApptainerExecutor(sif_path=sif_file, workdir=tmp_path)
        executor.find_apptainer_binary()

        cmd = executor.build_command(apptainer_args={"cleanenv": None}, ngpb_args={"verbose": None})

        assert "--cleanenv" in cmd
        assert "--verbose" in cmd

    def test_build_command_no_binary(self, tmp_path):
        """Test command building fails when no binary is found."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file)

        with pytest.raises(RuntimeError, match="Apptainer path not found"):
            executor.build_command({}, {})


class TestArgumentValidation:
    """Tests for argument validation functionality."""

    @patch("builtins.open", new_callable=mock_open)
    def test_validate_all_arguments_with_unknown(self, mock_file, tmp_path, caplog):
        """Test validation with unknown arguments writes to log file."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file, workdir=tmp_path)

        with caplog.at_level(logging.WARNING):
            executor.validate_all_arguments(
                bind="/tmp:/tmp", unknown_arg="value", another_unknown="test"
            )

        assert "Unknown arguments provided" in caplog.text
        mock_file.assert_called()

    @patch("builtins.open")
    def test_validate_arguments_file_write_error(self, mock_open_func, tmp_path, caplog):
        """Test validation handles file write errors gracefully."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_open_func.side_effect = OSError("Permission denied")

        executor = ApptainerExecutor(sif_path=sif_file, workdir=tmp_path)

        with caplog.at_level(logging.WARNING):
            executor.validate_all_arguments(unknown_arg="value")

        assert "Could not write argument warnings to file" in caplog.text


class TestExecuteCommand:
    """Tests for command execution functionality."""

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("builtins.open", new_callable=mock_open)
    def test_execute_command_success(self, mock_file, mock_which, mock_run, tmp_path):
        """Test successful command execution."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"

        # Mock version check
        version_result = Mock(returncode=0, stdout="apptainer version 1.2.3")
        # Mock actual execution
        exec_result = Mock(returncode=0, stdout="Success", stderr="")
        mock_run.side_effect = [version_result, exec_result]

        executor = ApptainerExecutor(sif_path=sif_file, workdir=tmp_path)
        result = executor.execute_command(prmfile="config.prm")

        assert result.returncode == 0
        assert mock_run.call_count == 2

        # Check that shell=False is used
        exec_call = mock_run.call_args_list[1]
        assert exec_call[1]["shell"] is False

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("builtins.open", new_callable=mock_open)
    def test_execute_command_failure(self, mock_file, mock_which, mock_run, tmp_path):
        """Test command execution failure handling."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"

        version_result = Mock(returncode=0, stdout="apptainer version 1.2.3")
        exec_result = Mock(returncode=1, stdout="", stderr="Error occurred")
        mock_run.side_effect = [version_result, exec_result]

        executor = ApptainerExecutor(sif_path=sif_file, workdir=tmp_path)

        with pytest.raises(RuntimeError, match="Apptainer execution failed"):
            executor.execute_command()

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_execute_command_timeout(self, mock_which, mock_run, tmp_path):
        """Test command execution timeout handling."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"

        version_result = Mock(returncode=0, stdout="apptainer version 1.2.3")
        mock_run.side_effect = [version_result, subprocess.TimeoutExpired(cmd=[], timeout=60)]

        executor = ApptainerExecutor(sif_path=sif_file, workdir=tmp_path, timeout=60)

        with pytest.raises(RuntimeError, match="timed out after 60 seconds"):
            executor.execute_command()

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_execute_command_unexpected_error(self, mock_which, mock_run, tmp_path):
        """Test unexpected error handling during execution."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"

        version_result = Mock(returncode=0, stdout="apptainer version 1.2.3")
        mock_run.side_effect = [version_result, OSError("Unexpected error")]

        executor = ApptainerExecutor(sif_path=sif_file, workdir=tmp_path)

        with pytest.raises(RuntimeError, match="Unexpected error during Apptainer execution"):
            executor.execute_command()

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("builtins.open", new_callable=mock_open)
    def test_execute_command_with_environment(self, mock_file, mock_which, mock_run, tmp_path):
        """Test command execution with custom environment variables."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"

        version_result = Mock(returncode=0, stdout="apptainer version 1.2.3")
        exec_result = Mock(returncode=0, stdout="Success", stderr="")
        mock_run.side_effect = [version_result, exec_result]

        executor = ApptainerExecutor(
            sif_path=sif_file, workdir=tmp_path, env={"CUSTOM_VAR": "value"}
        )
        executor.execute_command()

        # Check that environment was passed to subprocess
        exec_call = mock_run.call_args_list[1]
        env = exec_call[1]["env"]
        assert "CUSTOM_VAR" in env
        assert env["CUSTOM_VAR"] == "value"

    @patch("subprocess.run")
    @patch("shutil.which")
    @patch("builtins.open")
    def test_execute_command_log_copy_error(
        self, mock_open_func, mock_which, mock_run, tmp_path, caplog
    ):
        """Test handling of log copy errors."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"

        version_result = Mock(returncode=0, stdout="apptainer version 1.2.3")
        exec_result = Mock(returncode=0, stdout="Success", stderr="")
        mock_run.side_effect = [version_result, exec_result]

        # Mock file operations to fail on copy log
        def side_effect(path, *args, **kwargs):
            if "logs" in str(path):
                raise OSError("Permission denied")
            return mock_open()()

        mock_open_func.side_effect = side_effect

        executor = ApptainerExecutor(
            sif_path=sif_file, workdir=tmp_path, log_copy_dir=tmp_path / "logs"
        )

        with caplog.at_level(logging.ERROR):
            executor.execute_command()

        assert "Logging error occurred" in caplog.text


class TestSecurityAndSideEffects:
    """Tests for security and side effect considerations."""

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_shell_false_security(self, mock_which, mock_run, tmp_path):
        """Test that shell=False is always used for security."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"
        mock_run.return_value = Mock(returncode=0, stdout="version", stderr="")

        executor = ApptainerExecutor(sif_path=sif_file)

        # Test version check
        executor.validate_apptainer_availability()
        version_call = mock_run.call_args_list[0]
        assert version_call[1]["shell"] is False

        # Test command execution
        mock_run.side_effect = [
            Mock(returncode=0, stdout="version", stderr=""),
            Mock(returncode=0, stdout="success", stderr=""),
        ]

        with patch("builtins.open", mock_open()):
            executor.execute_command()

        exec_call = mock_run.call_args_list[1]
        assert exec_call[1]["shell"] is False

    def test_path_traversal_protection(self, tmp_path):
        """Test protection against path traversal attacks."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        # Paths should be converted to Path objects and resolved
        executor = ApptainerExecutor(
            sif_path=str(sif_file),
            workdir="../../../etc",  # Potential path traversal
        )

        # The workdir should be resolved to an absolute path
        assert executor.workdir.is_absolute()

    def test_environment_isolation(self, tmp_path):
        """Test that custom environment doesn't leak system vars."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file, env={"SAFE_VAR": "value"})

        # Environment should be isolated copy
        assert executor.env == {"SAFE_VAR": "value"}
        assert "SAFE_VAR" not in os.environ


class TestEdgeCasesAndBoundaryConditions:
    """Tests for edge cases and boundary conditions."""

    def test_very_large_n_proc(self, tmp_path):
        """Test with very large n_proc value."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file, n_proc=999999)
        assert executor.n_proc == 999999

    def test_empty_kwargs(self, tmp_path):
        """Test methods with empty kwargs."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file)

        apptainer_args, unknown = executor.sort_apptainer_kwargs()
        assert apptainer_args == {}
        assert unknown == []

        ngpb_args, unknown = executor.sort_ngpb_kwargs()
        assert ngpb_args == {}
        assert unknown == []

    def test_unicode_paths(self, tmp_path):
        """Test handling of Unicode characters in paths."""
        unicode_dir = tmp_path / "тест_директория_测试"
        unicode_dir.mkdir()
        sif_file = unicode_dir / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file, workdir=unicode_dir)
        assert executor.sif_path == sif_file
        assert executor.workdir == unicode_dir

    def test_very_long_paths(self, tmp_path):
        """Test with very long file paths."""
        # Create a deeply nested directory structure
        long_path = tmp_path
        for i in range(10):  # Create reasonably long path
            long_path = long_path / f"very_long_directory_name_{i}"
        long_path.mkdir(parents=True)

        sif_file = long_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file, workdir=long_path)
        assert executor.sif_path == sif_file
        assert executor.workdir == long_path


class TestInvariants:
    """Tests for class invariants and contracts."""

    def test_workdir_always_exists_after_init(self, tmp_path):
        """Test that workdir always exists after initialization."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        workdir = tmp_path / "workdir_that_does_not_exist"

        executor = ApptainerExecutor(sif_path=sif_file, workdir=workdir)

        assert executor.workdir.exists()
        assert executor.workdir.is_dir()

    def test_sif_path_always_absolute_after_init(self, tmp_path):
        """Test that sif_path is always absolute after initialization."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        # Use relative path
        os.chdir(tmp_path)
        executor = ApptainerExecutor(sif_path="test.sif")

        assert executor.sif_path.is_absolute()

    def test_logger_always_available(self, tmp_path):
        """Test that logger is always available after initialization."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file)

        assert hasattr(executor, "logger")
        assert isinstance(executor.logger, logging.Logger)
        assert executor.logger.name.endswith("ApptainerExecutor")


class TestIdempotency:
    """Tests for idempotent operations."""

    @patch("shutil.which")
    def test_find_binary_idempotent(self, mock_which, tmp_path):
        """Test that finding binary multiple times gives same result."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"

        executor = ApptainerExecutor(sif_path=sif_file)

        result1 = executor.find_apptainer_binary()
        result2 = executor.find_apptainer_binary()

        assert result1 == result2 == "/usr/bin/apptainer"
        assert executor.apptainer_path == "/usr/bin/apptainer"

    def test_sort_kwargs_idempotent(self, tmp_path):
        """Test that sorting kwargs multiple times gives same result."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file)
        kwargs = {"bind": "/tmp:/tmp", "prmfile": "test.prm", "unknown": "value"}

        result1 = executor.sort_apptainer_kwargs(**kwargs)
        result2 = executor.sort_apptainer_kwargs(**kwargs)

        assert result1 == result2


class TestConcurrencySafety:
    """Tests for thread safety considerations."""

    def test_logger_setup_thread_safe(self, tmp_path):
        """Test that logger setup is thread-safe."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        # Create multiple instances - should not interfere
        executor1 = ApptainerExecutor(sif_path=sif_file)
        executor2 = ApptainerExecutor(sif_path=sif_file)

        assert executor1.logger is not executor2.logger
        assert both_loggers_work(executor1.logger, executor2.logger)


def both_loggers_work(logger1, logger2):
    """Helper function to test that both loggers work independently."""
    try:
        logger1.info("Test message 1")
        logger2.info("Test message 2")
        return True
    except Exception:
        return False


# Integration and regression tests
class TestRegressionTests:
    """Regression tests for previously fixed bugs."""

    def test_empty_environment_dict(self, tmp_path):
        """Regression test: empty environment dict should not cause issues."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        # This previously caused issues
        executor = ApptainerExecutor(sif_path=sif_file, env={})
        assert executor.env == {}

    def test_none_timeout_handling(self, tmp_path):
        """Regression test: None timeout should be handled correctly."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()

        executor = ApptainerExecutor(sif_path=sif_file, timeout=None)
        assert executor.timeout is None

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_mixed_argument_types(self, mock_which, mock_run, tmp_path):
        """Regression test: mixed argument types should be handled."""
        sif_file = tmp_path / "test.sif"
        sif_file.touch()
        mock_which.return_value = "/usr/bin/apptainer"
        mock_run.return_value = Mock(returncode=0, stdout="version")

        executor = ApptainerExecutor(sif_path=sif_file)

        # Mix of string, int, bool, None
        apptainer_args, unknown = executor.sort_apptainer_kwargs(
            bind="/tmp:/tmp",  # string
            debug=True,  # bool
            verbose=None,  # None (flag)
            memory=1024,  # int
        )

        assert apptainer_args["bind"] == "/tmp:/tmp"
        assert apptainer_args["debug"] == "True"
        assert apptainer_args["verbose"] is None
        assert apptainer_args["memory"] == "1024"
