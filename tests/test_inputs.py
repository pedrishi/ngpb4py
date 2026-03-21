from ngpb4py.inputs import NgpbInputs


def test_inputs_as_args_without_pqrfile(tmp_path):
    prm_path = tmp_path / "options.prm"
    pdb_path = tmp_path / "1CCM.pdb"
    charge_path = tmp_path / "charge.crg"
    radius_path = tmp_path / "radius.siz"

    inputs = NgpbInputs(
        prmfile=prm_path,
        pqrfile=None,
        aux_files=[pdb_path, charge_path, radius_path],
    )

    assert inputs.as_args() == [
        "--prmfile",
        str(prm_path),
        str(pdb_path),
        str(charge_path),
        str(radius_path),
    ]


def test_inputs_iter_paths_without_pqrfile(tmp_path):
    prm_path = tmp_path / "options.prm"
    pdb_path = tmp_path / "1CCM.pdb"
    charge_path = tmp_path / "charge.crg"
    radius_path = tmp_path / "radius.siz"

    inputs = NgpbInputs(
        prmfile=prm_path,
        pqrfile=None,
        aux_files=[pdb_path, charge_path, radius_path],
    )

    assert list(inputs.iter_paths()) == [
        prm_path,
        pdb_path,
        charge_path,
        radius_path,
    ]
