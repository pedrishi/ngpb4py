from ngpb4py import NgpbRunner

result = NgpbRunner(nproc=1).run(
    config={
        "filetype": "pdb",
        "filename": "4LZT.pdb",
        "perfil1": 0.99,
        "perfil2": 0.8,
        "scale": 2.0,
        "mesh_shape": 3,
        "n_grid": 50,
    }
)

print(result.metrics["energy.total"])
