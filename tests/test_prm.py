from pathlib import Path

from ngpb4py import NgpbConfig
from ngpb4py.io.prm import load_prm
from examples.exercise4.exercise4 import build_inputs


def test_prm_round_trip(tmp_path):
    config = NgpbConfig.defaults().with_updates({"solver.max_iterations": 42})
    prm_path = tmp_path / "ngpb.prm"
    prm_path.write_text(config.to_prm())
    loaded = load_prm(str(prm_path))
    assert loaded["solver.max_iterations"] == 42


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


def test_exercise4_build_inputs_uses_local_paths():
    inputs = build_inputs("focus")
    expected_dir = Path("examples/exercise4").resolve()

    assert inputs.prmfile == expected_dir / "focus.prm"
    assert inputs.pqrfile is None
    assert inputs.aux_files == [
        expected_dir / "1CCM.pdb",
        expected_dir / "radius.siz",
        expected_dir / "charge.crg",
    ]


def test_exercise4_build_inputs_rejects_unknown_variant():
    try:
        build_inputs("bad-variant")
    except ValueError as exc:
        assert "Unknown Exercise 4 variant" in str(exc)
    else:
        raise AssertionError("build_inputs should reject unknown variants")
