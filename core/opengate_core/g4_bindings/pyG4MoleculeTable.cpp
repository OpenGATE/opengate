#include "pybind11/pybind11.h"
#include "pybind11/stl.h"

#include "G4Molecule.hh"
#include "G4MoleculeDefinition.hh"
#include "G4MoleculeTable.hh"
#include "G4SystemOfUnits.hh"

namespace py = pybind11;

void init_G4MoleculeTable(py::module &m) {
  py::class_<G4MoleculeTable, std::unique_ptr<G4MoleculeTable, py::nodelete>>(
      m, "G4MoleculeTable")
      // ----------------------------------------------------
      // Singleton accessor
      // ----------------------------------------------------
      .def_static("Instance", &G4MoleculeTable::Instance,
                  py::return_value_policy::reference,
                  "Return the global G4MoleculeTable singleton")

      // ----------------------------------------------------
      // Molecule definition lookup
      // ----------------------------------------------------
      .def(
          "GetMoleculeDefinition",
          [](G4MoleculeTable *self, const std::string &name) {
            return self->GetMoleculeDefinition(name, false);
          },
          py::arg("name"), py::return_value_policy::reference,
          "Get a molecule definition by name. Returns None if not found.")

      // ----------------------------------------------------
      // Create molecule definitions (optional, but useful)
      // ----------------------------------------------------
      .def(
          "CreateMoleculeDefinition",
          [](G4MoleculeTable *self, const std::string &name,
             double diffusionCoefficient) {
            return self->CreateMoleculeDefinition(name, diffusionCoefficient);
          },
          py::arg("name"), py::arg("diffusion_coefficient"),
          py::return_value_policy::reference,
          "Create a new molecule definition and return it")

      // ----------------------------------------------------
      // List all registered molecules
      // ----------------------------------------------------
      .def(
          "GetAllMoleculeNames",
          [](G4MoleculeTable *self) {
            std::vector<std::string> names;
            auto iterator = self->GetDefintionIterator();
            iterator.reset();
            while (iterator()) {
              names.push_back(iterator.value()->GetName());
            }
            return names;
          },
          "Return a list of all registered molecule names")

      // give a minimal repr consistent with other GATE classes
      .def("__repr__", [](const G4MoleculeTable *) {
        return "<G4MoleculeTable (singleton)>";
      });
}
