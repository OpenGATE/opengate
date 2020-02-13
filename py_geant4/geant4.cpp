#include <pybind11/pybind11.h>

namespace py = pybind11;

void init_G4ThreeVector(py::module &);
void init_G4RunManager(py::module &);

PYBIND11_MODULE(geant4, m) {

  init_G4ThreeVector(m);
  init_G4RunManager(m);

}
