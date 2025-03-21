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
    _chemistryList = this;
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
    // https://stackoverflow.com/questions/14243854/c-dynamic-cast-causes-a-segfault-even-when-the-object-that-is-casted-is-not-n
    // avoid dynamic_cast here because RTTI information comes from a linked
    // library static_cast is safe (this inherits C*)
    auto *ptr = static_cast<C *>(_chemistryList);
    return ptr;
  }

  template <typename T> static void setConstructReactionTableHook(T fn) {
    _constructReactionTableHook = fn;
  }

private:
  inline static ConstructReactionTableHook _constructReactionTableHook;
  inline static G4VUserChemistryList *_chemistryList = nullptr;
};

#endif
