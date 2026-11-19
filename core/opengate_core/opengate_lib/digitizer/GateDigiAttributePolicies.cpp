/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include "GateDigiAttributePolicies.h"
#include "../GateHelpers.h"
#include "GateHelpersDigitizer.h"
#include <algorithm>
#include <sstream>

void GateDigiAttributePolicies::InitializeUserInfo(
    py::dict &user_info, const std::string &module_name) {
  fModuleName = module_name;
  fItems.clear();
  if (!user_info.contains("attribute_policies"))
    return;
  const auto policies = py::dict(user_info["attribute_policies"]);
  for (const auto &item : policies) {
    Item a;
    a.fName = std::string(py::str(item.first));
    const auto p = std::string(py::str(item.second));
    if (p == "max")
      a.fPolicy = Max;
    else if (p == "min")
      a.fPolicy = Min;
    else if (p == "first")
      a.fPolicy = First;
    else if (p == "last")
      a.fPolicy = Last;
    else if (p == "energy_winner")
      a.fPolicy = EnergyWinner;
    else {
      std::ostringstream oss;
      oss << "Error in " << fModuleName << ": unknown attribute policy '" << p
          << "' for the attribute '" << a.fName
          << "'. Must be max, min, first, last or energy_winner.";
      Fatal(oss.str());
    }
    fItems.push_back(a);
  }
}

void GateDigiAttributePolicies::Check(
    GateDigiCollection *input,
    const std::vector<std::string> &computed_attributes) const {
  for (const auto &a : fItems) {
    if (std::find(computed_attributes.begin(), computed_attributes.end(),
                  a.fName) != computed_attributes.end()) {
      Fatal("Error in " + fModuleName +
            ": no attribute policy can be set "
            "for '" +
            a.fName + "', this attribute is computed by the module.");
    }
    CheckRequiredAttribute(input, a.fName);
    const auto type = input->GetDigiAttribute(a.fName)->GetDigiAttributeType();
    if ((a.fPolicy == Max || a.fPolicy == Min) && type != 'D' && type != 'I' &&
        type != 'L') {
      Fatal("Error in " + fModuleName +
            ": the policies max and min "
            "require a numeric attribute (double, int, int64), which is not "
            "the case of '" +
            a.fName + "'.");
    }
  }
}

void GateDigiAttributePolicies::AppendNames(
    std::vector<std::string> &names) const {
  for (const auto &a : fItems)
    names.emplace_back(a.fName);
}

void GateDigiAttributePolicies::SetCollections(GateDigiCollection *input,
                                               GateDigiCollection *output) {
  for (auto &a : fItems) {
    a.fInput = input->GetDigiAttribute(a.fName);
    a.fOutput = output->GetDigiAttribute(a.fName);
  }
}

void GateDigiAttributePolicies::Update(Tracker &tracker, const size_t index,
                                       const double time,
                                       const double energy_score) const {
  const auto n = fItems.size();
  if (n == 0)
    return;
  if (tracker.fIndex.size() < n) {
    tracker.fIndex.resize(n, 0);
    tracker.fScore.resize(n, 0.0);
    tracker.fIsSet.resize(n, false);
  }
  // every policy keeps the digi of largest score (the first one in case of
  // equality)
  for (size_t k = 0; k < n; k++) {
    const auto &a = fItems[k];
    double score = 0;
    switch (a.fPolicy) {
    case Max:
    case Min: {
      double value;
      switch (a.fInput->GetDigiAttributeType()) {
      case 'D':
        value = a.fInput->GetDValues()[index];
        break;
      case 'I':
        value = a.fInput->GetIValues()[index];
        break;
      default:
        value = static_cast<double>(a.fInput->GetLValues()[index]);
      }
      score = a.fPolicy == Max ? value : -value;
      break;
    }
    case First:
      score = -time;
      break;
    case Last:
      score = time;
      break;
    case EnergyWinner:
      score = energy_score;
      break;
    }
    if (!tracker.fIsSet[k] || score > tracker.fScore[k]) {
      tracker.fIndex[k] = index;
      tracker.fScore[k] = score;
      tracker.fIsSet[k] = true;
    }
  }
}

void GateDigiAttributePolicies::Fill(const Tracker &tracker) const {
  for (size_t k = 0; k < fItems.size(); k++) {
    const auto &a = fItems[k];
    a.fOutput->Fill(a.fInput, tracker.fIndex[k]);
  }
}
