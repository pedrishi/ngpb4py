"""Unit tests for NGPB class and parameter validation."""

import pytest

from ngpb4py import NGPB, ParameterError
from ngpb4py.parameters import (
    ElectrostaticsParameters,
    InputParameters,
    MeshParameters,
    OutputParameters,
    SolverParameters,
    SurfaceParameters,
)


class TestNGPBInitialization:
    """Test NGPB class initialization."""

    def test_init_no_params(self):
        """Test initialization with no parameters."""
        ngpb = NGPB()
        assert ngpb.apptainer_path is None
        assert ngpb.scratch_dir is None

    def test_init_with_apptainer_path(self):
        """Test initialization with apptainer_path."""
        ngpb = NGPB(apptainer_path="/usr/bin/apptainer")
        assert ngpb.apptainer_path == "/usr/bin/apptainer"

    def test_init_with_scratch_dir(self):
        """Test initialization with scratch_dir."""
        ngpb = NGPB(scratch_dir="/tmp/ngpb")
        assert ngpb.scratch_dir == "/tmp/ngpb"

    def test_init_with_valid_ngpb_params(self):
        """Test initialization with valid NGPB parameters."""
        ngpb = NGPB(
            filename="protein.pqr",
            ionic_strength=0.15,
            mesh_shape=1,
            calc_energy=2,
        )
        assert ngpb._input_params.filename == "protein.pqr"
        assert ngpb._electrostatics_params.ionic_strength == 0.15
        assert ngpb._mesh_params.mesh_shape == 1
        assert ngpb._electrostatics_params.calc_energy == 2

    def test_init_with_invalid_param_name(self):
        """Test initialization with invalid parameter name."""
        with pytest.raises(ParameterError, match="Invalid parameter"):
            NGPB(invalid_param="value")

    def test_init_with_invalid_param_type(self):
        """Test initialization with invalid parameter type."""
        with pytest.raises(ParameterError, match="must be of type"):
            NGPB(mesh_shape="invalid")


class TestParameterValidation:
    """Test parameter validation."""

    def test_filetype_validation(self):
        """Test filetype parameter validation."""
        NGPB(filetype="pqr")
        NGPB(filetype="pdb")
        with pytest.raises(ParameterError, match="filetype must be"):
            NGPB(filetype="invalid")

    def test_mesh_shape_validation(self):
        """Test mesh_shape parameter validation."""
        for valid_value in [0, 1, 2, 3]:
            NGPB(mesh_shape=valid_value)
        with pytest.raises(ParameterError, match="mesh_shape must be"):
            NGPB(mesh_shape=4)

    def test_binary_params_validation(self):
        """Test binary parameter (0 or 1) validation."""
        binary_params = [
            "write_pqr",
            "rand_center",
            "refine_box",
            "linearized",
            "calc_coulombic",
            "stern_layer_surf",
            "atoms_write",
            "potential_map",
            "surf_write",
        ]
        for param in binary_params:
            NGPB(**{param: 0})
            NGPB(**{param: 1})
            with pytest.raises(ParameterError, match=f"{param} must be 0 or 1"):
                NGPB(**{param: 2})

    def test_bc_type_validation(self):
        """Test boundary condition type validation."""
        for valid_value in [0, 1, 2]:
            NGPB(bc_type=valid_value)
        with pytest.raises(ParameterError, match="bc_type must be"):
            NGPB(bc_type=3)

    def test_calc_energy_validation(self):
        """Test energy calculation type validation."""
        for valid_value in [0, 1, 2]:
            NGPB(calc_energy=valid_value)
        with pytest.raises(ParameterError, match="calc_energy must be"):
            NGPB(calc_energy=3)

    def test_surface_type_validation(self):
        """Test surface type validation."""
        NGPB(surface_type=0)
        NGPB(surface_type=1)
        with pytest.raises(ParameterError, match="surface_type must be"):
            NGPB(surface_type=2)

    def test_map_type_validation(self):
        """Test map type validation."""
        NGPB(map_type="vtu")
        NGPB(map_type="vtk")
        with pytest.raises(ParameterError, match="map_type must be"):
            NGPB(map_type="invalid")

    def test_linear_solver_validation(self):
        """Test linear solver validation."""
        NGPB(linear_solver="mumps")
        NGPB(linear_solver="lis")
        with pytest.raises(ParameterError, match="linear_solver must be"):
            NGPB(linear_solver="invalid")

    def test_positive_params_validation(self):
        """Test positive parameter validation."""
        positive_params = [
            "perfil1",
            "perfil2",
            "scale",
            "molecular_dielectric_constant",
            "solvent_dielectric_constant",
            "ionic_strength",
            "T",
            "surface_parameter",
            "stern_layer_thickness",
        ]
        for param in positive_params:
            NGPB(**{param: 1.0})
            with pytest.raises(ParameterError, match=f"{param} must be positive"):
                NGPB(**{param: 0.0})
            with pytest.raises(ParameterError, match=f"{param} must be positive"):
                NGPB(**{param: -1.0})

    def test_positive_int_params_validation(self):
        """Test positive integer parameter validation."""
        positive_int_params = [
            "n_grid",
            "unilevel",
            "outlevel",
            "number_of_threads",
        ]
        for param in positive_int_params:
            NGPB(**{param: 1})
            with pytest.raises(ParameterError, match=f"{param} must be positive"):
                NGPB(**{param: 0})
            with pytest.raises(ParameterError, match=f"{param} must be positive"):
                NGPB(**{param: -1})


