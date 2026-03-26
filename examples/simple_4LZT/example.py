from ngpb4py import NgpbRunner

result = NgpbRunner(nproc=1).run(config={"filetype": "pdb", "filename": "4LZT.pdb"})

print(result.metrics["energy.total"])
