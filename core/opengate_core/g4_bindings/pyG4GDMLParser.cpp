#include <pybind11/pybind11.h>

#ifdef USE_GDML

#include "G4GDMLParser.hh"

namespace py = pybind11;

void init_G4GDMLParser(py::module &m) {
  py::class_<G4GDMLParser>(m, "G4GDMLParser")
      .def(py::init<>())

      .def(
          "Read",
          [](G4GDMLParser &parser, const G4String &filename, G4bool validate) {
            parser.Read(filename, validate);
          },
          py::arg("filename"), py::arg("validate") = true)

      .def("GetWorldVolume", &G4GDMLParser::GetWorldVolume,
           py::arg("setup_name") = "Default",
           py::return_value_policy::reference_internal)

      .def("SetStripFlag", &G4GDMLParser::SetStripFlag, py::arg("strip"))

      .def("SetOverlapCheck", &G4GDMLParser::SetOverlapCheck, py::arg("check"));
}

#endif
