"""Entry point for ngpb4py-setup: runs setup.sh to install Apptainer if needed."""

import os
import subprocess
import sys


def main():
    """Run the setup.sh script to install Apptainer if missing."""
    script_path = os.path.join(os.path.dirname(__file__), "setup.sh")
    if not os.path.exists(script_path):
        print(f"setup.sh not found at {script_path}", file=sys.stderr)
        sys.exit(1)
    try:
        subprocess.run(["bash", script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running setup.sh: {e}", file=sys.stderr)
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
