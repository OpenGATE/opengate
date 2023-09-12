/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "G4LossTableManager.hh"
#include "G4MaterialCutsCouple.hh"
#include "G4ProductionCuts.hh"
#include "G4ProductionCutsTable.hh"
#include "G4Region.hh"
#include "G4RegionStore.hh"
#include "G4Types.hh"
#include "G4VAtomDeexcitation.hh"
#include <ostream>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

py::tuple check_active_region(G4String region_name) {
  G4ProductionCutsTable *theCoupleTable =
      G4ProductionCutsTable::GetProductionCutsTable();
  G4int nCouples = (G4int)theCoupleTable->GetTableSize();

  const G4RegionStore *regionStore = G4RegionStore::GetInstance();
  const G4Region *reg = regionStore->GetRegion(region_name, false);

  G4LossTableManager *lossTableManager = G4LossTableManager::Instance();
  G4VAtomDeexcitation *atomDeexcitation = lossTableManager->AtomDeexcitation();

  if (nullptr != reg && 0 < nCouples) {
    // production cuts for this region
    const G4ProductionCuts *rpcuts = reg->GetProductionCuts();
    // loop of couples to find the correct one
    for (G4int i = 0; i < nCouples; ++i) {
      const G4MaterialCutsCouple *couple =
          theCoupleTable->GetMaterialCutsCouple(i);
      // match couple to cuts from region
      if (couple->GetProductionCuts() == rpcuts) {
        // check the flags. This needs the couple index
        G4bool deexcitationActiveRegion =
            atomDeexcitation->CheckDeexcitationActiveRegion(i);
        G4bool augerActiveRegion = atomDeexcitation->CheckAugerActiveRegion(i);
        return py::make_tuple(deexcitationActiveRegion, augerActiveRegion);
      }
    }
  }
  // return nullptr (None) if nothing reasonable was found
  return py::make_tuple(py::none(), py::none());
}

void init_GateCheckDeex(py::module &m) {

  m.def("check_active_region", check_active_region);
}
