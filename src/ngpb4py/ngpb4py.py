"""Main NGPB class for running NextGenPB simulations."""

from pathlib import Path
from typing import Any

from ngpb4py.exceptions import ParameterError
from ngpb4py.parameters import (
    ElectrostaticsParameters,
    InputParameters,
    MeshParameters,
    OutputParameters,
    SolverParameters,
    SurfaceParameters,
)


class NGPB:
    """Pythonic wrapper for NextGenPB Poisson-Boltzmann solver.

    This class provides a simple interface to run NextGenPB simulations
    inside an Apptainer container with validated parameters.

    Parameters
    ----------
    apptainer_path : str, optional
        Path to the Apptainer executable. If not provided, searches in PATH.
    scratch_dir : str, optional
        Directory for temporary files and simulation outputs.
        If not provided, uses a default temporary directory.
    **kwargs : dict, optional
        NGPB input parameters. See Notes for available parameters.

    Notes
    -----
    Available parameter groups:

    Input Parameters:
        filetype, filename, radius_file, charge_file, write_pqr, name_pqr

    Mesh Parameters:
        mesh_shape, perfil1, perfil2, scale, rand_center, cx_foc, cy_foc,
        cz_foc, n_grid, unilevel, outlevel, x1, x2, y1, y2, z1, z2,
        refine_box, outrefine_x1, outrefine_x2, outrefine_y1, outrefine_y2,
        outrefine_z1, outrefine_z2

    Electrostatics Parameters:
        linearized, bc_type, molecular_dielectric_constant,
        solvent_dielectric_constant, ionic_strength, T, calc_energy,
        calc_coulombic

    Surface Parameters:
        surface_type, surface_parameter, stern_layer_surf,
        stern_layer_thickness, number_of_threads

    Solver Parameters:
        linear_solver, solver_options

    Output Parameters:
        atoms_write, map_type, potential_map, surf_write

    Raises
    ------
    ParameterError
        If invalid parameters are provided.

    Examples
    --------
    >>> ngpb = NGPB(apptainer_path="/usr/bin/apptainer",
    ...             scratch_dir="/tmp/ngpb",
    ...             filename="protein.pqr",
    ...             ionic_strength=0.15)
    >>> ngpb.run(run_dir="simulation_1")
    """

    def __init__(
        self,
        apptainer_path: str | None = None,
        scratch_dir: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize NGPB instance with optional parameters.

        Parameters
        ----------
        apptainer_path : str, optional
            Path to the Apptainer executable
        scratch_dir : str, optional
            Directory for temporary files and simulation outputs
        **kwargs : dict, optional
            NGPB input parameters
        """
        # Store apptainer path (immutable after init)
        self._apptainer_path = apptainer_path

        # Store scratch directory
        self._scratch_dir = scratch_dir

        # Initialize parameter dataclasses
        self._input_params = InputParameters()
        self._mesh_params = MeshParameters()
        self._electrostatics_params = ElectrostaticsParameters()
        self._surface_params = SurfaceParameters()
        self._solver_params = SolverParameters()
        self._output_params = OutputParameters()

        # Apply user-provided parameters
        if kwargs:
            self._apply_parameters(**kwargs)

    def _apply_parameters(self, **kwargs: Any) -> None:
        """Apply and validate parameter updates.

        Parameters
        ----------
        **kwargs : dict
            Parameters to update

        Raises
        ------
        ParameterError
            If invalid parameter names or values are provided
        """
        # Get all valid parameter names from dataclasses
        valid_params = set()
        param_map = {}

        for params_obj, params_class in [
            (self._input_params, InputParameters),
            (self._mesh_params, MeshParameters),
            (self._electrostatics_params, ElectrostaticsParameters),
            (self._surface_params, SurfaceParameters),
            (self._solver_params, SolverParameters),
            (self._output_params, OutputParameters),
        ]:
            for field_name in params_class.__dataclass_fields__:
                valid_params.add(field_name)
                param_map[field_name] = params_obj

        # Check for invalid parameter names
        invalid_params = set(kwargs.keys()) - valid_params
        if invalid_params:
            raise ParameterError(
                f"Invalid parameter(s): {', '.join(sorted(invalid_params))}. "
                f"Valid parameters are: {', '.join(sorted(valid_params))}"
            )

        # Apply and validate each parameter
        for param_name, param_value in kwargs.items():
            params_obj = param_map[param_name]
            self._validate_parameter(param_name, param_value, params_obj)
            setattr(params_obj, param_name, param_value)

    def _validate_parameter(
        self, param_name: str, param_value: Any, params_obj: Any
    ) -> None:
        """Validate a single parameter.

        Parameters
        ----------
        param_name : str
            Name of the parameter
        param_value : Any
            Value of the parameter
        params_obj : Any
            Parameter dataclass instance

        Raises
        ------
        ParameterError
            If parameter value is invalid
        """
        # Get expected type from dataclass field
        expected_type = params_obj.__dataclass_fields__[param_name].type

        # Type validation
        if not isinstance(param_value, expected_type):
            raise ParameterError(
                f"Parameter '{param_name}' must be of type {expected_type.__name__}, "
                f"got {type(param_value).__name__}"
            )

        # Value-specific validations
        self._validate_parameter_value(param_name, param_value)

    def _validate_parameter_value(self, param_name: str, param_value: Any) -> None:
        """Validate parameter value constraints.

        Parameters
        ----------
        param_name : str
            Name of the parameter
        param_value : Any
            Value of the parameter

        Raises
        ------
        ParameterError
            If parameter value violates constraints
        """
        # Validate categorical parameters
        self._validate_categorical_param(param_name, param_value)
        # Validate positive numeric parameters
        self._validate_positive_param(param_name, param_value)

    def _validate_categorical_param(self, param_name: str, param_value: Any) -> None:
        """Validate categorical parameter values."""
        # Filetype validation
        if param_name == "filetype" and param_value not in ("pqr", "pdb"):
            raise ParameterError(
                f"filetype must be 'pqr' or 'pdb', got '{param_value}'"
            )

        # Mesh shape validation
        if param_name == "mesh_shape" and param_value not in (0, 1, 2, 3):
            raise ParameterError(
                f"mesh_shape must be 0, 1, 2, or 3, got {param_value}"
            )

        # Binary parameter validation (0 or 1)
        binary_params = {
            "write_pqr",
            "rand_center",
            "refine_box",
            "linearized",
            "calc_coulombic",
            "stern_layer_surf",
            "atoms_write",
            "potential_map",
            "surf_write",
        }
        if param_name in binary_params and param_value not in (0, 1):
            raise ParameterError(
                f"{param_name} must be 0 or 1, got {param_value}"
            )

        # Boundary condition type validation
        if param_name == "bc_type" and param_value not in (0, 1, 2):
            raise ParameterError(
                f"bc_type must be 0, 1, or 2, got {param_value}"
            )

        # Energy calculation type validation
        if param_name == "calc_energy" and param_value not in (0, 1, 2):
            raise ParameterError(
                f"calc_energy must be 0, 1, or 2, got {param_value}"
            )

        # Surface type validation
        if param_name == "surface_type" and param_value not in (0, 1):
            raise ParameterError(
                f"surface_type must be 0 or 1, got {param_value}"
            )

        # Map type validation
        if param_name == "map_type" and param_value not in ("vtu", "vtk"):
            raise ParameterError(
                f"map_type must be 'vtu' or 'vtk', got '{param_value}'"
            )

        # Linear solver validation
        if param_name == "linear_solver" and param_value not in ("mumps", "lis"):
            raise ParameterError(
                f"linear_solver must be 'mumps' or 'lis', got '{param_value}'"
            )

    def _validate_positive_param(self, param_name: str, param_value: Any) -> None:
        """Validate positive numeric parameter values."""
        # Positive value validations
        positive_params = {
            "perfil1",
            "perfil2",
            "scale",
            "n_grid",
            "unilevel",
            "outlevel",
            "molecular_dielectric_constant",
            "solvent_dielectric_constant",
            "ionic_strength",
            "T",
            "surface_parameter",
            "stern_layer_thickness",
            "number_of_threads",
        }
        if param_name in positive_params and param_value <= 0:
            raise ParameterError(
                f"{param_name} must be positive, got {param_value}"
            )

    def run(self, run_dir: str | None = None, **kwargs: Any) -> None:
        """Run NextGenPB simulation.

        Parameters
        ----------
        run_dir : str, optional
            Directory name for this run, created inside scratch_dir.
            If not provided, a default name will be generated.
        **kwargs : dict, optional
            NGPB input parameters to update for this run.
            All parameters can be reassigned except apptainer_path.

        Raises
        ------
        ParameterError
            If invalid parameters are provided or if apptainer_path
            is attempted to be reassigned.

        Notes
        -----
        The apptainer_path cannot be changed after initialization.
        All other parameters can be updated for each run.

        Examples
        --------
        >>> ngpb = NGPB(scratch_dir="/tmp/ngpb")
        >>> ngpb.run(run_dir="run1", ionic_strength=0.15)
        >>> ngpb.run(run_dir="run2", ionic_strength=0.10)
        """
        # Check for apptainer_path in kwargs (not allowed to be reassigned)
        if "apptainer_path" in kwargs:
            raise ParameterError(
                "apptainer_path cannot be reassigned. "
                "It can only be set during initialization."
            )

        # Apply any parameter updates
        if kwargs:
            self._apply_parameters(**kwargs)

        # Prepare run directory
        if run_dir is not None:
            if self._scratch_dir is None:
                raise ParameterError(
                    "scratch_dir must be set to use run_dir parameter"
                )
            _ = Path(self._scratch_dir) / run_dir
        elif self._scratch_dir is not None:
            _ = Path(self._scratch_dir)
        else:
            _ = Path.cwd()

        # TODO: Implement actual simulation execution
        # This is a placeholder for the actual implementation
        # that will call NextGenPB via Apptainer

    @property
    def apptainer_path(self) -> str | None:
        """Get the Apptainer executable path.

        Returns
        -------
        str or None
            Path to Apptainer executable
        """
        return self._apptainer_path

    @property
    def scratch_dir(self) -> str | None:
        """Get the scratch directory path.

        Returns
        -------
        str or None
            Path to scratch directory
        """
        return self._scratch_dir
