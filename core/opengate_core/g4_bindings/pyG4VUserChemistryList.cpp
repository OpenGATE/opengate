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
  py::class_<G4VUserChemistryList, PyG4VUserChemistryList>(
      m, "G4VUserChemistryList")
      .def(py::init<>()); // allow Python subclassing
}
