from pathlib import Path

import pytest
from examples.exercise4.exercise4 import build_config

from ngpb4py import NgpbConfig
from ngpb4py.config import packaged_default_input
from ngpb4py.io.prm import load_prm


def test_defaults_match_documented_upstream_defaults():
    config = NgpbConfig.defaults()

    assert config.data == {
        "filetype": "pqr",
        "filename": "input.pqr",
        "radius_file": "radius.siz",
        "charge_file": "charge.crg",
        "write_pqr": 0,
        "name_pqr": "output.pqr",
        "mesh_shape": 0,
        "perfil1": 0.8,
        "perfil2": 0.2,
        "scale": 2.0,
        "rand_center": 0,
        "cx_foc": 0.0,
        "cy_foc": 0.0,
        "cz_foc": 0.0,
        "n_grid": 10,
        "unilevel": 6,
        "outlevel": 1,
        "refine_box": 0,
        "outrefine_x1": -4.0,
        "outrefine_x2": 4.0,
        "outrefine_y1": -4.0,
        "outrefine_y2": 4.0,
        "outrefine_z1": -4.0,
        "outrefine_z2": 4.0,
        "linearized": 1,
        "bc_type": 1,
        "molecular_dielectric_constant": 2.0,
        "solvent_dielectric_constant": 80.0,
        "ionic_strength": 0.145,
        "T": 298.15,
        "calc_energy": 2,
        "calc_coulombic": 0,
        "atoms_write": 0,
        "map_type": "vtu",
        "potential_map": 0,
        "surf_write": 0,
        "stern_layer_surf": 0,
        "stern_layer_thickness": 2.0,
        "number_of_threads": 1,
        "linear_solver": "lis",
    }


def test_schema_records_documented_prm_blocks():
    config = NgpbConfig.defaults()

    assert config.schema["filetype"].block == "input"
    assert config.schema["scale"].block == "mesh"
    assert config.schema["bc_type"].block == "model"
    assert config.schema["surface_type"].block == "surface"
    assert config.schema["linear_solver"].block == "solver"


def test_documented_keys_without_explicit_defaults_are_supported_but_omitted_from_defaults():
    config = NgpbConfig.defaults().with_updates(
        {
            "x1": -16,
            "x2": 16,
            "y1": -16,
            "y2": 16,
            "z1": -16,
            "z2": 16,
            "surface_type": 0,
            "surface_parameter": 1.4,
            "solver_options": "-p\\ ssor\\ -i\\ cgs",
        }
    )

    for key in (
        "x1",
        "x2",
        "y1",
        "y2",
        "z1",
        "z2",
        "surface_type",
        "surface_parameter",
        "solver_options",
    ):
        assert key not in NgpbConfig.defaults().data
        assert key in config.schema

    config.validate()


def test_prm_round_trip_with_documented_defaults(tmp_path):
    config = NgpbConfig.defaults().with_updates({"potential_map": 1, "linear_solver": "mumps"})
    prm_path = tmp_path / "ngpb.prm"
    prm_path.write_text(config.to_prm())
    loaded = load_prm(str(prm_path))

    assert loaded["potential_map"] == 1
    assert loaded["linear_solver"] == "mumps"
    assert loaded["filetype"] == "pqr"


def test_to_prm_renders_documented_blocks_in_canonical_order():
    config = NgpbConfig.defaults().with_updates(
        {"surface_type": 0, "surface_parameter": 1.4, "solver_options": "-i\\ cgs"}
    )

    rendered = config.to_prm()

    assert "[input]\n" in rendered
    assert "\n[mesh]\n" in rendered
    assert "\n[model]\n" in rendered
    assert "\n[surface]\n" in rendered
    assert "\n[solver]\n" in rendered
    assert rendered.index("[input]") < rendered.index("[mesh]") < rendered.index("[model]")
    assert rendered.index("[model]") < rendered.index("[surface]") < rendered.index("[solver]")
    assert rendered.count("[../]") == 5


