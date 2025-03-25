#ifndef OPENGATE_LIB_CHEMISTRY_ADAPTATOR_H
#define OPENGATE_LIB_CHEMISTRY_ADAPTATOR_H

#include <functional>

class G4DNAMolecularReactionTable;
#include <G4DNAMolecularReactionTable.hh>

template <typename C> class ChemistryAdaptator : public C {
public:
  using ConstructReactionTableHook =
      std::function<void(G4DNAMolecularReactionTable *)>;

public:
  ChemistryAdaptator(int verbosity) {
    C::SetVerboseLevel(verbosity);
    _chemistryLists.push_back(this);
  }

  void
  ConstructTimeStepModel(G4DNAMolecularReactionTable *reactionTable) override {
    C::ConstructTimeStepModel(reactionTable);
    reactionTable->PrintTable();
  }

  void
  ConstructReactionTable(G4DNAMolecularReactionTable *reactionTable) override {
    C::ConstructReactionTable(reactionTable);
    if (_constructReactionTableHook)
      _constructReactionTableHook(reactionTable);
  }

  static C *getChemistryList() {
    for (auto *chemistryList : _chemistryLists) {
      auto *ptr = dynamic_cast<C *>(chemistryList);
      if (ptr != nullptr)
        return ptr;
    }
    return nullptr;
  }

  template <typename T> static void setConstructReactionTableHook(T fn) {
    _constructReactionTableHook = fn;
  }

private:
  inline static ConstructReactionTableHook _constructReactionTableHook;
  inline static std::vector<G4VUserChemistryList *> _chemistryLists;
};

#endif
