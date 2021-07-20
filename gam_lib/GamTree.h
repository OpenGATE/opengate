/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#ifndef GamTree_h
#define GamTree_h

#include <pybind11/stl.h>
#include "GamVActor.h"
#include "GamHelpers.h"
#include "GamTBranch.h"


class GamTree {
public:
    GamTree(std::string vname);

    std::string fTreeName = "Tree";
    std::vector<GamVBranch *> fBranches;
    std::map<std::string, GamVBranch *> fBranchesMap;

    void AddBranch(std::string vname);

    void FillStep(G4Step *step, G4TouchableHistory *touchable);

    GamVBranch *GetBranch(std::string vname);

    GamBranch<double> *GetDoubleBranch(std::string vname);

    GamBranch<G4ThreeVector> *GetThreeVectorBranch(std::string vname);

    GamBranch<std::string> *GetStringBranch(std::string vname);

    std::string Dump();

    // To root (via G4?)
    void WriteToRoot(std::string filename);

};

class EnergyWindow {
public:
    unsigned long fIndex;
    std::shared_ptr<GamTree> fSingles;
    std::shared_ptr<GamTree> fWindow;
    double Emin;
    double Emax;

    void DoIt() {
        auto edep = fSingles->GetDoubleBranch("TotalEnergyDeposit")->values;

        /*
         FIXME
         - call every ? event ? batch of event ?
         - need to copy all branches, need to know type
         - alternative : list of index ; then copy

         */
        std::vector<unsigned long> index;
        for (unsigned long i = 0; i < edep.size(); i++) {
            if (edep[i] >= Emin and edep[i] <= Emax) {
                index.push_back(i);
            }
        }
        DDD("size");
        DDD(index.size());
        for (auto b:fSingles->fBranches) {
            b->CopyValues(fWindow->GetBranch(b->fBranchName), index);
        }
    }
};


class TakeEnergyCentroid {
public:
    unsigned long fIndex;
    std::shared_ptr<GamTree> fHits;
    std::shared_ptr<GamTree> fSingles;

    void DoIt() {
        auto Ein = fHits->GetDoubleBranch("TotalEnergyDeposit");
        auto Eout = fSingles->GetDoubleBranch("TotalEnergyDeposit");
        auto PosIn = fHits->GetThreeVectorBranch("PostPosition");
        auto PosOut = fSingles->GetThreeVectorBranch("PostPosition");
        double Etot = 0;
        G4ThreeVector position;
        auto n = Ein->values.size();
        for (auto i = fIndex; i < n; i++) {
            auto E = Ein->values[i];
            auto p = PosIn->values[i];
            Etot += E;
            p = p + E * p;
        }
        if (n != fIndex) {
            Eout->values.push_back(Etot);
            PosOut->values.push_back(position);
        }

        // FIXME how to guarantee same size in all branches ?!

        // other branches: copy only the first hits value (to change)
        std::vector<unsigned long> index;
        index.push_back(fIndex);
        if (n != fIndex) {// do not copy if no hit
            for (auto b:fSingles->fBranches) { // FIXME as a function CopyValue etc
                if (b->fBranchName != "TotalEnergyDeposit")
                    if (b->fBranchName != "PostPosition") {
                        // FIXME check branch exist in fHits
                        fHits->GetBranch(b->fBranchName)->CopyValues(b, index);
                    }
            }
        }

        // next index
        fIndex = n;
    }

};


#endif // GamTree_h
