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


# Install Apptainer unprivileged from pre-built binaries
echo "Installing Apptainer unprivileged from pre-built binaries..."
curl -s https://raw.githubusercontent.com/apptainer/apptainer/main/tools/install-unprivileged.sh | bash -s - install-dir


INSTALLED_VERSION=$(apptainer --version | awk '{print $2}')
if version_ge "$INSTALLED_VERSION" "$REQUIRED_VERSION"; then
	echo "Apptainer $INSTALLED_VERSION installed successfully."
else
	echo "Failed to install Apptainer >= $REQUIRED_VERSION." >&2
	exit 1
fi
