#include "GateFilterData.h"
#include <pybind11/pybind11.h>
#include <pybind11/pytypes.h>

namespace py = pybind11;

void init_GateFilterData(py::module &m) {
  m.def("GetAttrParticleName", &GetAttr<attr::ParticleName>::get)
      .def("GetAttrPreKineticEnergy", &GetAttr<attr::PreKineticEnergy>::get);
}