def test_from_prm_preserves_unknown_keys_when_rendered(tmp_path):
    prm_path = tmp_path / "custom.prm"
    prm_path.write_text("custom_key = custom_value\nfilename = molecule.pqr\neps_map = 1\n")

    config = NgpbConfig.from_prm(str(prm_path))
    rendered_path = tmp_path / "rendered.prm"
    rendered_path.write_text(config.to_prm())

    loaded = load_prm(str(rendered_path))
    assert loaded["custom_key"] == "custom_value"
    assert loaded["eps_map"] == 1
    assert loaded["filename"] == "molecule.pqr"

    rendered = rendered_path.read_text()
    assert "[input]" in rendered
    assert "custom_key = custom_value" in rendered


@pytest.mark.parametrize(
    ("updates", "expected_error"),
    [
        ({"filetype": "xyz"}, ValueError),
        ({"mesh_shape": 9}, ValueError),
        ({"bc_type": 7}, ValueError),
        ({"calc_energy": "2"}, TypeError),
        ({"surface_type": 3}, ValueError),
        ({"linear_solver": "petsc"}, ValueError),
    ],
)
def test_validate_rejects_invalid_documented_values(updates, expected_error):
    config = NgpbConfig.defaults().with_updates(updates)

    with pytest.raises(expected_error):
        config.validate()


def test_validate_accepts_int_literals_for_float_fields_loaded_from_prm(tmp_path):
    prm_path = tmp_path / "manual_box.prm"
    prm_path.write_text("x1 = -16\nx2 = 16\nsurface_parameter = 1\n")

    config = NgpbConfig.from_prm(str(prm_path))
    config.validate()


def test_from_prm_resolves_missing_relative_path_from_cwd(tmp_path, monkeypatch):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    prm_path = project_dir / "options.prm"
    prm_path.write_text("filename = molecule.pqr\n")

    monkeypatch.chdir(tmp_path)

    config = NgpbConfig.from_prm("project/options.prm")

    assert config.source_prm_path == prm_path.resolve()
    assert config.source_dir == project_dir.resolve()


