/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateCopyNumberFilter_h
#define GateCopyNumberFilter_h

#include "GateVFilter.h"

#include <set>
#include <vector>

/**
 * Filter Geant4 steps by the copy number of the pre-step touchable at depth 0.
 *
 * The accepted copy numbers are supplied through the Python user-info field
 * "copy_numbers". An empty set disables copy-number filtering and accepts all
 * valid steps.
 */
class GateCopyNumberFilter : public GateVFilter {
public:
  GateCopyNumberFilter() : GateVFilter() {}

  /// Read "copy_numbers" from the Python filter configuration.
  void InitializeUserInfo(py::dict &user_info) override;

  /// Return true when the pre-step touchable copy number is accepted.
  bool Evaluate(G4Step *step) const override;

private:
  /// Unique copy numbers accepted by this filter.
  std::set<int> fCopyNumbers;
};

#endif // GateCopyNumberFilter_h
