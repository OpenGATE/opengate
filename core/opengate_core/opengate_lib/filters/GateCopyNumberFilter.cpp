/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateCopyNumberFilter.h"

#include "G4Step.hh"
#include "G4StepPoint.hh"
#include "G4TouchableHandle.hh"
#include "G4VTouchable.hh"

#include <pybind11/stl.h>

void GateCopyNumberFilter::InitializeUserInfo(py::dict &user_info) {
  // Initialize the common GateVFilter state before reading filter-specific
  // configuration.
  GateVFilter::InitializeUserInfo(user_info);

  // Reinitialization must replace, rather than append to, the previous set.
  fCopyNumbers.clear();

  if (user_info.contains("copy_numbers")) {
    try {
      auto values = user_info["copy_numbers"].cast<std::vector<int>>();
      // A set provides fast membership tests and removes duplicate values.
      for (auto v : values) {
        fCopyNumbers.insert(v);
      }
    } catch (...) {
      // Keep the filter empty when Python input cannot be converted to a list
      // of integers. By design, an empty set accepts all steps.
    }
  }
}

bool GateCopyNumberFilter::Evaluate(G4Step *step) const {
  // An empty selection means that copy-number filtering is disabled.
  if (fCopyNumbers.empty())
    return true;

  // A configured filter cannot evaluate an invalid step or touchable.
  if (!step)
    return false;

  auto *pre = step->GetPreStepPoint();
  if (!pre)
    return false;

  auto touchable = pre->GetTouchableHandle();
  if (!touchable)
    return false;

  // GetCopyNumber() without an explicit depth reads the current volume
  // (touchable history depth 0), which is the parameterised tetrahedron here.
  const int copy_no = touchable->GetCopyNumber();
  return (fCopyNumbers.count(copy_no) > 0);
}
