# AMDM development LUT fixture

`AMDM_LUT.txt` is a byte-for-byte copy of the development table supplied for
the AMDM port. Its SHA-256 is
`93d42113b9f48e3ec069000f5983e4568f7bca2e873d1cb06186d08f949771ab`.

`test110_amdm_supplied_lut.py` loads this fixture relative to its own source
file, checks its checksum and schema, and compares scoring with independently
recorded transport steps. It does not need a LUT at the repository root.

This is test input data, not an expected simulation output or a production LUT
selected automatically by AMDMActor. Users supply a table appropriate to their
study and explicitly configure `LUTfilename`.
