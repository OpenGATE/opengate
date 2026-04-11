#include "pybind11/pybind11.h"
#include "pybind11/stl.h"

#include "G4Molecule.hh"
#include "G4ElectronOccupancy.hh"
#include "G4MolecularConfiguration.hh"
#include "G4MolecularDissociationChannel.hh"
#include "G4MoleculeDefinition.hh"
#include "G4MoleculeTable.hh"
#include "G4ParticleDefinition.hh"
#include "G4SystemOfUnits.hh"

namespace py = pybind11;

void init_G4MoleculeTable(py::module &m) {
  py::class_<G4MolecularConfiguration,
             std::unique_ptr<G4MolecularConfiguration, py::nodelete>>(
      m, "G4MolecularConfiguration")
      .def("GetDefinition", &G4MolecularConfiguration::GetDefinition,
           py::return_value_policy::reference)
      .def("GetName", &G4MolecularConfiguration::GetName,
           py::return_value_policy::reference)
      .def("SetDiffusionCoefficient",
           &G4MolecularConfiguration::SetDiffusionCoefficient)
      .def("SetVanDerVaalsRadius",
           &G4MolecularConfiguration::SetVanDerVaalsRadius)
      .def("SetMass", &G4MolecularConfiguration::SetMass)
      .def("GetCharge", &G4MolecularConfiguration::GetCharge);

  py::class_<G4MolecularDissociationChannel,
             std::unique_ptr<G4MolecularDissociationChannel, py::nodelete>>(
      m, "G4MolecularDissociationChannel")
      .def(py::init<const G4String &>(), py::arg("name"))
      .def("AddProduct", &G4MolecularDissociationChannel::AddProduct,
           py::arg("product"), py::arg("displacement") = 0.)
      .def("SetEnergy", &G4MolecularDissociationChannel::SetEnergy)
      .def("SetProbability", &G4MolecularDissociationChannel::SetProbability)
      .def("SetDecayTime", &G4MolecularDissociationChannel::SetDecayTime)
      .def("GetName", &G4MolecularDissociationChannel::GetName,
           py::return_value_policy::reference);

  py::class_<G4MoleculeDefinition, G4ParticleDefinition,
             std::unique_ptr<G4MoleculeDefinition, py::nodelete>>(
      m, "G4MoleculeDefinition")
      .def("AddDecayChannel",
           py::overload_cast<const G4String &,
                             const G4MolecularDissociationChannel *>(
               &G4MoleculeDefinition::AddDecayChannel),
           py::arg("configuration_label"), py::arg("channel"))
      .def("SetDiffusionCoefficient", &G4MoleculeDefinition::SetDiffusionCoefficient)
      .def("SetVanDerVaalsRadius", &G4MoleculeDefinition::SetVanDerVaalsRadius);

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
          [](G4MoleculeTable *self, const std::string &name,
             bool must_exist) {
            return self->GetMoleculeDefinition(name, must_exist);
          },
          py::arg("name"), py::arg("must_exist") = false,
          py::return_value_policy::reference,
          "Get a molecule definition by name. Returns None if not found.")
      .def(
          "GetConfiguration",
          [](G4MoleculeTable *self, const std::string &name,
             bool must_exist) {
            return self->GetConfiguration(name, must_exist);
          },
          py::arg("name"), py::arg("must_exist") = false,
          py::return_value_policy::reference,
          "Get a molecular configuration by name. Returns None if not found.")

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
      .def(
          "CreateConfiguration",
          py::overload_cast<const G4String&, G4MoleculeDefinition*, int, double>(
              &G4MoleculeTable::CreateConfiguration),
          py::arg("user_identifier"),
          py::arg("molecule_definition"),
          py::arg("charge"),
          py::arg("diffusion_coefficient") = -1.0,
          py::return_value_policy::reference,
          "Create a molecular configuration from a molecule definition and charge.")
      .def(
          "CreateConfiguration",
          py::overload_cast<const G4String&, G4MoleculeDefinition*>(
              &G4MoleculeTable::CreateConfiguration),
          py::arg("user_identifier"),
          py::arg("molecule_definition"),
          py::return_value_policy::reference,
          "Create a molecular configuration from a molecule definition.")

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
