"""Unit tests for NextGenPB output file parsers."""

# ruff: noqa: PLR2004

import tempfile
from pathlib import Path

import pytest

from ngpb4py.parsers import (
    LogParser,
    PhiNodesParser,
    PhiOnAtomsParser,
    PhiSurfParser,
)


class TestPhiSurfParser:
    """Tests for PhiSurfParser."""

    def test_parse_basic(self) -> None:
        """Test parsing basic phi_surf.txt file."""
        content = """# x     y     z     phi
1.234  2.345  3.456  -0.048
4.567  5.678  6.789  -0.047
7.890  8.901  9.012   0.023
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        try:
            parser = PhiSurfParser()
            result = parser.parse(filepath)

            assert result["num_points"] == 3
            assert len(result["coordinates"]) == 3
            assert len(result["potentials"]) == 3

            assert result["coordinates"][0] == pytest.approx([1.234, 2.345, 3.456])
            assert result["potentials"][0] == pytest.approx(-0.048)
            assert result["coordinates"][1] == pytest.approx([4.567, 5.678, 6.789])
            assert result["potentials"][1] == pytest.approx(-0.047)
            assert result["coordinates"][2] == pytest.approx([7.890, 8.901, 9.012])
            assert result["potentials"][2] == pytest.approx(0.023)
        finally:
            filepath.unlink()

    def test_parse_empty_file(self) -> None:
        """Test parsing empty file."""
        content = ""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        try:
            parser = PhiSurfParser()
            result = parser.parse(filepath)

            assert result["num_points"] == 0
            assert result["coordinates"] == []
            assert result["potentials"] == []
        finally:
            filepath.unlink()

    def test_parse_with_comments(self) -> None:
        """Test parsing file with comments."""
        content = """# This is a comment
# Another comment
1.0  2.0  3.0  0.5
# Inline comment
4.0  5.0  6.0  0.6
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        try:
            parser = PhiSurfParser()
            result = parser.parse(filepath)

            assert result["num_points"] == 2
            assert len(result["coordinates"]) == 2
        finally:
            filepath.unlink()


class TestPhiNodesParser:
    """Tests for PhiNodesParser."""

    def test_parse_basic(self) -> None:
        """Test parsing basic phi_nodes.txt file."""
        content = """10.0   6.5   9.1   0.021
10.1   6.5   9.1   0.023
10.2   6.6   9.2   0.025
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        try:
            parser = PhiNodesParser()
            result = parser.parse(filepath)

            assert result["num_nodes"] == 3
            assert len(result["coordinates"]) == 3
            assert len(result["potentials"]) == 3

            assert result["coordinates"][0] == pytest.approx([10.0, 6.5, 9.1])
            assert result["potentials"][0] == pytest.approx(0.021)
        finally:
            filepath.unlink()

    def test_parse_scientific_notation(self) -> None:
        """Test parsing file with scientific notation."""
        content = """1.23e+01  2.34e+01  3.45e+01  -4.56e-02
5.67e+00  6.78e+00  7.89e+00   8.90e-03
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        try:
            parser = PhiNodesParser()
            result = parser.parse(filepath)

            assert result["num_nodes"] == 2
            assert result["coordinates"][0] == pytest.approx([12.3, 23.4, 34.5])
            assert result["potentials"][0] == pytest.approx(-0.0456)
        finally:
            filepath.unlink()


class TestPhiOnAtomsParser:
    """Tests for PhiOnAtomsParser."""

    def test_parse_basic(self) -> None:
        """Test parsing basic phi_on_atoms.txt file."""
        content = """       1   12.400    5.800    7.300  -0.0610
       2   13.100    5.990    6.600  -0.0560
       3   14.200    6.100    7.100  -0.0520
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        try:
            parser = PhiOnAtomsParser()
            result = parser.parse(filepath)

            assert result["num_atoms"] == 3
            assert len(result["atom_indices"]) == 3
            assert len(result["coordinates"]) == 3
            assert len(result["potentials"]) == 3

            assert result["atom_indices"][0] == 1
            assert result["coordinates"][0] == pytest.approx([12.400, 5.800, 7.300])
            assert result["potentials"][0] == pytest.approx(-0.0610)

            assert result["atom_indices"][1] == 2
            assert result["atom_indices"][2] == 3
        finally:
            filepath.unlink()

    def test_parse_with_header(self) -> None:
        """Test parsing file with header."""
        content = """# Atom  x      y      z      phi
1   12.4   5.8    7.3   -0.061
2   13.1   5.99   6.6   -0.056
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        try:
            parser = PhiOnAtomsParser()
            result = parser.parse(filepath)

            assert result["num_atoms"] == 2
            assert result["atom_indices"] == [1, 2]
        finally:
            filepath.unlink()


class TestLogParser:
    """Tests for LogParser."""

    def test_parse_basic(self) -> None:
        """Test parsing basic log file."""
        content = """
========== [ System Information ] ==========
  Number of atoms    : 100
  Solute epsilon     : 2.0
  Solvent epsilon    : 80.0
  Temperature        : 298.15 [K]
  Ionic strength     : 0.145 [mol/L]
============================================

========== [ Domain Information ] ==========
  Scale:  2.5
============================================

================ [ Electrostatic Energy ] =================
  Net charge [e]:                                      1.5
  Flux charge [e]:                                     1.4998
  Polarization energy [kT]:                            45.123
  Direct ionic energy [kT]:                            12.456
  Coulombic energy [kT]:                               23.789
  Sum of electrostatic energy contributions [kT]:      81.368
===========================================================
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        try:
            parser = LogParser()
            result = parser.parse(filepath)

            assert "system_info" in result
            assert result["system_info"]["num_atoms"] == 100
            assert result["system_info"]["solute_epsilon"] == pytest.approx(2.0)
            assert result["system_info"]["solvent_epsilon"] == pytest.approx(80.0)
            assert result["system_info"]["temperature"] == pytest.approx(298.15)
            assert result["system_info"]["ionic_strength"] == pytest.approx(0.145)

            assert "domain_info" in result
            assert result["domain_info"]["scale"] == pytest.approx(2.5)

            assert "energy" in result
            assert result["energy"]["net_charge"] == pytest.approx(1.5)
            assert result["energy"]["flux_charge"] == pytest.approx(1.4998)
            assert result["energy"]["polarization_energy"] == pytest.approx(45.123)
            assert result["energy"]["ionic_energy"] == pytest.approx(12.456)
            assert result["energy"]["coulombic_energy"] == pytest.approx(23.789)
            assert result["energy"]["total_energy"] == pytest.approx(81.368)

            assert "raw_log" in result
            assert len(result["raw_log"]) > 0
        finally:
            filepath.unlink()

    def test_parse_partial_log(self) -> None:
        """Test parsing log file with partial information."""
        content = """
========== [ System Information ] ==========
  Number of atoms    : 50
  Temperature        : 300.0 [K]
============================================
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        try:
            parser = LogParser()
            result = parser.parse(filepath)

            assert result["system_info"]["num_atoms"] == 50
            assert result["system_info"]["temperature"] == pytest.approx(300.0)
            assert "solute_epsilon" not in result["system_info"]
        finally:
            filepath.unlink()

    def test_parse_empty_log(self) -> None:
        """Test parsing empty log file."""
        content = ""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            f.write(content)
            f.flush()
            filepath = Path(f.name)

        try:
            parser = LogParser()
            result = parser.parse(filepath)

            assert result["system_info"] == {}
            assert result["domain_info"] == {}
            assert result["energy"] == {}
            assert result["raw_log"] == ""
        finally:
            filepath.unlink()
