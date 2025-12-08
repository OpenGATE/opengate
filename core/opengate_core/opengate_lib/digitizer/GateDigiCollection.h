/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GateDigiCollection_h
#define GateDigiCollection_h

#include "G4TouchableHistory.hh"
#include "GateVDigiAttribute.h"
#include <pybind11/stl.h>

class GateDigiCollectionManager;

class GateDigiCollectionIterator;

/*
 * Management of a Digi Collection.
 * See usage example in GateDigitizerHitsCollectionActor
 *
 * - Can only be created with
 * GateDigiCollectionManager::GetInstance()->NewDigiCollection("toto") (all HC
 * must have a different name) because of root management
 * - Attributes must be initialized before use (in StartSimulationAction)
 *   with a list of attribute names : InitDigiAttributesFromNames
 *
 *  - if root output:
 *    1) SetFilenameAndInitRoot
 *    2) RootInitializeTupleForMaster after attributes initialisation, in
 *       StartSimulationAction
      3) RootInitializeTupleForWorker in RunAction  !! ONLY DURING FIRST RUN !!
      4) FillToRoot to copy the values in the root file
          Can be, e.g., each Event or each Run
          Clear is needed once FillToRootIfNeeded.
 *        This function also sets the internal event index (needed).
 *    5) Write
 *       If MT, need Write for all threads (EndOfRunAction) and for Master
 *       (EndSimulationAction) *
      6) Close may not be needed (unsure)
 *
 */

class GateDigiCollection : public G4VHitsCollection {
public:
  friend GateDigiCollectionManager;

  typedef GateDigiCollectionIterator Iterator;

  ~GateDigiCollection() override;

  void InitDigiAttributesFromNames(const std::vector<std::string> &names);

  void InitDigiAttributesFromCopy(
      GateDigiCollection *input,
      const std::vector<std::string> &skipDigiAttributeNames = {});

  void InitDigiAttribute(GateVDigiAttribute *att);

  void InitDigiAttributeFromName(const std::string &name);

  void RootStartInitialization();

  void RootInitializeTupleForMaster();

  void RootInitializeTupleForWorker();

  void FillToRootIfNeeded(bool clear);

  void Write() const;

  void Close() const;

  void SetWriteToRootFlag(bool f);

  void SetFilenameAndInitRoot(const std::string &filename);

  std::string GetFilename() const { return fFilename; }

  std::string GetTitle() const { return fDigiCollectionTitle; }

  void SetTupleId(int id) { fTupleId = id; }

  int GetTupleId() const { return fTupleId; }

  size_t GetSize() const override;

  void Clear() const;

  std::vector<GateVDigiAttribute *> &GetDigiAttributes() {
    return fDigiAttributes;
  }

  std::set<std::string> GetDigiAttributeNames() const;

  GateVDigiAttribute *GetDigiAttribute(const std::string &name);

  bool IsDigiAttributeExists(const std::string &name) const;

  void FillHits(G4Step *step);

  void FillDigiWithEmptyValue();

  std::string DumpLastDigi() const;

  std::string DumpDigi(int i) const;

  Iterator NewIterator();

  size_t GetBeginOfEventIndex() const;

  void SetBeginOfEventIndex(size_t index) const;

  void SetBeginOfEventIndex() const;

protected:
  // Can only be created by GateDigiCollectionManager
  explicit GateDigiCollection(const std::string &collName);

  std::string fFilename;
  std::string fDigiCollectionName;
  std::string fDigiCollectionTitle;
  std::map<std::string, GateVDigiAttribute *> fDigiAttributeMap;
  std::vector<GateVDigiAttribute *> fDigiAttributes;
  int fTupleId;
  int fCurrentDigiAttributeId;
  bool fWriteToRootFlag;

  // thread local: the index of the beginning
  // of event is specific for each thread
  struct threadLocal_t {
    size_t fBeginOfEventIndex = 0;
  };
  G4Cache<threadLocal_t> threadLocalData;

  void FillToRoot();
};

#endif // GateDigiCollection_h
