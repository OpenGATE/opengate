/* --------------------------------------------------
   Copyright (C): OpenGATE Collaboration
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE.md for further details
   -------------------------------------------------- */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <ostream>

namespace py = pybind11;

#include "G4EmParameters.hh"
#include "G4MscStepLimitType.hh"
#include "G4NuclearFormfactorType.hh"
#include "G4DNAModelSubType.hh"
#include "G4EmSaturation.hh"
#include "G4ThreeVector.hh"
#include "G4Threading.hh"

void init_G4EmParameters(py::module &m) {
    // (prevent to delete from py side with py::nodelete)
    py::class_<G4EmParameters, std::unique_ptr<G4EmParameters, py::nodelete>>(m, "G4EmParameters")

        .def("Instance", &G4EmParameters::Instance, py::return_value_policy::reference)
        .def("ToString", [](G4EmParameters *em) {
            std::ostringstream out;
            out << *em;
            return out.str();
        })

        .def("SetFluo", &G4EmParameters::SetFluo)
        .def("SetAuger", &G4EmParameters::SetAuger)
        .def("SetAugerCascade", &G4EmParameters::SetAugerCascade)
        .def("SetPixe", &G4EmParameters::SetPixe)

        .def("SetLossFluctuations", &G4EmParameters::SetLossFluctuations)
        .def("SetBuildCSDARange", &G4EmParameters::SetBuildCSDARange)
        .def("SetLPM", &G4EmParameters::SetLPM)
        .def("SetUseCutAsFinalRange", &G4EmParameters::SetUseCutAsFinalRange)

        .def("SetDefaults", &G4EmParameters::SetDefaults)

        .def("SetLossFluctuations", &G4EmParameters::SetLossFluctuations)
        .def("LossFluctuation", &G4EmParameters::LossFluctuation)
        .def("SetBuildCSDARange", &G4EmParameters::SetBuildCSDARange)
        .def("BuildCSDARange", &G4EmParameters::BuildCSDARange)
        .def("SetLPM", &G4EmParameters::SetLPM)
        .def("LPM", &G4EmParameters::LPM)

        //.def("SetSpline", &G4EmParameters::SetSpline)
        //.def("Spline", &G4EmParameters::Spline)

        .def("SetUseCutAsFinalRange", &G4EmParameters::SetUseCutAsFinalRange)
        .def("UseCutAsFinalRange", &G4EmParameters::UseCutAsFinalRange)

        .def("SetApplyCuts", &G4EmParameters::SetApplyCuts)
        .def("ApplyCuts", &G4EmParameters::ApplyCuts)

        .def("SetFluo", &G4EmParameters::SetFluo)
        .def("Fluo", &G4EmParameters::Fluo)

        .def("SetBeardenFluoDir", &G4EmParameters::SetBeardenFluoDir)
        .def("BeardenFluoDir", &G4EmParameters::BeardenFluoDir)

        .def("Auger", &G4EmParameters::Auger)
        .def("Pixe", &G4EmParameters::Pixe)

        .def("SetDeexcitationIgnoreCut", &G4EmParameters::SetDeexcitationIgnoreCut)
        .def("DeexcitationIgnoreCut", &G4EmParameters::DeexcitationIgnoreCut)

        .def("SetLateralDisplacement", &G4EmParameters::SetLateralDisplacement)
        .def("LateralDisplacement", &G4EmParameters::LateralDisplacement)

        .def("SetLateralDisplacementAlg96", &G4EmParameters::SetLateralDisplacementAlg96)
        .def("LateralDisplacementAlg96", &G4EmParameters::LateralDisplacementAlg96)

        .def("SetMuHadLateralDisplacement", &G4EmParameters::SetMuHadLateralDisplacement)
        .def("MuHadLateralDisplacement", &G4EmParameters::MuHadLateralDisplacement)

        .def("ActivateAngularGeneratorForIonisation", &G4EmParameters::ActivateAngularGeneratorForIonisation)
        .def("UseAngularGeneratorForIonisation", &G4EmParameters::UseAngularGeneratorForIonisation)

        .def("SetUseMottCorrection", &G4EmParameters::SetUseMottCorrection)
        .def("UseMottCorrection", &G4EmParameters::UseMottCorrection)

        .def("SetIntegral", &G4EmParameters::SetIntegral)
        .def("Integral", &G4EmParameters::Integral)

        .def("SetBirksActive", &G4EmParameters::SetBirksActive)
        .def("BirksActive", &G4EmParameters::BirksActive)

        .def("SetUseICRU90Data", &G4EmParameters::SetUseICRU90Data)
        .def("UseICRU90Data", &G4EmParameters::UseICRU90Data)

        .def("SetDNAFast", &G4EmParameters::SetDNAFast)
        .def("DNAFast", &G4EmParameters::DNAFast)

        .def("SetDNAStationary", &G4EmParameters::SetDNAStationary)
        .def("DNAStationary", &G4EmParameters::DNAStationary)

        .def("SetDNAElectronMsc", &G4EmParameters::SetDNAElectronMsc)
        .def("DNAElectronMsc", &G4EmParameters::DNAElectronMsc)

        .def("SetGeneralProcessActive", &G4EmParameters::SetGeneralProcessActive)
        .def("GeneralProcessActive", &G4EmParameters::GeneralProcessActive)

        .def("SetEnableSamplingTable", &G4EmParameters::SetEnableSamplingTable)
        .def("EnableSamplingTable", &G4EmParameters::EnableSamplingTable)

        .def("SetEnablePolarisation", &G4EmParameters::SetEnablePolarisation)
        .def("EnablePolarisation", &G4EmParameters::EnablePolarisation)

        .def("GetDirectionalSplitting", &G4EmParameters::GetDirectionalSplitting)
        .def("SetDirectionalSplitting", &G4EmParameters::SetDirectionalSplitting)

        .def("QuantumEntanglement", &G4EmParameters::QuantumEntanglement)
        .def("SetQuantumEntanglement", &G4EmParameters::SetQuantumEntanglement)

        .def("RetrieveMuDataFromFile", &G4EmParameters::RetrieveMuDataFromFile)
        .def("SetRetrieveMuDataFromFile", &G4EmParameters::SetRetrieveMuDataFromFile)

            // 5d
        .def("SetOnIsolated", &G4EmParameters::SetOnIsolated)
        .def("OnIsolated", &G4EmParameters::OnIsolated)

        .def("ActivateDNA", &G4EmParameters::ActivateDNA)

            // double parameters with values
        //.def("SetMinSubRange", &G4EmParameters::SetMinSubRange)
        //.def("MinSubRange", &G4EmParameters::MinSubRange)

        .def("SetMinEnergy", &G4EmParameters::SetMinEnergy)
        .def("MinKinEnergy", &G4EmParameters::MinKinEnergy)

        .def("SetMaxEnergy", &G4EmParameters::SetMaxEnergy)
        .def("MaxKinEnergy", &G4EmParameters::MaxKinEnergy)

        .def("SetMaxEnergyForCSDARange", &G4EmParameters::SetMaxEnergyForCSDARange)
        .def("MaxEnergyForCSDARange", &G4EmParameters::MaxEnergyForCSDARange)

        .def("SetLowestElectronEnergy", &G4EmParameters::SetLowestElectronEnergy)
        .def("LowestElectronEnergy", &G4EmParameters::LowestElectronEnergy)

        .def("SetLowestMuHadEnergy", &G4EmParameters::SetLowestMuHadEnergy)
        .def("LowestMuHadEnergy", &G4EmParameters::LowestMuHadEnergy)

        .def("SetLowestTripletEnergy", &G4EmParameters::SetLowestTripletEnergy)
        .def("LowestTripletEnergy", &G4EmParameters::LowestTripletEnergy)

        .def("SetLinearLossLimit", &G4EmParameters::SetLinearLossLimit)
        .def("LinearLossLimit", &G4EmParameters::LinearLossLimit)

        .def("SetBremsstrahlungTh", &G4EmParameters::SetBremsstrahlungTh)
        .def("BremsstrahlungTh", &G4EmParameters::BremsstrahlungTh)
        .def("SetMuHadBremsstrahlungTh", &G4EmParameters::SetMuHadBremsstrahlungTh)
        .def("MuHadBremsstrahlungTh", &G4EmParameters::MuHadBremsstrahlungTh)

        .def("SetLambdaFactor", &G4EmParameters::SetLambdaFactor)
        .def("LambdaFactor", &G4EmParameters::LambdaFactor)

        .def("SetFactorForAngleLimit", &G4EmParameters::SetFactorForAngleLimit)
        .def("FactorForAngleLimit", &G4EmParameters::FactorForAngleLimit)

        .def("SetMscThetaLimit", &G4EmParameters::SetMscThetaLimit)
        .def("MscThetaLimit", &G4EmParameters::MscThetaLimit)

        .def("SetMscEnergyLimit", &G4EmParameters::SetMscEnergyLimit)
        .def("MscEnergyLimit", &G4EmParameters::MscEnergyLimit)

        .def("SetMscRangeFactor", &G4EmParameters::SetMscRangeFactor)
        .def("MscRangeFactor", &G4EmParameters::MscRangeFactor)

        .def("SetMscMuHadRangeFactor", &G4EmParameters::SetMscMuHadRangeFactor)
        .def("MscMuHadRangeFactor", &G4EmParameters::MscMuHadRangeFactor)

        .def("SetMscGeomFactor", &G4EmParameters::SetMscGeomFactor)
        .def("MscGeomFactor", &G4EmParameters::MscGeomFactor)

        .def("SetMscSafetyFactor", &G4EmParameters::SetMscSafetyFactor)
        .def("MscSafetyFactor", &G4EmParameters::MscSafetyFactor)

        .def("SetMscLambdaLimit", &G4EmParameters::SetMscLambdaLimit)
        .def("MscLambdaLimit", &G4EmParameters::MscLambdaLimit)

        .def("SetMscSkin", &G4EmParameters::SetMscSkin)
        .def("MscSkin", &G4EmParameters::MscSkin)

        .def("SetScreeningFactor", &G4EmParameters::SetScreeningFactor)
        .def("ScreeningFactor", &G4EmParameters::ScreeningFactor)

        .def("SetMaxNIELEnergy", &G4EmParameters::SetMaxNIELEnergy)
        .def("MaxNIELEnergy", &G4EmParameters::MaxNIELEnergy)

        .def("SetMaxEnergyFor5DMuPair", &G4EmParameters::SetMaxEnergyFor5DMuPair)
        .def("MaxEnergyFor5DMuPair", &G4EmParameters::MaxEnergyFor5DMuPair)

        .def("SetStepFunction", &G4EmParameters::SetStepFunction)
        .def("SetStepFunctionMuHad", &G4EmParameters::SetStepFunctionMuHad)
        .def("SetStepFunctionLightIons", &G4EmParameters::SetStepFunctionLightIons)
        .def("SetStepFunctionIons", &G4EmParameters::SetStepFunctionIons)
            //.def("FillStepFunction", &G4EmParameters::FillStepFunction)

        .def("SetDirectionalSplittingRadius", &G4EmParameters::SetDirectionalSplittingRadius)
        .def("GetDirectionalSplittingRadius", &G4EmParameters::GetDirectionalSplittingRadius)

        .def("SetDirectionalSplittingTarget", &G4EmParameters::SetDirectionalSplittingTarget)
        .def("GetDirectionalSplittingTarget", &G4EmParameters::GetDirectionalSplittingTarget)

            // integer parameters
        //.def("SetNumberOfBins", &G4EmParameters::SetNumberOfBins)
        .def("NumberOfBins", &G4EmParameters::NumberOfBins)

        .def("SetNumberOfBinsPerDecade", &G4EmParameters::SetNumberOfBinsPerDecade)
        .def("NumberOfBinsPerDecade", &G4EmParameters::NumberOfBinsPerDecade)

        .def("SetVerbose", &G4EmParameters::SetVerbose)
        .def("Verbose", &G4EmParameters::Verbose)

        .def("SetWorkerVerbose", &G4EmParameters::SetWorkerVerbose)
        .def("WorkerVerbose", &G4EmParameters::WorkerVerbose)

        .def("SetMscStepLimitType", &G4EmParameters::SetMscStepLimitType)

        .def("SetMscMuHadStepLimitType", &G4EmParameters::SetMscMuHadStepLimitType)

        .def("SetSingleScatteringType", &G4EmParameters::SetSingleScatteringType)

        .def("SetNuclearFormfactorType", &G4EmParameters::SetNuclearFormfactorType)

        .def("SetDNAeSolvationSubType", &G4EmParameters::SetDNAeSolvationSubType)

            //5d
        .def("SetConversionType", &G4EmParameters::SetConversionType)
        .def("GetConversionType", &G4EmParameters::GetConversionType)

            // string parameters
        .def("SetPIXECrossSectionModel", &G4EmParameters::SetPIXECrossSectionModel)
        .def("PIXECrossSectionModel", &G4EmParameters::PIXECrossSectionModel)

        .def("SetPIXEElectronCrossSectionModel", &G4EmParameters::SetPIXEElectronCrossSectionModel)
        .def("PIXEElectronCrossSectionModel", &G4EmParameters::PIXEElectronCrossSectionModel)

        .def("SetLivermoreDataDir", &G4EmParameters::SetLivermoreDataDir)
        .def("LivermoreDataDir", &G4EmParameters::LivermoreDataDir)

            // parameters per region or per process
        .def("AddPAIModel", &G4EmParameters::AddPAIModel)
        .def("ParticlesPAI", &G4EmParameters::ParticlesPAI)
        .def("RegionsPAI", &G4EmParameters::RegionsPAI)
        .def("TypesPAI", &G4EmParameters::TypesPAI)

        .def("AddMicroElec", &G4EmParameters::AddMicroElec)
        .def("RegionsMicroElec", &G4EmParameters::RegionsMicroElec)

        .def("AddDNA", &G4EmParameters::AddDNA)

        .def("RegionsDNA", &G4EmParameters::RegionsDNA)
        .def("TypesDNA", &G4EmParameters::TypesDNA)

        .def("AddPhysics", &G4EmParameters::AddPhysics)

        .def("RegionsPhysics", &G4EmParameters::RegionsPhysics)
        .def("TypesPhysics", &G4EmParameters::TypesPhysics)

        //.def("SetSubCutoff", &G4EmParameters::SetSubCutoff)

        .def("SetDeexActiveRegion", &G4EmParameters::SetDeexActiveRegion)

        .def("SetProcessBiasingFactor", &G4EmParameters::SetProcessBiasingFactor)

        .def("ActivateForcedInteraction", &G4EmParameters::ActivateForcedInteraction)

        .def("ActivateSecondaryBiasing", &G4EmParameters::ActivateSecondaryBiasing)

        .def("SetEmSaturation", &G4EmParameters::SetEmSaturation)
        .def("GetEmSaturation", &G4EmParameters::GetEmSaturation)

        // initialisation methods
        //.def("DefineRegParamForLoss", &G4EmParameters::DefineRegParamForLoss)
        //.def("DefineRegParamForEM", &G4EmParameters::DefineRegParamForEM)
        //.def("DefineRegParamForDeex", &G4EmParameters::DefineRegParamForDeex)
        ;
}
