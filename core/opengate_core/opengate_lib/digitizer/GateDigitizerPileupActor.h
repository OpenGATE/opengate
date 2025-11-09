/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigitizerPileupActor_h
#define GateDigitizerPileupActor_h

#include "GateVDigitizerWithOutputActor.h"
#include <G4Cache.hh>
#include <G4Navigator.hh>
#include <map>
#include <pybind11/stl.h>
#include <variant>

namespace py = pybind11;

/*
 * Digitizer module for pile-up.
 */

class GateDigitizerPileupActor : public GateVDigitizerWithOutputActor {

public:
  // Constructor
  explicit GateDigitizerPileupActor(py::dict &user_info);

  // Destructor
  ~GateDigitizerPileupActor() override;

  void InitializeUserInfo(py::dict &user_info) override;

  // Called every time a Run starts (all threads)
  void BeginOfRunAction(const G4Run *run) override;

  // Called every time an Event ends (all threads)
  void EndOfEventAction(const G4Event *event) override;

  // Called every time a Run ends (all threads)
  void EndOfRunAction(const G4Run *run) override;

  void SetGroupVolumeDepth(int depth);

protected:
  void DigitInitialize(
      const std::vector<std::string> &attributes_not_in_filler) override;

  // User parameters
  int fGroupVolumeDepth;
  double fTimeWindow;

  // Output attribute pointers
  GateVDigiAttribute *fOutputEdepAttribute{};
  GateVDigiAttribute *fOutputGlobalTimeAttribute{};
  GateVDigiAttribute *fOutputVolumeIDAttribute{};

  void ProcessPileup();

  // During computation (thread local)
  struct threadLocalT {
    double *edep;
    double *time;
    GateUniqueVolumeID::Pointer *volID;

    // Storage for piled up singles
    struct PileupGroup {
      double highest_edep;
      double total_edep;
      double first_time;
      double time;
      GateUniqueVolumeID::Pointer volume_id;

      using AttributeValue =
          std::variant<double, int, int64_t, std::string, G4ThreeVector,
                       GateUniqueVolumeID::Pointer>;
      std::map<std::string, AttributeValue> stored_attributes;
    };

    std::map<uint64_t, std::vector<PileupGroup>> volume_groups;
  };
  G4Cache<threadLocalT> fThreadLocalData;

  void StoreAttributeValues(threadLocalT::PileupGroup &group, size_t index);
  void FillAttributeValues(const threadLocalT::PileupGroup &group);
};

#endif // GateDigitizerPileupActor_h
