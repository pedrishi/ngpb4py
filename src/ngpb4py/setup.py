#!/usr/bin/env python3
"""Apptainer setup script entry point."""

import os
import subprocess
import sys


def main() -> int:
    """Run the Apptainer setup script.

    Returns
    -------
    int
        Exit code from the setup script.

    """
    # Get the directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    setup_script = os.path.join(script_dir, "setup.sh")

    # Ensure the setup script is executable
    if not os.access(setup_script, os.X_OK):
        os.chmod(setup_script, 0o755)

    # Run the bash script
    try:
        result = subprocess.run([setup_script], check=False)
        return result.returncode
    except FileNotFoundError:
        print(f"Error: Setup script not found at {setup_script}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error running setup script: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
