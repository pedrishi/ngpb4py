from pathlib import Path

from ngpb4py.io.logs import parse_log
from ngpb4py.result import NgpbResult


def test_parse_log_sections():
    text = Path("tests/data/sample.log").read_text()

    parsed = parse_log(text)

    assert parsed.section_count() == 6
    assert parsed.system is not None
    assert parsed.system.parameters_file == "options.pot"
    assert parsed.system.pqr_file == "1CCM.pqr"
    assert parsed.system.number_of_atoms == 642
    assert parsed.system.protein_size_angstrom == (27.815, 34.156, 24.478)
    assert parsed.system.solute_dielectric_constant == 2
    assert parsed.system.solvent_dielectric_constant == 80
    assert parsed.system.temperature_kelvin == 298.15
    assert parsed.system.ionic_strength_mol_per_l == 0.145

    assert parsed.domain is not None
    assert parsed.domain.scale == 2
    assert parsed.domain.center_of_system_angstrom == (1.1775, 0.068, 0.07)
    assert parsed.domain.complete_domain_box is not None
    assert parsed.domain.complete_domain_box.x.minimum == -62.8225
    assert parsed.domain.uniform_grid_subdivisions is not None
    assert parsed.domain.uniform_grid_subdivisions.nx == 74
    assert parsed.domain.uniform_grid_subdivisions.ny == 88
    assert parsed.domain.uniform_grid_subdivisions.nz == 66

    assert parsed.surface is not None
    assert parsed.surface.cavity_detection_time_s == 0
    assert parsed.surface.completed is True

    assert parsed.grid is not None
    assert parsed.grid.total_nodes == 473299
    assert parsed.grid.total_quadrants == 492472
    assert parsed.grid.rank_count == 2

    assert parsed.solver is not None
    assert parsed.solver.boundary_conditions == "Null"
    assert parsed.solver.rho_calculation_time_ms == 12
    assert parsed.solver.linear_solver == "CGS"
    assert parsed.solver.preconditioner == "SSOR"
    assert parsed.solver.iteration_count == 3
    assert parsed.solver.final_status == "normal end"

    assert parsed.energies is not None
    assert parsed.energies.net_charge_e == 7.771561172376096e-16
    assert parsed.energies.flux_charge_e == 1.864835543054415e-10
    assert parsed.energies.polarization_energy_kt == -316.2410979131763
    assert parsed.energies.direct_ionic_energy_kt == -0.3089150450692983
    assert parsed.energies.coulombic_energy_kt == -10097.24155852402
    assert parsed.energies.total_electrostatic_energy_kt == -10413.79157148227


def test_parse_log_is_tolerant_of_missing_sections():
    parsed = parse_log(
        "\n".join(
            [
                "Selected parameters file: options.pot",
                "",
                "========== [ System Information ] ==========",
                "  Number of atoms    : 10",
                "============================================",
                "",
                "================ [ Electrostatic Energy ] =================",
                "  Net charge [e]: 1.0",
                "===========================================================",
            ]
        )
    )

    assert parsed.system is not None
    assert parsed.system.parameters_file == "options.pot"
    assert parsed.system.number_of_atoms == 10
    assert parsed.domain is None
    assert parsed.surface is None
    assert parsed.grid is None
    assert parsed.solver is None
    assert parsed.energies is not None
    assert parsed.energies.net_charge_e == 1.0


def test_parse_log_ignores_unknown_lines_within_sections():
    parsed = parse_log(
        "\n".join(
            [
                "========== [ Building Grid ] ==========",
                "  [Rank 0] Local nodes     : 100",
                "  something version-specific and unknown",
                "  [Global] Total quadrants : 120",
                "=======================================",
            ]
        )
    )

    assert parsed.grid is not None
    assert parsed.grid.rank_count == 1
    assert parsed.grid.total_quadrants == 120
    assert parsed.grid.total_nodes is None


def test_ngpb_result_from_logs_exposes_structured_log(tmp_path):
    stdout_path = tmp_path / "stdout.log"
    stderr_path = tmp_path / "stderr.log"
    stdout_text = Path("tests/data/sample.log").read_text()
    stdout_path.write_text(stdout_text)
    stderr_path.write_text("")

    result = NgpbResult.from_logs(
        run_id="test-run",
        scratch_dir=tmp_path,
        workdir=tmp_path,
        kept_files=True,
        command=["ngpb", "--pqrfile", "1CCM.pqr"],
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        output_paths=[],
        provenance={"backend": "test"},
    )

    assert result.log.system is not None
    assert result.log.system.number_of_atoms == 642
    assert result.log.domain is not None
    assert result.log.domain.uniform_grid_subdivisions is not None
    assert result.log.domain.uniform_grid_subdivisions.nx == 74
    assert result.log.grid is not None
    assert result.log.grid.total_nodes == 473299
    assert result.log.solver is not None
    assert result.log.solver.linear_solver == "CGS"
    assert result.log.energies is not None
    assert result.log.energies.total_electrostatic_energy_kt == -10413.79157148227
    assert result.metrics["mesh.elements"] == 492472
    assert result.metrics["solver.iterations"] == 3


def test_ngpb_result_parses_known_output_files(tmp_path):
    stdout_path = tmp_path / "stdout.log"
    stderr_path = tmp_path / "stderr.log"
    stdout_path.write_text("")
    stderr_path.write_text("")

    phi_surf_path = tmp_path / "phi_surf.txt"
    phi_surf_path.write_text("0.0 1.0 2.0 3.0\n1.5 2.5 3.5 4.5\n")
    phi_nodes_path = tmp_path / "phi_nodes.txt"
    phi_nodes_path.write_text("header row\n4.0 5.0 6.0 7.0\n\n8.0 9.0 10.0 11.0\n")
    ignored_path = tmp_path / "other.txt"
    ignored_path.write_text("7.0 8.0 9.0 10.0\n")

    result = NgpbResult.from_logs(
        run_id="test-run",
        scratch_dir=tmp_path,
        workdir=tmp_path,
        kept_files=True,
        command=["ngpb"],
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        output_paths=[phi_surf_path, phi_nodes_path, ignored_path],
        provenance={"backend": "test"},
    )

    assert result.parsed_outputs["phi_surf.txt"].coordinates == [[0.0, 1.0, 2.0], [1.5, 2.5, 3.5]]
    assert result.parsed_outputs["phi_surf.txt"].potentials == [3.0, 4.5]
    assert result.parsed_outputs["phi_nodes.txt"].coordinates == [[4.0, 5.0, 6.0], [8.0, 9.0, 10.0]]
    assert result.parsed_outputs["phi_nodes.txt"].potentials == [7.0, 11.0]
    assert "other.txt" not in result.parsed_outputs
