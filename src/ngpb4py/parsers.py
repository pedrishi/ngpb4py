"""Parsers for NextGenPB output files."""

from pathlib import Path
from typing import Any


class PhiSurfParser:
    """Parser for phi_surf.txt - potential values on the molecular surface."""

    _MIN_PARTS = 4  # x, y, z, phi

    def parse(self, filepath: str | Path) -> dict[str, Any]:
        """
        Parse phi_surf.txt file containing potential values on the molecular surface.

        Parameters
        ----------
        filepath : str | Path
            Path to the phi_surf.txt file

        Returns
        -------
        dict[str, Any]
            Dictionary containing:
            - 'coordinates': list of [x, y, z] coordinates
            - 'potentials': list of potential values
            - 'num_points': number of surface points
        """
        filepath = Path(filepath)
        coordinates = []
        potentials = []

        with filepath.open(encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                if len(parts) >= self._MIN_PARTS:
                    x, y, z, phi = map(float, parts[: self._MIN_PARTS])
                    coordinates.append([x, y, z])
                    potentials.append(phi)

        return {
            "coordinates": coordinates,
            "potentials": potentials,
            "num_points": len(coordinates),
        }


class PhiNodesParser:
    """Parser for phi_nodes.txt - potential values at molecular surface boundary nodes."""

    _MIN_PARTS = 4  # x, y, z, phi

    def parse(self, filepath: str | Path) -> dict[str, Any]:
        """
        Parse phi_nodes.txt file containing potential values at boundary nodes.

        Parameters
        ----------
        filepath : str | Path
            Path to the phi_nodes.txt file

        Returns
        -------
        dict[str, Any]
            Dictionary containing:
            - 'coordinates': list of [x, y, z] coordinates
            - 'potentials': list of potential values
            - 'num_nodes': number of boundary nodes
        """
        filepath = Path(filepath)
        coordinates = []
        potentials = []

        with filepath.open(encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                if len(parts) >= self._MIN_PARTS:
                    x, y, z, phi = map(float, parts[: self._MIN_PARTS])
                    coordinates.append([x, y, z])
                    potentials.append(phi)

        return {
            "coordinates": coordinates,
            "potentials": potentials,
            "num_nodes": len(coordinates),
        }


class PhiOnAtomsParser:
    """Parser for phi_on_atoms.txt - potential values at atomic positions."""

    _MIN_PARTS = 5  # index, x, y, z, phi

    def parse(self, filepath: str | Path) -> dict[str, Any]:
        """
        Parse phi_on_atoms.txt file containing potential values at atomic positions.

        Parameters
        ----------
        filepath : str | Path
            Path to the phi_on_atoms.txt file

        Returns
        -------
        dict[str, Any]
            Dictionary containing:
            - 'atom_indices': list of atom indices
            - 'coordinates': list of [x, y, z] coordinates
            - 'potentials': list of potential values
            - 'num_atoms': number of atoms
        """
        filepath = Path(filepath)
        atom_indices = []
        coordinates = []
        potentials = []

        with filepath.open(encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                parts = line.split()
                if len(parts) >= self._MIN_PARTS:
                    idx = int(parts[0])
                    # Extract x, y, z, phi from parts[1:5] (indices 1, 2, 3, 4)
                    x, y, z, phi = map(float, parts[1:5])
                    atom_indices.append(idx)
                    coordinates.append([x, y, z])
                    potentials.append(phi)

        return {
            "atom_indices": atom_indices,
            "coordinates": coordinates,
            "potentials": potentials,
            "num_atoms": len(atom_indices),
        }


class LogParser:
    """Parser for NextGenPB output log files."""

    # Expected number of parts when splitting by colon
    _EXPECTED_PARTS = 2

    def parse(self, filepath: str | Path) -> dict[str, Any]:
        """
        Parse NextGenPB output log file.

        Parameters
        ----------
        filepath : str | Path
            Path to the log file

        Returns
        -------
        dict[str, Any]
            Dictionary containing extracted information from the log:
            - 'system_info': dict with system information (atoms, size, etc.)
            - 'domain_info': dict with domain information (scale, box size, etc.)
            - 'energy': dict with energy values
            - 'raw_log': full log text
        """
        filepath = Path(filepath)
        log_text = filepath.read_text(encoding="utf-8")

        result = {
            "system_info": {},
            "domain_info": {},
            "energy": {},
            "raw_log": log_text,
        }

        lines = log_text.split("\n")

        for raw_line in lines:
            line = raw_line.strip()
            self._parse_system_info(line, result)
            self._parse_domain_info(line, result)
            self._parse_energy_info(line, result)

        return result

    def _parse_system_info(self, line: str, result: dict[str, Any]) -> None:
        """Parse system information from a log line."""
        system_fields = {
            "Number of atoms": ("num_atoms", int),
            "Solute epsilon": ("solute_epsilon", float),
            "Solvent epsilon": ("solvent_epsilon", float),
        }

        for key, (field_name, converter) in system_fields.items():
            if key in line:
                self._extract_value(line, result["system_info"], field_name, converter)
                return

        if "Temperature" in line and "[K]" in line:
            parts = line.split(":")
            if len(parts) == self._EXPECTED_PARTS:
                temp_str = parts[1].replace("[K]", "").strip()
                result["system_info"]["temperature"] = float(temp_str)
        elif "Ionic strength" in line and "[mol/L]" in line:
            parts = line.split(":")
            if len(parts) == self._EXPECTED_PARTS:
                ionic_str = parts[1].replace("[mol/L]", "").strip()
                result["system_info"]["ionic_strength"] = float(ionic_str)

    def _parse_domain_info(self, line: str, result: dict[str, Any]) -> None:
        """Parse domain information from a log line."""
        if "Scale:" in line:
            self._extract_value(line, result["domain_info"], "scale", float)

    def _parse_energy_info(self, line: str, result: dict[str, Any]) -> None:
        """Parse energy information from a log line."""
        energy_fields = {
            "Net charge [e]:": ("net_charge", float),
            "Flux charge [e]:": ("flux_charge", float),
            "Polarization energy [kT]:": ("polarization_energy", float),
            "Direct ionic energy [kT]:": ("ionic_energy", float),
            "Coulombic energy [kT]:": ("coulombic_energy", float),
            "Sum of electrostatic energy contributions [kT]:": ("total_energy", float),
        }

        for key, (field_name, converter) in energy_fields.items():
            if key in line:
                self._extract_value(line, result["energy"], field_name, converter)
                return

    def _extract_value(self, line: str, target: dict, field_name: str, converter: type) -> None:
        """Extract and convert a value from a colon-separated line."""
        parts = line.split(":")
        if len(parts) == self._EXPECTED_PARTS:
            target[field_name] = converter(parts[1].strip())
