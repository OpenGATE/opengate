#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "G4DNAMolecularReactionTable.hh"
#include "G4VUserChemistryList.hh"

namespace py = pybind11;

// Geant4 declares these methods pure virtual but does not provide exported
// out-of-line definitions. The pybind trampoline object still needs the
// symbols at link/load time, so we provide minimal definitions here.
void G4VUserChemistryList::ConstructReactionTable(
    G4DNAMolecularReactionTable * /*reactionTable*/) {}

void G4VUserChemistryList::ConstructTimeStepModel(
    G4DNAMolecularReactionTable * /*reactionTable*/) {}

// --------------------------------------------------------------------------
// Trampoline class for Python overrides
// --------------------------------------------------------------------------
class PyG4VUserChemistryList : public G4VUserChemistryList {
public:
  using G4VUserChemistryList::G4VUserChemistryList;

  // ConstructMolecule()
  void ConstructMolecule() override {
    PYBIND11_OVERRIDE_PURE(void, G4VUserChemistryList, ConstructMolecule, );
  }

  // ConstructProcess()
  void ConstructProcess() override {
    PYBIND11_OVERRIDE(void, G4VUserChemistryList, ConstructProcess, );
  }

  // ConstructDissociationChannels()
  void ConstructDissociationChannels() override {
    PYBIND11_OVERRIDE(void, G4VUserChemistryList,
                      ConstructDissociationChannels, );
  }

  // ConstructReactionTable(G4DNAMolecularReactionTable* table)
  void ConstructReactionTable(G4DNAMolecularReactionTable *table) override {
    PYBIND11_OVERRIDE_PURE(void, G4VUserChemistryList, ConstructReactionTable,
                           table);
  }

  // ConstructTimeStepModel(G4DNAMolecularReactionTable* reactionTable)
  void
  ConstructTimeStepModel(G4DNAMolecularReactionTable *reactionTable) override {
    PYBIND11_OVERRIDE_PURE(void, G4VUserChemistryList, ConstructTimeStepModel,
                           reactionTable);
  }
};

// --------------------------------------------------------------------------
// Module definition
// --------------------------------------------------------------------------
void init_G4VUserChemistryList(py::module &m) {
  py::class_<G4DNAMolecularReactionData,
             std::unique_ptr<G4DNAMolecularReactionData, py::nodelete>>(
      m, "G4DNAMolecularReactionData")
      .def(py::init<G4double, const G4MolecularConfiguration *,
                    const G4MolecularConfiguration *>(),
           py::arg("reaction_rate"), py::arg("reactant_a"),
           py::arg("reactant_b"))
      .def("GetReactionID", &G4DNAMolecularReactionData::GetReactionID)
      .def("SetReactionType", &G4DNAMolecularReactionData::SetReactionType)
      .def("GetReactionType", &G4DNAMolecularReactionData::GetReactionType)
      .def("GetReactant1", &G4DNAMolecularReactionData::GetReactant1,
           py::return_value_policy::reference)
      .def("GetReactant2", &G4DNAMolecularReactionData::GetReactant2,
           py::return_value_policy::reference)
      .def("AddProduct",
           py::overload_cast<const G4MolecularConfiguration *>(
               &G4DNAMolecularReactionData::AddProduct),
           py::arg("product"))
      .def("GetProducts", [](G4DNAMolecularReactionData *self) {
        std::vector<const G4MolecularConfiguration *> products;
        const auto *g4_products = self->GetProducts();
        if (g4_products != nullptr) {
          products.assign(g4_products->begin(), g4_products->end());
        }
        return products;
      });

  py::class_<G4DNAMolecularReactionTable,
             std::unique_ptr<G4DNAMolecularReactionTable, py::nodelete>>(
      m, "G4DNAMolecularReactionTable")
      .def_static("GetReactionTable",
                  &G4DNAMolecularReactionTable::GetReactionTable,
                  py::return_value_policy::reference)
      .def("SetReaction",
           py::overload_cast<G4DNAMolecularReactionData *>(
               &G4DNAMolecularReactionTable::SetReaction),
           py::arg("reaction_data"));

  py::class_<G4VUserChemistryList, PyG4VUserChemistryList>(
      m, "G4VUserChemistryList")
      .def(py::init<>()) // allow Python subclassing
      .def("ConstructMolecule",
           [](G4VUserChemistryList &self) { self.ConstructMolecule(); })
      .def("ConstructProcess",
           [](G4VUserChemistryList &self) { self.ConstructProcess(); })
      .def("ConstructDissociationChannels",
           [](G4VUserChemistryList &self) {
             self.ConstructDissociationChannels();
           })
      .def("ConstructReactionTable",
           [](G4VUserChemistryList &self, G4DNAMolecularReactionTable *table) {
             self.ConstructReactionTable(table);
           })
      .def("ConstructTimeStepModel",
           [](G4VUserChemistryList &self, G4DNAMolecularReactionTable *table) {
             self.ConstructTimeStepModel(table);
           });
}
