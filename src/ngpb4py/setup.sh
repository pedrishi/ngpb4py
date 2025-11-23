#!/usr/bin/env bash
# ngpb4py-setup: Installs Apptainer ≥ 1.2 if missing

set -e

REQUIRED_VERSION="1.2.0"

function version_ge() {
	# returns 0 if $1 >= $2
	[ "$1" = "$2" ] && return 0
	local IFS=.
	local i ver1=($1) ver2=($2)
	# fill empty fields in ver1 with zeros
	for ((i=${#ver1[@]}; i<${#ver2[@]}; i++)); do
		ver1[i]=0
	done
	for ((i=0; i<${#ver1[@]}; i++)); do
		if [[ -z ${ver2[i]} ]]; then
			# fill empty fields in ver2 with zeros
			ver2[i]=0
		fi
		if ((10#${ver1[i]} > 10#${ver2[i]})); then
			return 0
		fi
		if ((10#${ver1[i]} < 10#${ver2[i]})); then
			return 1
		fi
	done
	return 0
}

function main() {
	if command -v apptainer &>/dev/null; then
		INSTALLED_VERSION=$(apptainer --version | awk '{print $2}')
		if version_ge "$INSTALLED_VERSION" "$REQUIRED_VERSION"; then
			echo "Apptainer $INSTALLED_VERSION is already installed."
			exit 0
		else
			echo "Apptainer version $INSTALLED_VERSION is too old. Upgrading..."
		fi
	else
		echo "Apptainer not found. Installing..."
	fi

	# Determine installation directory
	INSTALL_DIR="${APPTAINER_INSTALL_DIR:-$HOME/.local}"
	export PATH="$INSTALL_DIR/bin:$PATH"

	# Check if apptainer is already in the install directory
	if [ -f "$INSTALL_DIR/bin/apptainer" ]; then
		INSTALLED_VERSION=$(apptainer --version | awk '{print $2}')
		if version_ge "$INSTALLED_VERSION" "$REQUIRED_VERSION"; then
			echo "Apptainer $INSTALLED_VERSION is already installed in $INSTALL_DIR."
			exit 0
		fi
	fi

	# Create installation directory if it doesn't exist
	mkdir -p "$INSTALL_DIR"

	echo "Installing Apptainer to $INSTALL_DIR..."

	# Check for required dependencies
	if ! command -v rpm2cpio &>/dev/null; then
		echo "Error: rpm2cpio is required but not found." >&2
		echo "Please install rpm2cpio using your system package manager:" >&2
		echo "  Ubuntu/Debian: apt-get install rpm2cpio" >&2
		echo "  RHEL/CentOS/Fedora: yum install rpm" >&2
		echo "  macOS: brew install rpm2cpio" >&2
		exit 1
	fi

	if ! command -v cpio &>/dev/null; then
		echo "Error: cpio is required but not found." >&2
		echo "Please install cpio using your system package manager:" >&2
		echo "  Ubuntu/Debian: apt-get install cpio" >&2
		echo "  RHEL/CentOS/Fedora: yum install cpio" >&2
		echo "  macOS: brew install cpio" >&2
		exit 1
	fi

	# Use official Apptainer unprivileged installation script
	curl -s https://raw.githubusercontent.com/apptainer/apptainer/main/tools/install-unprivileged.sh | \
		bash -s - "$INSTALL_DIR"

	INSTALLED_VERSION=$(apptainer --version | awk '{print $2}')
	if version_ge "$INSTALLED_VERSION" "$REQUIRED_VERSION"; then
		echo "Apptainer $INSTALLED_VERSION installed successfully."
	else
		echo "Failed to install Apptainer >= $REQUIRED_VERSION." >&2
		exit 1
	fi
}

# Only run main if not being sourced
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
	main
fi
