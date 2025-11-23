"""Parameter dataclasses for NGPB configuration."""

from dataclasses import dataclass


@dataclass
class InputParameters:
    """Molecular input settings.

    Parameters
    ----------
    filetype : str, optional
        Structure file type ('pqr' or 'pdb'), by default 'pqr'
    filename : str, optional
        Path to the structure file, by default 'input.pqr'
    radius_file : str, optional
        Radius file path (used only if filetype = pdb), by default 'radius.siz'
    charge_file : str, optional
        Charge file path (used only if filetype = pdb), by default 'charge.crg'
    write_pqr : int, optional
        Whether to write a processed .pqr file (0 or 1), by default 0
    name_pqr : str, optional
        Name of the output .pqr file, by default 'output.pqr'
    """

    filetype: str = "pqr"
    filename: str = "input.pqr"
    radius_file: str = "radius.siz"
    charge_file: str = "charge.crg"
    write_pqr: int = 0
    name_pqr: str = "output.pqr"


@dataclass
class MeshParameters:
    """Mesh generation settings.

    Parameters
    ----------
    mesh_shape : int, optional
        Mesh shape configuration (0=derefined, 1=uniform, 2=manual box, 3=focused),
        by default 0
    perfil1 : float, optional
        Ratio between molecular size and grid spacing in core region, by default 0.8
    perfil2 : float, optional
        Ratio for outer region mesh spacing, by default 0.2
    scale : float, optional
        Inverse of grid size in core region, by default 2.0
    rand_center : int, optional
        If 1, randomly shifts the center of the domain box, by default 0
    cx_foc : float, optional
        X coordinate of focused region center (for mesh_shape=3), by default 0.0
    cy_foc : float, optional
        Y coordinate of focused region center (for mesh_shape=3), by default 0.0
    cz_foc : float, optional
        Z coordinate of focused region center (for mesh_shape=3), by default 0.0
    n_grid : int, optional
        Number of grid intervals in the focused zone (for mesh_shape=3), by default 10
    unilevel : int, optional
        Uniform refinement level (for mesh_shape=1 or 2), by default 6
    outlevel : int, optional
        Minimum refinement level outside the refine box (for mesh_shape=1 or 2),
        by default 1
    x1 : float, optional
        X lower bound of manual bounding box (for mesh_shape=2), by default -16.0
    x2 : float, optional
        X upper bound of manual bounding box (for mesh_shape=2), by default 16.0
    y1 : float, optional
        Y lower bound of manual bounding box (for mesh_shape=2), by default -16.0
    y2 : float, optional
        Y upper bound of manual bounding box (for mesh_shape=2), by default 16.0
    z1 : float, optional
        Z lower bound of manual bounding box (for mesh_shape=2), by default -16.0
    z2 : float, optional
        Z upper bound of manual bounding box (for mesh_shape=2), by default 16.0
    refine_box : int, optional
        Enable box refinement (0 or 1), by default 0
    outrefine_x1 : float, optional
        X lower bound of refinement box, by default -4.0
    outrefine_x2 : float, optional
        X upper bound of refinement box, by default 4.0
    outrefine_y1 : float, optional
        Y lower bound of refinement box, by default -4.0
    outrefine_y2 : float, optional
        Y upper bound of refinement box, by default 4.0
    outrefine_z1 : float, optional
        Z lower bound of refinement box, by default -4.0
    outrefine_z2 : float, optional
        Z upper bound of refinement box, by default 4.0
    """

    mesh_shape: int = 0
    perfil1: float = 0.8
    perfil2: float = 0.2
    scale: float = 2.0
    rand_center: int = 0
    cx_foc: float = 0.0
    cy_foc: float = 0.0
    cz_foc: float = 0.0
    n_grid: int = 10
    unilevel: int = 6
    outlevel: int = 1
    x1: float = -16.0
    x2: float = 16.0
    y1: float = -16.0
    y2: float = 16.0
    z1: float = -16.0
    z2: float = 16.0
    refine_box: int = 0
    outrefine_x1: float = -4.0
    outrefine_x2: float = 4.0
    outrefine_y1: float = -4.0
    outrefine_y2: float = 4.0
    outrefine_z1: float = -4.0
    outrefine_z2: float = 4.0


@dataclass
class ElectrostaticsParameters:
    """Electrostatics model settings.

    Parameters
    ----------
    linearized : int, optional
        Enable linearized PBE (1=yes, currently mandatory), by default 1
    bc_type : int, optional
        Boundary condition type (0=Neumann, 1=Dirichlet, 2=Coulombic), by default 1
    molecular_dielectric_constant : float, optional
        Dielectric constant inside the molecule, by default 2.0
    solvent_dielectric_constant : float, optional
        Dielectric constant of the solvent, by default 80.0
    ionic_strength : float, optional
        Concentration of ions in the solvent (mol/L), by default 0.145
    T : float, optional
        Temperature of the system (Kelvin), by default 298.15
    calc_energy : int, optional
        Energy calculation type (0=none, 1=polarization, 2=polarization+ionic),
        by default 2
    calc_coulombic : int, optional
        Whether to compute Coulombic energy (0 or 1), by default 0
    """

    linearized: int = 1
    bc_type: int = 1
    molecular_dielectric_constant: float = 2.0
    solvent_dielectric_constant: float = 80.0
    ionic_strength: float = 0.145
    T: float = 298.15
    calc_energy: int = 2
    calc_coulombic: int = 0


@dataclass
class SurfaceParameters:
    """Surface definition settings.

    Parameters
    ----------
    surface_type : int, optional
        Surface type (0=SES, 1=Skin), by default 0
    surface_parameter : float, optional
        Probe radius for SES or smoothness for Skin, by default 1.4
    stern_layer_surf : int, optional
        Enable Stern layer (0 or 1), by default 0
    stern_layer_thickness : float, optional
        Thickness of the Stern layer in Angstroms, by default 2.0
    number_of_threads : int, optional
        Number of CPU threads used by NanoShaper, by default 1
    """

    surface_type: int = 0
    surface_parameter: float = 1.4
    stern_layer_surf: int = 0
    stern_layer_thickness: float = 2.0
    number_of_threads: int = 1


@dataclass
class SolverParameters:
    """Solver and algorithm settings.

    Parameters
    ----------
    linear_solver : str, optional
        Linear solver backend ('mumps' or 'lis'), by default 'lis'
    solver_options : str, optional
        Additional solver options string (for lis solver), by default
        '-p ssor -ssor_omega 0.51 -i cgs -tol 1.e-6 -print 2 -conv_cond 2 -tol_w 0'
    """

    linear_solver: str = "lis"
    solver_options: str = (
        "-p ssor -ssor_omega 0.51 -i cgs -tol 1.e-6 -print 2 -conv_cond 2 -tol_w 0"
    )


@dataclass
class OutputParameters:
    """Output options settings.

    Parameters
    ----------
    atoms_write : int, optional
        Write electrostatic potential at atomic positions (0 or 1), by default 0
    map_type : str, optional
        File format for exporting potential maps ('vtu' or 'vtk'), by default 'vtu'
    potential_map : int, optional
        Export a 3D potential map (0 or 1), by default 0
    surf_write : int, optional
        Export potential on the molecular surface (0 or 1), by default 0
    """

    atoms_write: int = 0
    map_type: str = "vtu"
    potential_map: int = 0
    surf_write: int = 0
