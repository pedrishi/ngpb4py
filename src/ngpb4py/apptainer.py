"""
Apptainer execution wrapper for NextGenPB simulations.

This module provides a lightweight wrapper around Apptainer container execution
for running NextGenPB (ngpb) simulations in a containerized environment.

NGPB CLI Argument Collection:
--prmfile
--pqrfile
> run.log
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path


class ApptainerExecutor:
    """
    Lightweight module to build and execute Apptainer-based NextGenPB commands.

    This class handles argument sorting, command building, and execution management
    for running ngpb within Apptainer containers with proper error handling and logging.
    """

    APPTAINER_KNOWN_ARGS = {
        # Global options
        "build-config",
        "config",
        "debug",
        "help",
        "nocolor",
        "quiet",
        "silent",
        "verbose",
        "version",
        # exec command specific options
        "add-caps",
        "allow-setuid",
        "app",
        "apply-cgroups",
        "bind",
        "blkio-weight",
        "blkio-weight-device",
        "boot",
        "cleanenv",
        "compat",
        "contain",
        "containall",
        "cpu-shares",
        "cpus",
        "cpuset-cpus",
        "cpuset-mems",
        "device",
        "device-cgroup-rule",
        "disable-cache",
        "dns",
        "docker-login",
        "drop-caps",
        "env",
        "env-file",
        "fakeroot",
        "fusemount",
        "home",
        "hostname",
        "ipc",
        "keep-privs",
        "memory",
        "memory-reservation",
        "memory-swap",
        "mount",
        "net",
        "network",
        "network-args",
        "no-eval",
        "no-home",
        "no-https",
        "no-init",
        "no-mount",
        "no-privs",
        "no-umask",
        "nv",
        "oci",
        "overlay",
        "passwd",
        "pem-path",
        "pid",
        "pids-limit",
        "pwd",
        "rocm",
        "scratch",
        "security",
        "shell",
        "sif-fuse",
        "tmp",
        "tmpfs",
        "underlay",
        "unsquash",
        "user",
        "userns",
        "uts",
        "vm",
        "vm-cpu",
        "vm-err",
        "vm-ip",
        "vm-ram",
        "workdir",
        "writable",
        "writable-tmpfs",
    }

    NGPB_KNOWN_ARGS = {"prmfile", "pqrfile", "run_log"}

    # collecting the ngpb input parameters from the documentation:
    def __init__(
        self,
        sif_path: str | Path,
        n_proc: int = 1,
        workdir: str | Path = ".",
        env: dict[str, str] | None = None,
        timeout: int | None = None,
        log_copy_dir: str | Path | None = None,
    ):
        """
        Initialize the ApptainerExecutor.

        Parameters
        ----------
        sif_path : str or Path
            Path to the SIF file for Apptainer execution
        n_proc : int, default=1
            Number of processes for MPI execution
        workdir : str or Path, default="."
            Working directory for execution and file saving
        env : dict, optional
            Environment variables to set for Apptainer execution
        timeout : int, optional
            Timeout in seconds for the Apptainer process
        log_copy_dir : str or Path, optional
            Directory to copy log files to (in addition to workdir)
        """
        self.sif_path = Path(sif_path)
        self.n_proc = n_proc
        self.workdir = Path(workdir)
        self.env = env or {}
        self.timeout = timeout
        self.log_copy_dir = Path(log_copy_dir) if log_copy_dir else None

        self.apptainer_path: str | None = None
        self.logger = self._setup_logger()

        # Ensure workdir exists
        self.workdir.mkdir(parents=True, exist_ok=True)

        # Validate initialization parameters
        self._validate_init_params()

    def _setup_logger(self) -> logging.Logger:
        """Set up logger for the class."""
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _validate_init_params(self) -> None:
        """Validate initialization parameters."""
        if not self.sif_path.exists():
            raise FileNotFoundError(f"SIF file not found: {self.sif_path}")

        if self.n_proc <= 0:
            raise ValueError(f"n_proc must be positive, got: {self.n_proc}")

        if self.timeout is not None and self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got: {self.timeout}")

    def find_apptainer_binary(self) -> str | None:
        """
        Find the Apptainer binary in the system PATH.

        Returns
        -------
        str or None
            Path to the apptainer executable if found, None otherwise
        """
        try:
            # Use shutil.which to find apptainer in PATH
            apptainer_path = shutil.which("apptainer")
            if apptainer_path:
                self.apptainer_path = apptainer_path
                self.logger.info(f"Found apptainer at: {apptainer_path}")
                return apptainer_path

            # Also check for singularity as fallback
            singularity_path = shutil.which("singularity")
            if singularity_path:
                self.logger.warning(
                    "Apptainer not found, but found Singularity. Using Singularity as fallback."
                )
                self.apptainer_path = singularity_path
                return singularity_path

            return None

        except Exception as e:
            self.logger.error(f"Error searching for apptainer binary: {e}")
            return None

    def validate_apptainer_availability(self) -> None:
        """
        Validate that Apptainer is available and create helpful error messages.

        Raises
        ------
        RuntimeError
            If Apptainer is not available or not functional
        """
        if not self.apptainer_path:
            self.find_apptainer_binary()

        if not self.apptainer_path:
            error_msg = (
                "Apptainer not found in system PATH. "
                "Please ensure Apptainer is installed and available. "
                "You can install it using the ngpb4py-setup command or "
                "visit https://apptainer.org/docs/admin/main/installation.html"
            )
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Test if apptainer is functional
        try:
            result = subprocess.run(
                [self.apptainer_path, "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
                shell=False,
            )
            if result.returncode != 0:
                error_msg = (
                    f"Apptainer binary found at {self.apptainer_path} "
                    f"but is not functional. Exit code: {result.returncode}. "
                    f"Error: {result.stderr}"
                )
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

            self.logger.info(f"Apptainer version check successful: {result.stdout.strip()}")

        except subprocess.TimeoutExpired:
            error_msg = f"Apptainer binary at {self.apptainer_path} timed out during version check"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

        except Exception as e:
            error_msg = (
                f"Error testing Apptainer functionality: {e}. "
                "Please check your Apptainer installation."
            )
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)

    def setup_logging(
        self, log_filename: str = "apptainer_execution.log"
    ) -> tuple[Path, Path | None]:
        """
        Set up logging files for stdout/stderr capture.

        Parameters
        ----------
        log_filename : str, default="apptainer_execution.log"
            Name of the log file

        Returns
        -------
        tuple of Path
            Primary log path in workdir and optional copy path
        """
        primary_log = self.workdir / log_filename
        copy_log = None

        if self.log_copy_dir:
            self.log_copy_dir.mkdir(parents=True, exist_ok=True)
            copy_log = self.log_copy_dir / log_filename

        return primary_log, copy_log

    def create_logging_error_message(self, error: Exception, log_path: Path) -> str:
        """
        Create verbose error messages for logging-related issues.

        Parameters
        ----------
        error : Exception
            The error that occurred
        log_path : Path
            Path where logging was attempted

        Returns
        -------
        str
            Detailed error message
        """
        error_msg = (
            f"Logging error occurred: {error}. "
            f"Attempted to write to: {log_path}. "
            f"Please check directory permissions and available disk space. "
            f"Current working directory: {os.getcwd()}. "
            f"Log directory exists: {log_path.parent.exists()}. "
            f"Log directory writable: {os.access(log_path.parent, os.W_OK)}"
        )
        return error_msg

    def sort_apptainer_kwargs(self, **kwargs) -> tuple[dict[str, str | None], list[str]]:
        """
        Sort kwargs pertaining to Apptainer and prepare them for execution.

        Parameters
        ----------
        **kwargs
            Keyword arguments that may contain Apptainer options

        Returns
        -------
        tuple
            Dictionary of valid Apptainer arguments and list of unknown arguments
        """
        apptainer_args = {}
        unknown_args = []

        for key, value in kwargs.items():
            if key in self.APPTAINER_KNOWN_ARGS:
                apptainer_args[key] = str(value) if value is not None else None
            elif key.startswith("apptainer_"):
                # Handle prefixed arguments
                clean_key = key.replace("apptainer_", "")
                if clean_key in self.APPTAINER_KNOWN_ARGS:
                    apptainer_args[clean_key] = str(value) if value is not None else None
                else:
                    unknown_args.append(key)
            else:
                # This might be an ngpb argument, so we don't mark it as unknown here
                continue

        return apptainer_args, unknown_args

    def handle_apptainer_kwargs_errors(self, unknown_args: list[str]) -> None:
        """
        Handle errors related to unknown Apptainer arguments.

        Parameters
        ----------
        unknown_args : list of str
            List of unknown argument names
        """
        if unknown_args:
            warning_msg = (
                f"Unknown Apptainer arguments provided: {unknown_args}. "
                f"Known Apptainer arguments are: {sorted(self.APPTAINER_KNOWN_ARGS)}. "
                "These arguments will be ignored."
            )
            self.logger.warning(warning_msg)

    def sort_ngpb_kwargs(self, **kwargs) -> tuple[dict[str, str | None], list[str]]:
        """
        Sort kwargs pertaining to NextGenPB (ngpb) and collect options.

        Parameters
        ----------
        **kwargs
            Keyword arguments that may contain ngpb options

        Returns
        -------
        tuple
            Dictionary of valid ngpb arguments and list of unknown arguments
        """
        ngpb_args = {}
        unknown_args = []

        for key, value in kwargs.items():
            if key in self.NGPB_KNOWN_ARGS:
                ngpb_args[key] = str(value) if value is not None else None
            elif key.startswith("ngpb_"):
                # Handle prefixed arguments
                clean_key = key.replace("ngpb_", "")
                if clean_key in self.NGPB_KNOWN_ARGS:
                    ngpb_args[clean_key] = str(value) if value is not None else None
                else:
                    unknown_args.append(key)
            elif key not in self.APPTAINER_KNOWN_ARGS and not key.startswith("apptainer_"):
                # This is not a known apptainer arg, might be unknown ngpb arg
                unknown_args.append(key)

        return ngpb_args, unknown_args

    def build_command(
        self, apptainer_args: dict[str, str | None], ngpb_args: dict[str, str | None]
    ) -> list[str]:
        """
        Build the final Apptainer execution command.

        Parameters
        ----------
        apptainer_args : dict
            Dictionary of Apptainer-specific arguments
        ngpb_args : dict
            Dictionary of ngpb-specific arguments

        Returns
        -------
        list of str
            Complete command as a list of strings
        """
        if not self.apptainer_path:
            raise RuntimeError(
                "Apptainer path not found. Call validate_apptainer_availability() first."
            )

        # Start building command: apptainer exec
        cmd = [self.apptainer_path, "exec"]

        # Add default apptainer arguments
        cmd.extend(["--pwd", "/App"])
        cmd.extend(["--bind", f"{self.workdir.absolute()}:/App"])

        # Add custom apptainer arguments
        for key, value in apptainer_args.items():
            if value is None:
                cmd.append(f"--{key}")
            else:
                cmd.extend([f"--{key}", value])

        # Add SIF file
        cmd.append(str(self.sif_path.absolute()))

        # Add MPI execution
        cmd.extend(["mpirun", "-np", str(self.n_proc)])

        # Add ngpb command
        cmd.append("ngpb")

        # Add ngpb arguments
        for key, value in ngpb_args.items():
            if value is None:
                cmd.append(f"--{key}")
            else:
                cmd.extend([f"--{key}", value])

        return cmd

    def validate_all_arguments(self, **kwargs) -> None:
        """
        Validate all arguments and log warnings for unknown kwargs.

        Parameters
        ----------
        **kwargs
            All keyword arguments passed to the class
        """
        apptainer_args, unknown_apptainer = self.sort_apptainer_kwargs(**kwargs)
        ngpb_args, unknown_ngpb = self.sort_ngpb_kwargs(**kwargs)

        # Handle unknown arguments
        self.handle_apptainer_kwargs_errors(unknown_apptainer)

        if unknown_ngpb:
            # Filter out apptainer args that were already processed
            truly_unknown = [
                arg
                for arg in unknown_ngpb
                if arg not in self.APPTAINER_KNOWN_ARGS and not arg.startswith("apptainer_")
            ]

            if truly_unknown:
                warning_msg = (
                    f"Unknown arguments provided: {truly_unknown}. "
                    f"Known ngpb arguments are: {sorted(self.NGPB_KNOWN_ARGS)}. "
                    f"Known Apptainer arguments are: {sorted(self.APPTAINER_KNOWN_ARGS)}. "
                    "Unknown arguments will be ignored."
                )
                self.logger.warning(warning_msg)

                # Write warning to log file
                try:
                    log_file = self.workdir / "argument_warnings.log"
                    with open(log_file, "a") as f:
                        f.write(f"{warning_msg}\n")
                except Exception as e:
                    self.logger.error(f"Could not write argument warnings to file: {e}")

    def execute_command(self, **kwargs) -> subprocess.CompletedProcess:
        """
        Execute the Apptainer command with error capture and parallel logging.

        Parameters
        ----------
        **kwargs
            Keyword arguments for both Apptainer and ngpb

        Returns
        -------
        subprocess.CompletedProcess
            Result of the command execution

        Raises
        ------
        RuntimeError
            If execution fails or times out
        """
        # Validate apptainer availability
        self.validate_apptainer_availability()

        # Validate arguments
        self.validate_all_arguments(**kwargs)

        # Sort arguments
        apptainer_args, _ = self.sort_apptainer_kwargs(**kwargs)
        ngpb_args, _ = self.sort_ngpb_kwargs(**kwargs)

        # Build command
        cmd = self.build_command(apptainer_args, ngpb_args)

        # Set up logging
        primary_log, copy_log = self.setup_logging()

        self.logger.info(f"Executing command: {' '.join(cmd)}")

        try:
            # Prepare environment
            exec_env = os.environ.copy()
            exec_env.update(self.env)

            # Execute command
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=exec_env,
                cwd=self.workdir,
                shell=False,
            )

            # Write logs
            log_content = f"Command: {' '.join(cmd)}\n"
            log_content += f"Return code: {result.returncode}\n"
            log_content += f"STDOUT:\n{result.stdout}\n"
            log_content += f"STDERR:\n{result.stderr}\n"

            # Write to primary log
            try:
                with open(primary_log, "w") as f:
                    f.write(log_content)
            except Exception as e:
                error_msg = self.create_logging_error_message(e, primary_log)
                self.logger.error(error_msg)

            # Write to copy log if specified
            if copy_log:
                try:
                    with open(copy_log, "w") as f:
                        f.write(log_content)
                except Exception as e:
                    error_msg = self.create_logging_error_message(e, copy_log)
                    self.logger.error(error_msg)

            # Handle execution errors
            if result.returncode != 0:
                error_msg = (
                    f"Apptainer execution failed with return code {result.returncode}. "
                    f"Command: {' '.join(cmd)}. "
                    f"STDERR: {result.stderr}. "
                    f"STDOUT: {result.stdout}. "
                    f"Check log file at: {primary_log}"
                )
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)

            self.logger.info("Apptainer execution completed successfully")
            return result

        except subprocess.TimeoutExpired as e:
            error_msg = (
                f"Apptainer execution timed out after {self.timeout} seconds. "
                f"Command: {' '.join(cmd)}. "
                f"Consider increasing the timeout parameter."
            )
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e

        except Exception as e:
            error_msg = (
                f"Unexpected error during Apptainer execution: {e}. "
                f"Command: {' '.join(cmd)}. "
                f"Working directory: {self.workdir}. "
                f"SIF file: {self.sif_path}"
            )
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e
