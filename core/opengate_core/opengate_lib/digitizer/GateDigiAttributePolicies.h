/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigiAttributePolicies_h
#define GateDigiAttributePolicies_h

#include "GateDigiCollection.h"
#include "GateVDigiAttribute.h"
#include <pybind11/stl.h>
#include <string>
#include <vector>

namespace py = pybind11;

/*
 * Attribute policies shared by the digitizer modules that group several
 * input digi into one output digi (adder, readout, charge induction).
 *
 * The user gives a dict {attribute name: policy}. For each group (a single,
 * a pixel...), each policy selects ONE input digi whose value is copied to
 * the output digi:
 * - "max", "min": the digi with the largest/smallest value (numeric only)
 * - "first", "last": the earliest/latest digi (GlobalTime)
 * - "energy_winner": the digi with the largest energy score (the module
 *   defines the score: the deposited energy for the adder, the
 *   contribution to the signal of the pixel for the charge induction).
 *
 * Usage in a module:
 * - InitializeUserInfo: read the dict
 * - StartSimulationAction: Check (required attributes, types)
 * - DigitInitialize: AppendNames (to remove them from the filler), then
 *   SetCollections
 * - for each input digi of a group: Update(tracker of the group, ...)
 * - when the output digi is filled: Fill(tracker of the group)
 */

class GateDigiAttributePolicies {
public:
  enum Policy { Max, Min, First, Last, EnergyWinner };

  struct Item {
    std::string fName;
    Policy fPolicy;
    GateVDigiAttribute *fInput{};
    GateVDigiAttribute *fOutput{};
  };

  // Per group: for the k-th attribute, the index of the selected digi
  struct Tracker {
    std::vector<size_t> fIndex;
    std::vector<double> fScore;
    std::vector<bool> fIsSet;
  };

  // read the dict "attribute_policies" of the user info
  void InitializeUserInfo(py::dict &user_info, const std::string &module_name);

  // check that the attributes exist and have a compatible type, and that
  // no policy is set for the attributes computed by the module
  void Check(GateDigiCollection *input,
             const std::vector<std::string> &computed_attributes) const;

  // append the names of the attributes with a policy
  void AppendNames(std::vector<std::string> &names) const;

  // set the input/output attributes (thread local digi collections)
  void SetCollections(GateDigiCollection *input, GateDigiCollection *output);

  bool Empty() const { return fItems.empty(); }

  // consider the input digi 'index' for the group
  void Update(Tracker &tracker, size_t index, double time,
              double energy_score) const;

  // fill the output attributes with the values of the selected digi
  void Fill(const Tracker &tracker) const;

protected:
  std::vector<Item> fItems;
  std::string fModuleName;
};

#endif // GateDigiAttributePolicies_h