def test_resolve_input_file_prefers_existing_cwd_relative_path(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    input_path = run_dir / "molecule.pqr"
    input_path.write_text("ATOM\n")

    monkeypatch.chdir(run_dir)
    config = NgpbConfig.defaults().with_updates({"filename": "molecule.pqr"})

    assert config.resolve_input_file("filename") == input_path.resolve()


def test_resolve_input_file_falls_back_to_source_prm_directory(tmp_path, monkeypatch):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    input_path = project_dir / "radius.siz"
    input_path.write_text("1.0\n")

    monkeypatch.chdir(tmp_path)
    config = NgpbConfig(data={"radius_file": "radius.siz"}, source_dir=project_dir.resolve())

    assert config.resolve_input_file("radius_file") == input_path.resolve()


def test_resolve_input_file_preserves_absolute_paths(tmp_path):
    input_path = tmp_path / "charge.crg"
    input_path.write_text("1 0.0\n")

    config = NgpbConfig.defaults().with_updates({"charge_file": str(input_path.resolve())})

    assert config.resolve_input_file("charge_file") == input_path.resolve()


def test_defaults_use_packaged_auxiliary_databases():
    config = NgpbConfig.defaults()

    assert config.uses_packaged_default_input("radius_file") is True
    assert config.uses_packaged_default_input("charge_file") is True


def test_explicit_auxiliary_database_path_disables_packaged_default():
    config = NgpbConfig.defaults().with_updates({"radius_file": "custom.siz"})

    assert config.uses_packaged_default_input("radius_file") is False


def test_packaged_default_input_exposes_packaged_resource():
    resource = packaged_default_input("radius_file")

    assert resource.name == "radius.siz"
    assert resource.is_file()
    assert "atom__res_radius_" in resource.read_text()


def test_exercise1_prm_load():
    prm_path = Path("tests/data/ex1.prm")
    loaded = load_prm(str(prm_path))

    assert loaded["filetype"] == "pqr"
    assert loaded["filename"] == "1CCM.pqr"
    assert loaded["mesh_shape"] == 0
    assert loaded["perfil1"] == 0.95
    assert loaded["perfil2"] == 0.2
    assert loaded["scale"] == 2.0
    assert loaded["bc_type"] == 1
    assert loaded["molecular_dielectric_constant"] == 2
    assert loaded["solvent_dielectric_constant"] == 80
    assert loaded["ionic_strength"] == 0.145
    assert loaded["T"] == 298.15
    assert loaded["calc_energy"] == 2
    assert loaded["calc_coulombic"] == 1


def test_exercise4_fine_mesh_prm_load():
    prm_path = Path("examples/exercise4/fine_mesh.prm")
    loaded = load_prm(str(prm_path))

    assert loaded["filetype"] == "pdb"
    assert loaded["filename"] == "1CCM.pdb"
    assert loaded["radius_file"] == "radius.siz"
    assert loaded["charge_file"] == "charge.crg"
    assert loaded["write_pqr"] == 1
    assert loaded["name_pqr"] == "1CCM_out.pqr"
    assert loaded["mesh_shape"] == 0
    assert loaded["perfil1"] == 0.95
    assert loaded["perfil2"] == 0.2
    assert loaded["scale"] == 4.0
    assert loaded["map_type"] == "vtu"
    assert loaded["potential_map"] == 1


def test_exercise4_rand_center_prm_load():
    prm_path = Path("examples/exercise4/rand_center.prm")
    loaded = load_prm(str(prm_path))

    assert loaded["filetype"] == "pdb"
    assert loaded["filename"] == "1CCM.pdb"
    assert loaded["radius_file"] == "radius.siz"
    assert loaded["charge_file"] == "charge.crg"
    assert loaded["write_pqr"] == 1
    assert loaded["name_pqr"] == "1CCM_out.pqr"
    assert loaded["mesh_shape"] == 0
    assert loaded["perfil1"] == 0.95
    assert loaded["perfil2"] == 0.2
    assert loaded["scale"] == 2.0
    assert loaded["rand_center"] == 1
    assert loaded["map_type"] == "vtu"
    assert loaded["potential_map"] == 1


def test_exercise4_focus_prm_load():
    prm_path = Path("examples/exercise4/focus.prm")
    loaded = load_prm(str(prm_path))

    assert loaded["filetype"] == "pdb"
    assert loaded["filename"] == "1CCM.pdb"
    assert loaded["radius_file"] == "radius.siz"
    assert loaded["charge_file"] == "charge.crg"
    assert loaded["write_pqr"] == 1
    assert loaded["name_pqr"] == "1CCM_out.pqr"
    assert loaded["mesh_shape"] == 3
    assert loaded["perfil1"] == 0.9
    assert loaded["perfil2"] == 0.2
    assert loaded["scale"] == 2.0
    assert loaded["cx_foc"] == 1
    assert loaded["cy_foc"] == 10
    assert loaded["cz_foc"] == 5
    assert loaded["n_grid"] == 50
    assert loaded["map_type"] == "vtu"
    assert loaded["potential_map"] == 1


def test_exercise_prm_files_validate_against_documented_schema():
    for prm_path in (
        Path("tests/data/ex1.prm"),
        Path("examples/exercise4/fine_mesh.prm"),
        Path("examples/exercise4/rand_center.prm"),
        Path("examples/exercise4/focus.prm"),
    ):
        NgpbConfig.from_prm(str(prm_path)).validate()


def test_ngpb_config_from_prm_tracks_source_metadata():
    config = NgpbConfig.from_prm("examples/exercise4/focus.prm")
    expected_dir = Path("examples/exercise4").resolve()

    assert config.source_prm_path == expected_dir / "focus.prm"
    assert config.source_dir == expected_dir


def test_ngpb_config_with_updates_preserves_source_metadata():
    config = NgpbConfig.from_prm("examples/exercise4/focus.prm").with_updates({"scale": 3.0})
    expected_dir = Path("examples/exercise4").resolve()

    assert config.source_prm_path == expected_dir / "focus.prm"
    assert config.source_dir == expected_dir
    assert config.data["scale"] == 3.0


def test_exercise4_build_config_uses_local_prm():
    config = build_config("focus")
    expected_dir = Path("examples/exercise4").resolve()

    assert config.source_prm_path == expected_dir / "focus.prm"
    assert config.source_dir == expected_dir


def test_exercise4_build_config_rejects_unknown_variant():
    try:
        build_config("bad-variant")
    except ValueError as exc:
        assert "Unknown Exercise 4 variant" in str(exc)
    else:
        raise AssertionError("build_config should reject unknown variants")
