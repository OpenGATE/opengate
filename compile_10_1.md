# Compile Notes For MRCP Port On OpenGATE 10.1.0

Date: 2026-05-19

Work directory:

```bash
cd /Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build
```

Successful configure command, adapted from the Gate-10.0.3 setup:

```bash
/Applications/CMake-4.2.3.app/Contents/bin/cmake \
  -DGeant4_DIR="/Users/yhuh/Study/installation/geant/geant4114/build" \
  -DOPENGATE_USE_ITK=ON \
  -DITK_DIR="/Users/yhuh/Study/installation/gate/Forgate10_tet/opengate/itk/ITK/build" \
  -DPython_EXECUTABLE="/opt/anaconda3/envs/tetGatev2/bin/python" \
  -DPython3_EXECUTABLE="/opt/anaconda3/envs/tetGatev2/bin/python" \
  -DPython_ROOT_DIR="/opt/anaconda3/envs/tetGatev2" \
  -DPython3_ROOT_DIR="/opt/anaconda3/envs/tetGatev2" \
  -DPython_INCLUDE_DIR="/opt/anaconda3/envs/tetGatev2/include/python3.12" \
  -DPython_LIBRARY="/opt/anaconda3/envs/tetGatev2/lib/libpython3.12.dylib" \
  -DCMAKE_PREFIX_PATH="/opt/anaconda3/envs/tetGatev2;/opt/homebrew/opt/fftw;/opt/homebrew" \
  -DOPENGATE_USE_VISU=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_SHARED_LINKER_FLAGS="-L/opt/homebrew/opt/fftw/lib" \
  ..
```

Recommended build command:

```bash
env LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  /Applications/CMake-4.2.3.app/Contents/bin/cmake --build . --config Release -j4
```

After build, check the new filter binding:

```bash
python -c "import opengate_core as g4; print(hasattr(g4, 'GateCopyNumberFilter'))"
```

Expected output:

```text
True
```

Actual binding check passed:

```text
GateCopyNumberFilter True True
G4Tet True
build_tet_mesh_g4tet True
```

Example build-mode check:

```bash
env PYTHONPATH=/Users/yhuh/Study/installation/gate/Gate-10.1/opengate/core/build:/Users/yhuh/Study/installation/gate/Gate-10.1/opengate \
  DYLD_LIBRARY_PATH=/opt/homebrew/opt/fftw/lib:/opt/homebrew/lib \
  /opt/anaconda3/envs/tetGatev2/bin/python \
  ./only_heart_ct_260320_v7_v14_20260429.py --mode build
```

Result:

```text
tet mesh ready: total tetrahedra=8582677, selected scoring tetrahedra=48012
engine initialize = 25.01 s
```