class TestNGPBRun:
    """Test NGPB run method."""

    def test_run_no_params(self):
        """Test run with no parameters."""
        ngpb = NGPB()
        ngpb.run()

    def test_run_with_run_dir(self):
        """Test run with run_dir parameter."""
        ngpb = NGPB(scratch_dir="/tmp/ngpb")
        ngpb.run(run_dir="simulation_1")

    def test_run_with_run_dir_no_scratch_dir(self):
        """Test run with run_dir but no scratch_dir raises error."""
        ngpb = NGPB()
        with pytest.raises(ParameterError, match="scratch_dir must be set"):
            ngpb.run(run_dir="simulation_1")

    def test_run_with_param_updates(self):
        """Test run with parameter updates."""
        ngpb = NGPB(ionic_strength=0.145)
        ngpb.run(ionic_strength=0.15)
        assert ngpb._electrostatics_params.ionic_strength == 0.15

    def test_run_cannot_update_apptainer_path(self):
        """Test that apptainer_path cannot be updated in run."""
        ngpb = NGPB(apptainer_path="/usr/bin/apptainer")
        with pytest.raises(ParameterError, match="apptainer_path cannot be reassigned"):
            ngpb.run(apptainer_path="/other/path")

    def test_run_with_invalid_param(self):
        """Test run with invalid parameter."""
        ngpb = NGPB()
        with pytest.raises(ParameterError, match="Invalid parameter"):
            ngpb.run(invalid_param="value")

    def test_run_preserves_apptainer_path(self):
        """Test that apptainer_path is preserved across runs."""
        ngpb = NGPB(apptainer_path="/usr/bin/apptainer", scratch_dir="/tmp/ngpb")
        ngpb.run(run_dir="run1", ionic_strength=0.15)
        ngpb.run(run_dir="run2", ionic_strength=0.10)
        assert ngpb.apptainer_path == "/usr/bin/apptainer"


class TestParameterDataclasses:
    """Test parameter dataclass defaults."""

    def test_input_parameters_defaults(self):
        """Test InputParameters default values."""
        params = InputParameters()
        assert params.filetype == "pqr"
        assert params.filename == "input.pqr"
        assert params.radius_file == "radius.siz"
        assert params.charge_file == "charge.crg"
        assert params.write_pqr == 0
        assert params.name_pqr == "output.pqr"

    def test_mesh_parameters_defaults(self):
        """Test MeshParameters default values."""
        params = MeshParameters()
        assert params.mesh_shape == 0
        assert params.perfil1 == 0.8
        assert params.perfil2 == 0.2
        assert params.scale == 2.0
        assert params.rand_center == 0
        assert params.refine_box == 0

    def test_electrostatics_parameters_defaults(self):
        """Test ElectrostaticsParameters default values."""
        params = ElectrostaticsParameters()
        assert params.linearized == 1
        assert params.bc_type == 1
        assert params.molecular_dielectric_constant == 2.0
        assert params.solvent_dielectric_constant == 80.0
        assert params.ionic_strength == 0.145
        assert params.T == 298.15
        assert params.calc_energy == 2
        assert params.calc_coulombic == 0

    def test_surface_parameters_defaults(self):
        """Test SurfaceParameters default values."""
        params = SurfaceParameters()
        assert params.surface_type == 0
        assert params.surface_parameter == 1.4
        assert params.stern_layer_surf == 0
        assert params.stern_layer_thickness == 2.0
        assert params.number_of_threads == 1

    def test_solver_parameters_defaults(self):
        """Test SolverParameters default values."""
        params = SolverParameters()
        assert params.linear_solver == "lis"
        assert isinstance(params.solver_options, str)

    def test_output_parameters_defaults(self):
        """Test OutputParameters default values."""
        params = OutputParameters()
        assert params.atoms_write == 0
        assert params.map_type == "vtu"
        assert params.potential_map == 0
        assert params.surf_write == 0


class TestNGPBAPI:
    """Test NGPB API importability."""

    def test_ngpb_importable(self):
        """Test that NGPB is importable from ngpb4py."""
        from ngpb4py import NGPB

        assert NGPB is not None

    def test_parameter_error_importable(self):
        """Test that ParameterError is importable from ngpb4py."""
        from ngpb4py import ParameterError

        assert ParameterError is not None

    def test_parameter_classes_importable(self):
        """Test that parameter classes are importable from ngpb4py."""
        from ngpb4py import (
            ElectrostaticsParameters,
            InputParameters,
            MeshParameters,
            OutputParameters,
            SolverParameters,
            SurfaceParameters,
        )

        assert InputParameters is not None
        assert MeshParameters is not None
        assert ElectrostaticsParameters is not None
        assert SurfaceParameters is not None
        assert SolverParameters is not None
        assert OutputParameters is not None
