#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "G4VUserChemistryList.hh"
#include "G4DNAMolecularReactionTable.hh"
#include "G4DNAChemistryManager.hh"

namespace py = pybind11;

// --------------------------------------------------------------------------
// Trampoline class for Python overrides
// --------------------------------------------------------------------------
class PyG4VUserChemistryList : public G4VUserChemistryList {
public:
    using G4VUserChemistryList::G4VUserChemistryList;

    // ConstructMolecule()
    void ConstructMolecule() override {
        PYBIND11_OVERRIDE_PURE(
            void,
            G4VUserChemistryList,
            ConstructMolecule,
        );
    }

    // ConstructDissociationChannels()
    void ConstructDissociationChannels() override {
        PYBIND11_OVERRIDE(
            void,
            G4VUserChemistryList,
            ConstructDissociationChannels,
        );
    }

    // ConstructReactionTable(G4DNAMolecularReactionTable* table)
    void ConstructReactionTable(G4DNAMolecularReactionTable* table) override {
        PYBIND11_OVERRIDE(
            void,
            G4VUserChemistryList,
            ConstructReactionTable,
            table
        );
    }

    // ConstructTimeStepModel(G4DNAChemistryManager* mgr)
    void ConstructTimeStepModel(G4DNAChemistryManager* mgr) override {
        PYBIND11_OVERRIDE(
            void,
            G4VUserChemistryList,
            ConstructTimeStepModel,
            mgr
        );
    }
};

// --------------------------------------------------------------------------
// Module definition
// --------------------------------------------------------------------------
void init_G4VUserChemistryList(py::module& m)
{
    py::class_<G4VUserChemistryList, PyG4VUserChemistryList>(
        m, "G4VUserChemistryList")
        .def(py::init<>())  // allow Python subclassing

        // Virtual methods exposed for overriding
        .def("ConstructMolecule", &G4VUserChemistryList::ConstructMolecule)
        .def("ConstructDissociationChannels",
             &G4VUserChemistryList::ConstructDissociationChannels)
        .def("ConstructReactionTable",
             &G4VUserChemistryList::ConstructReactionTable)
        .def("ConstructTimeStepModel",
             &G4VUserChemistryList::ConstructTimeStepModel);
}
