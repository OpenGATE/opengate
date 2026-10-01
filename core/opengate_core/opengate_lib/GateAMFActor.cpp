/* Copyright (C): OpenGATE Collaboration. LGPL; see LICENSE.md. */
#include "GateAMFActor.h"
#include "GateHelpers.h"
#include "GateHelpersDict.h"
#include "G4EmCalculator.hh"
#include "G4RandomTools.hh"
#include "G4Track.hh"
#include "G4ParticleDefinition.hh"
#include <itkImageRegionIterator.h>
#include <algorithm>
#include <fstream>
#include <sstream>

GateAMFActor::GateAMFActor(py::dict &user_info) : GateVActor(user_info, false) {
  fActions.insert("SteppingAction");
  fActions.insert("BeginOfEventAction");
}
GateAMFActor::~GateAMFActor() = default;

void GateAMFActor::InitializeUserInfo(py::dict &user_info) {
  GateVActor::InitializeUserInfo(user_info);
  fHitType = DictGetStr(user_info, "hit_type");
  fTranslation = DictGetG4ThreeVector(user_info, "translation");
  fImageSpacing = DictGetG4ThreeVector(user_info, "spacing");
  fImageSize = DictGetG4ThreeVector(user_info, "size");
  fImageRotation = DictGetG4RotationMatrix(user_info, "rotation");
  calculator = std::make_unique<MicrodosimetricCalculator>(
      nybin, 2 * fdomainRadiusInUm, fdomainRadiusInUm, fNucleusRadiusInUm,
      fBetaRefinGyminus2, 2, 9);
  calculator->setTSEDfilename(DictGetStr(user_info, "tsed_file_name"));
  calculator->setCalculationFlags(true, fdoseAveragedLinealEnergySaturationCorrected,
                                  fdoseAveragedLinealEnergy);
}

void GateAMFActor::InitializeCpp() {
  GateVActor::InitializeCpp();
  auto allocate = [this]() {
    auto image = Image3DType::New();
    Image3DType::SizeType size;
    Image3DType::SpacingType spacing;
    for (int i = 0; i < 3; ++i) { size[i] = fImageSize[i]; spacing[i] = fImageSpacing[i]; }
    image->SetRegions(size);
    image->SetSpacing(spacing);
    image->Allocate();
    image->FillBuffer(0);
    return image;
  };
  cpp_amf_dose_image = allocate();
  if (fdoseAveragedLinealEnergy) cpp_amf_dose_averaged_lineal_energy = allocate();
  if (fdoseAveragedLinealEnergySaturationCorrected)
    cpp_amf_dose_averaged_lineal_energy_saturation_corrected = allocate();
  if (fAlphaMCFMKMFlag) cpp_amf_alpha_mcfmkm_image = allocate();
  if (fBetaMCFMKMFlag) cpp_amf_beta_mcfmkm_image = allocate();
  if (fMicrodosimetricSpectra) {
    cpp_amf_microdosimetric_spectra = ImageVectorType::New();
    cpp_amf_microdosimetric_spectra->SetRegions(cpp_amf_dose_image->GetLargestPossibleRegion());
    cpp_amf_microdosimetric_spectra->SetSpacing(cpp_amf_dose_image->GetSpacing());
    cpp_amf_microdosimetric_spectra->SetNumberOfComponentsPerPixel(nybin);
    cpp_amf_microdosimetric_spectra->Allocate();
    VectorPixelType zero; zero.SetSize(nybin); zero.Fill(0);
    cpp_amf_microdosimetric_spectra->FillBuffer(zero);
  }
}

void GateAMFActor::BeginOfRunActionMasterThread(int run_id) {
  if (run_id != 0 || fFinalized) Fatal("AMFActor supports one run interval only");
  NbOfEvent = 0;
  auto attach = [this](Image3DType::Pointer image) {
    if (image) AttachImageToVolume<Image3DType>(image, fPhysicalVolumeName, fTranslation, fImageRotation);
  };
  attach(cpp_amf_dose_image);
  attach(cpp_amf_dose_averaged_lineal_energy);
  attach(cpp_amf_dose_averaged_lineal_energy_saturation_corrected);
  attach(cpp_amf_alpha_mcfmkm_image);
  attach(cpp_amf_beta_mcfmkm_image);
  if (fMicrodosimetricSpectra)
    AttachImageToVolume<ImageVectorType>(cpp_amf_microdosimetric_spectra, fPhysicalVolumeName, fTranslation, fImageRotation);
  auto spacing = cpp_amf_dose_image->GetSpacing();
  fVoxelVolume = spacing[0] * spacing[1] * spacing[2];
}

double GateAMFActor::getDose(G4Step *step) const {
  return step->GetTotalEnergyDeposit() / CLHEP::joule * step->GetTrack()->GetWeight() /
      (step->GetPreStepPoint()->GetMaterial()->GetDensity() / (CLHEP::kg / CLHEP::mm3) * fVoxelVolume);
}
double GateAMFActor::GetStoppingPower(G4Step *step) const {
  G4EmCalculator emcalc;
  return emcalc.ComputeTotalDEDX(step->GetTrack()->GetKineticEnergy(),
       step->GetTrack()->GetDefinition(), step->GetPreStepPoint()->GetMaterial()) / (CLHEP::keV / CLHEP::um);
}
void GateAMFActor::GetVoxelPosition(G4Step *step, G4ThreeVector &position,
                                  bool &inside, Image3DType::IndexType &index) const {
  const auto pre = step->GetPreStepPoint()->GetPosition();
  const auto post = step->GetPostStepPoint()->GetPosition();
  if (fHitType == "pre") position = pre;
  else if (fHitType == "post") position = post;
  else if (fHitType == "middle") position = (pre + post) * .5;
  else position = pre + G4UniformRand() * (post - pre);
  Image3DType::PointType point;
  for (int i = 0; i < 3; ++i) point[i] = position[i];
  inside = cpp_amf_dose_image->TransformPhysicalPointToIndex(point, index);
}

void GateAMFActor::SteppingAction(G4Step *step) {
  const auto particle = step->GetTrack()->GetDefinition();
  const double mass = particle->GetAtomicMass(), charge = particle->GetAtomicNumber();
  if (mass <= 0 || charge < 1 || charge > 18) return;
  const double energy = (step->GetPreStepPoint()->GetKineticEnergy() +
       step->GetPostStepPoint()->GetKineticEnergy()) / (2 * CLHEP::MeV * mass);
  if (energy < .025) return;
  const double dose = getDose(step);
  if (dose <= 0) return;
  G4ThreeVector position;
  bool inside;
  Image3DType::IndexType index;
  GetVoxelPosition(step, position, inside, index);
  if (!inside) return;
  VectorPixelType spectrum;
  double yd = 0, ys = 0;
  calculator->calculateDoseWeightedMicrodosimetricFunctionFast(
      spectrum, charge, mass, energy, GetStoppingPower(step), dose, yd, ys);
  if (fMicrodosimetricSpectra)
    ImageAddValue<ImageVectorType>(cpp_amf_microdosimetric_spectra, index, spectrum);
  if (fdoseAveragedLinealEnergy)
    ImageAddValue<Image3DType>(cpp_amf_dose_averaged_lineal_energy, index, yd);
  if (fdoseAveragedLinealEnergySaturationCorrected)
    ImageAddValue<Image3DType>(cpp_amf_dose_averaged_lineal_energy_saturation_corrected, index, ys);
  if (fAlphaMCFMKMFlag || fBetaMCFMKMFlag) {
    auto labels = GetHistogramLabels();
    const double density = step->GetPreStepPoint()->GetMaterial()->GetDensity() / (CLHEP::g / CLHEP::cm3);
    const double domain = CLHEP::pi * density * fdomainRadiusInUm * fdomainRadiusInUm;
    const double nucleus = CLHEP::pi * density * fNucleusRadiusInUm * fNucleusRadiusInUm;
    double alpha = 0, c = 0, total = 0;
    for (size_t i = 0; i < labels.size(); ++i) {
      const double y = labels[i];
      const double a = fAlphaNotinGyminus1 + fBetaRefinGyminus2 * .16022 * y / domain;
      const double t = a * .16022 * y / nucleus + fBetaRefinGyminus2 * std::pow(.16022 * y / nucleus, 2);
      if (t == 0) continue;
      const double correction = (1 - std::exp(-t)) / t;
      alpha += a * correction * spectrum[i];
      c += correction * spectrum[i];
      total += spectrum[i];
    }
    if (!std::isfinite(total) || total <= 0) Fatal("AMF: invalid biological normalization");
    if (fAlphaMCFMKMFlag)
      ImageAddValue<Image3DType>(cpp_amf_alpha_mcfmkm_image, index, alpha * dose / total);
    if (fBetaMCFMKMFlag)
      ImageAddValue<Image3DType>(cpp_amf_beta_mcfmkm_image, index, std::sqrt(fBetaRefinGyminus2 * std::pow(c / total, 2)) * dose);
  }
  ImageAddValue<Image3DType>(cpp_amf_dose_image, index, dose);
}

int GateAMFActor::EndOfRunActionMasterThread(int run_id) {
  if (run_id != 0 || fFinalized) Fatal("AMF: duplicate or unsupported run finalization");
  if (fMicrodosimetricSpectra)
    divideVectorImageByScalarImage(cpp_amf_microdosimetric_spectra, cpp_amf_dose_image);
  for (auto image : {cpp_amf_dose_averaged_lineal_energy,
                    cpp_amf_dose_averaged_lineal_energy_saturation_corrected,
                    cpp_amf_alpha_mcfmkm_image, cpp_amf_beta_mcfmkm_image})
    if (image) divideImage3DByImage3D(image, cpp_amf_dose_image);
  if (fBetaMCFMKMFlag) squareImage(cpp_amf_beta_mcfmkm_image);
  fFinalized = true;
  return 0;
}
std::vector<double> GateAMFActor::GetHistogramLabels() const {
  std::vector<double> labels; calculator->get_Histo_X_Labels(labels); return labels;
}
void GateAMFActor::divideImage3DByImage3D(Image3DType::Pointer numerator, Image3DType::Pointer denominator) {
  itk::ImageRegionIterator<Image3DType> n(numerator, numerator->GetLargestPossibleRegion());
  itk::ImageRegionIterator<Image3DType> d(denominator, denominator->GetLargestPossibleRegion());
  for (n.GoToBegin(), d.GoToBegin(); !n.IsAtEnd(); ++n, ++d) n.Set(d.Get() ? n.Get() / d.Get() : 0);
}
void GateAMFActor::divideVectorImageByScalarImage(ImageVectorType::Pointer numerator, Image3DType::Pointer denominator) {
  itk::ImageRegionIterator<ImageVectorType> n(numerator, numerator->GetLargestPossibleRegion());
  itk::ImageRegionIterator<Image3DType> d(denominator, denominator->GetLargestPossibleRegion());
  for (n.GoToBegin(), d.GoToBegin(); !n.IsAtEnd(); ++n, ++d) {
    auto value = n.Get();
    if (d.Get()) value /= d.Get(); else value.Fill(0);
    n.Set(value);
  }
}
void GateAMFActor::squareImage(Image3DType::Pointer image) {
  itk::ImageRegionIterator<Image3DType> it(image, image->GetLargestPossibleRegion());
  for (it.GoToBegin(); !it.IsAtEnd(); ++it) it.Set(it.Get() * it.Get());
}

// Constructor with all parameters
MicrodosimetricCalculator::MicrodosimetricCalculator(size_t nybin_val, double celDiam, double domainRadius,
                            double nucleusRadius, double betaRef, int iunit_val, int mparased_val)
    : nybin(nybin_val), CelDiam(celDiam), fDomainRadius(domainRadius),
        fNucleusRadius(nucleusRadius), fBetaRef(betaRef), iunit(iunit_val), mparased(mparased_val),
        factor(0.0), unitconv(0.0), binsperDecade(0.0), y0(0.0), ypower(-3.0) {
    if (nybin != 400 || iunit != 2 || mparased != 9 ||
        !std::isfinite(CelDiam) || CelDiam < .003 || CelDiam > 1.0 ||
        !std::isfinite(fDomainRadius) || fDomainRadius <= 0 ||
        !std::isfinite(fNucleusRadius) || fNucleusRadius <= 0 ||
        !std::isfinite(fBetaRef) || fBetaRef <= 0) {
        Fatal("AMF: invalid calculator dimensions, domain or biological parameters");
    }
    initialize();
}


inline int MicrodosimetricCalculator::buildIonParamCombos(
    double depev,
    int ic1, int ie1, int ip1,
    double ratioc, double ratioe, double ratiop,
    IonParamCombo combos[8],          // output
    double& weightedA8                // output: Σ weight * A8
) const {
    int idx = 0;
    weightedA8 = 0.0;
    const bool depevZero = (depev == 0.0);

    for (int ip = ip1; ip <= ip1 + 1; ++ip) {
        double Rp = (ip == ip1) ? (1.0 - ratiop) : ratiop;
        for (int ie = ie1; ie <= ie1 + 1; ++ie) {
            double Re = (ie == ie1) ? (1.0 - ratioe) : ratioe;
            for (int ic = ic1; ic <= ic1 + 1; ++ic) {
                double Rc = (ic == ic1) ? (1.0 - ratioc) : ratioc;
                double w  = Rp * Re * Rc;

                int index = ((ip - 1) * 96) + ((ie - 1) * 8) + (ic - 1);
                const auto& row = IonData[index];

                IonParamCombo& c = combos[idx++];
                c.weight = w;
                c.A0 = row[0];
                c.A1 = row[1];
                c.A2 = row[2];
                c.A3 = row[3];
                c.A4 = row[4];
                c.A5 = row[5];
                c.A6 = row[6];
                c.A7 = row[7];
                c.A8 = row[8];

                weightedA8 += w * c.A8;

                if (!depevZero && c.A8 > 0.0 && c.A2 != 0.0) {
                    c.cst1    = depev / c.A8;
                    double denom = c.cst1 * c.A2;
                    c.firstPref = 2.0 / (denom * denom);
                } else {
                    c.cst1     = 0.0;
                    c.firstPref = 0.0;
                }

                if (c.A6 > 0.0 && c.A7 != 0.0) {
                    c.logBase7 = std::log((c.A7 - 1.0) / c.A7);
                } else {
                    c.logBase7 = 0.0;
                }
            }
        }
    }
    return idx; // should always be 8
}

inline double MicrodosimetricCalculator::sedmeanFast(
    double x,
    bool depevZero,
    const IonParamCombo* combos,
    int nCombos
) const {
    double sed = 0.0;

    for (int k = 0; k < nCombos; ++k) {
        const IonParamCombo& c = combos[k];
        const double w = c.weight;

        double getfirst = 0.0;
        double getsecond = 0.0;
        double getthird = 0.0;

        // First component
        if (c.A0 > 0.0) {
            if (depevZero) {
                double dx  = std::abs(x - c.A1);
                double tmp = (dx > 0.0)
                           ? std::pow(dx, c.A2) / (2.0 * c.A1)
                           : 0.0;
                if (tmp > 50.0) tmp = 50.0;
                getfirst = c.A0 * std::exp(-tmp);
            } else {
                double tmp = c.A1 * (x - c.cst1 * c.A2);
                if (tmp > 50.0) tmp = 50.0;
                double denom = std::exp(tmp) + 1.0;
                getfirst = c.A0 * x / denom * c.firstPref;
            }
        }

        // Second component
        if (c.A3 > 0.0) {
            double dx  = std::abs(x - c.A4);
            double tmp = (dx > 0.0)
                       ? std::pow(dx, c.A5) / (2.0 * c.A4)
                       : 0.0;
            if (tmp > 50.0) tmp = 50.0;
            getsecond = c.A3 * std::exp(-tmp);
        }

        // Third component
        if (c.A6 > 0.0) {
            // pow(base, x) -> exp(log(base) * x), log(base) precomputed
            double tmp = std::exp(c.logBase7 * x);
            getthird = c.A6 / (c.A7 - 1.0) * tmp;
        }

        double total = getfirst + getsecond + getthird;
        if (total > 1.0e-10) {
            sed += w * total;
        }
        // (else: original code clamps very small sedfunc to 0)
    }

    return sed;
}

void MicrodosimetricCalculator::calculateDoseWeightedMicrodosimetricFunctionFast(
    VectorPixelType& microDosSpectra,
    double izz,
    double iAA,
    double energyPerNucleon,
    double dEdx,
    double dose,
    double& LinealEnergy_Dose,
    double& LinealEnergy_Dose_saturation_correctedS)
{
    if (IonData.size() != ROWS) Fatal("AMF: coefficient data has not been loaded");
    if (!std::isfinite(izz) || izz < 1 || izz > 18 ||
        !std::isfinite(iAA) || iAA <= 0 ||
        !std::isfinite(energyPerNucleon) || energyPerNucleon < .025 ||
        !std::isfinite(dEdx) || dEdx < 0 || !std::isfinite(dose) || dose < 0) {
        Fatal("AMF: invalid particle, energy, stopping power or dose");
    }
    LinealEnergy_Dose = 0.0;
    LinealEnergy_Dose_saturation_correctedS = 0.0;
    // Resize only if needed – no Fill(), we overwrite every element.
    if (microDosSpectra.Size() != nybin) {
        microDosSpectra.SetSize(nybin);
    }

    double sum0 = 0.0, sum1 = 0.0, sum2 = 0.0;
    double sumYdy = 0.0;
    double zNumerator = 0.0;
    double zDenominator = 0.0;

    // Energy in eV
    const double erg = energyPerNucleon * iAA;
    const double depev = std::min(dEdx * CelDiam * 1.0e3, erg * 1.0e6);
    const bool depevZero = (depev == 0.0);

    int ic1, ie1, ip1;
    double ratioc, ratioe, ratiop;

    getAparaion(CelDiam, energyPerNucleon, static_cast<int>(iAA),
                static_cast<int>(izz),
                ratioc, ratioe, ratiop, ic1, ie1, ip1);

    // Precompute parameter combinations once
    IonParamCombo combos[8];
    double weightedA8 = 0.0;
    int nCombos = buildIonParamCombos(
        depev, ic1, ie1, ip1,
        ratioc, ratioe, ratiop,
        combos, weightedA8);

    // Factor using weighted A8 (matches original sedmean behaviour)
    double factorLocal;
    if (iunit == 0 || weightedA8 == 0.0) {
        factorLocal = 1.0;
    } else {
        factorLocal = 1.0e6 / weightedA8;
    }

    // main loop over y-bins
    for (size_t i = 0; i < nybin; ++i) {
        const double ymid_val = ymid[i];
        const double ywid_val = ywid[i];

        const double eventmid = ymid_val * factorLocal * unitconv;

        // y * sedmean(y)
        const double y_sed = ymid_val *
                             sedmeanFast(eventmid, depevZero, combos, nCombos);

        const double ydy_val = y_sed * ymid_val;   // y^2 * sedmean(y)

        // Accumulate integrals
        sum0   += y_sed * ywid_val / ymid_val;    // ∫ f(y) dy
        sum1   += y_sed * ywid_val;               // ∫ y f(y) dy
        sum2   += y_sed * ywid_val * ymid_val;    // ∫ y^2 f(y) dy
        sumYdy += ydy_val;                        // Σ ydy (for normalization)

        if (fdoseAveragedLinealEnergySaturationCorrected) {
            zNumerator   += y_sed * Z[i];
            zDenominator += y_sed;
        }

        // Store un-normalized ydy; we normalize in a second pass
        ydy[i] = ydy_val;
    }

    if (!std::isfinite(sumYdy) || sumYdy <= 0 ||
        !std::isfinite(sum0) || sum0 <= 0 || !std::isfinite(sum1) || sum1 <= 0 ||
        !std::isfinite(sum2)) Fatal("AMF: coefficient distribution has no finite positive normalization");

    // Normalization factor (already precomputed binsperDecade in initialize())
    const double normalization_factor =
        (binsperDecade / std::log(10.0)) / sumYdy;

    for (size_t i = 0; i < nybin; ++i) {
        ydy[i] *= normalization_factor;
        microDosSpectra[i] = ydy[i] * dose;
    }
    // yD calculation
    if (fdoseAveragedLinealEnergy) {
        if (sum1 == 0.0) {
            std::cout << "Warning: sum1 is zero, returning zero vector." << std::endl;
            LinealEnergy_Dose = 0.0;
        } else {
            LinealEnergy_Dose = (sum2 / sum1) * dose;
        }
    }

    // yS calculation (saturation-corrected)
    if (fdoseAveragedLinealEnergySaturationCorrected && zDenominator > 0.0) {
        const double LinealEnergy_Freq = sum1 / sum0;
        LinealEnergy_Dose_saturation_correctedS =
            ((zNumerator / zDenominator) / LinealEnergy_Freq) * (y0 * y0) * dose;
    }
}


void MicrodosimetricCalculator::initialize() {
    ypower = -3.0;  // Initialize here instead

    if (yhig.size() != nybin + 1) yhig.resize(nybin + 1);
    if (yfy.size() != nybin) yfy.resize(nybin);
    if (ydy.size() != nybin) ydy.resize(nybin); // Resize ydy

    if (ymid.size() != nybin) ymid.resize(nybin);
    if (ywid.size() != nybin) ywid.resize(nybin);
    if (eventmid.size() != nybin) eventmid.resize(nybin);
    if (Z.size() != nybin) Z.resize(nybin);
    if (histo_x_labels.size() != nybin) histo_x_labels.resize(nybin);

    for (size_t i = 0; i < yhig.size(); ++i) {
        yhig[i] = std::pow(10.0, ypower);
        ypower += ystep;
    }

    if (iunit <= 1) {
        unitconv = 1.0;
    } else if (iunit == 2) {
        unitconv = 1.0e-3 * (2.0 / 3.0 * CelDiam);
    } else if (iunit == 3) {
        unitconv = 4.0 / 3.0 * M_PI * std::pow(CelDiam / 2.0, 3) * 1.0e-15 / 1.602e-13;
    }

    // // Calculate y0
    y0 = (M_PI * fDomainRadius * std::pow(fNucleusRadius, 2)) / (std::sqrt(fBetaRef * (std::pow(fDomainRadius, 2) + std::pow(fNucleusRadius, 2))) * 0.16022);

    for (size_t i = 0; i < nybin; ++i) {
        double ymid_val = (yhig[i] + yhig[i + 1]) / 2.0;
        ymid[i] = ymid_val;
        ywid[i] = yhig[i + 1] - yhig[i];
        Z[i] = 1 - std::exp(-std::pow(ymid_val, 2) / std::pow(y0, 2));
        histo_x_labels[i] = ymid_val;
    }

    // // Calculate the bins per decade
    binsperDecade = nybin / (std::log10(yhig.back() / yhig[0]));
}


void MicrodosimetricCalculator::get_Histo_X_Labels(std::vector<double>& labels) const {
    labels = histo_x_labels;
}


void MicrodosimetricCalculator::calculateDoseWeightedMicrodosimetricFunction(VectorPixelType& microDosSpectra, double izz, double iAA, double energyPerNucleon, double dEdx, double dose, double& LinealEnergy_Dose, double& LinealEnergy_Dose_saturation_correctedS)
{
    if (microDosSpectra.Size() != nybin) {
        microDosSpectra.SetSize(nybin);
        // microDosSpectra.Fill(0.0);
    }

    double factor;
    double sum0 = 0.0, sum1 = 0.0, sum2 = 0.0;
    double Apara[mparased] = {0.0};
    int ic1, ie1, ip1;
    double ratioc, ratioe, ratiop;
    double erg = energyPerNucleon * iAA;
    double depev = std::min(dEdx * CelDiam * 1.0e3, erg * 1.0e6);

    getAparaion(CelDiam, energyPerNucleon, iAA, izz, ratioc, ratioe, ratiop, ic1, ie1, ip1);
    sedmean(1.0, depev, ic1, ie1, ip1, ratioc, ratioe, ratiop, Apara);
    factor = (iunit == 0) ? 1.0 : 1.0e6 / Apara[8];

    double sumYdy = 0.0;
    double zNumerator = 0.0;
    double zDenominator = 0.0;

    for (size_t i = 0; i < nybin; ++i) {
        double eventmid = ymid[i] * factor * unitconv;
        yfy[i] = ymid[i] * sedmean(eventmid, depev, ic1, ie1, ip1, ratioc, ratioe, ratiop, Apara);
        ydy[i] = yfy[i] * ymid[i]; // Calculate ydy
        sum0 += yfy[i] * ywid[i] / ymid[i];
        sum1 += yfy[i] * ywid[i];
        sum2 += yfy[i] * ywid[i] * ymid[i];
        sumYdy += ydy[i];   // for normalization
        if (fdoseAveragedLinealEnergySaturationCorrected) {
            zNumerator   += yfy[i] * Z[i];
            zDenominator += yfy[i];
        }
    }

    double normalization_factor = (binsperDecade / std::log(10)) / sumYdy;

    for (size_t i = 0; i < ydy.size(); ++i) {
        ydy[i] *= normalization_factor;
        microDosSpectra[i] = ydy[i]*dose;
    }

    // yD calculation
    if (fdoseAveragedLinealEnergy){
        if (sum1 == 0) {
            std::cout << "Warning: sum1 is zero, returning zero vector." << std::endl;
            LinealEnergy_Dose = 0.0;
            return;
        }
        LinealEnergy_Dose = sum2/sum1;
        LinealEnergy_Dose *= dose;
    }
    // yS calculation
    if (fdoseAveragedLinealEnergySaturationCorrected && zDenominator > 0.0) {
        double LinealEnergy_Freq = sum1 / sum0;
        LinealEnergy_Dose_saturation_correctedS = ((zNumerator / zDenominator) / LinealEnergy_Freq) * (y0 * y0);
        LinealEnergy_Dose_saturation_correctedS *= dose;
    }

    return;
}



void MicrodosimetricCalculator::getAparaion(const double& CelDiam, const double& energyPerNucleon, const int& iAA, const int& izz, double& ratioc, double& ratioe, double& ratiop, int& ic1, int& ie1, int& ip1) {
    auto bracket = [](const auto &grid, double value, bool logarithmic,
                      int &lower, double &fraction) {
        size_t upper = 1;
        while (upper + 1 < grid.size() && value > grid[upper]) ++upper;
        lower = static_cast<int>(upper); // original one-based lower index
        if (value <= grid.front()) { fraction = 0.0; return; }
        if (value >= grid.back()) { fraction = 1.0; return; }
        const double low = grid[upper - 1], high = grid[upper];
        fraction = logarithmic ? std::log10(value / low) / std::log10(high / low)
                               : (value - low) / (high - low);
    };
    bracket(cdiamion, CelDiam, true, ic1, ratioc);
    bracket(eincion, energyPerNucleon, true, ie1, ratioe);
    bracket(izion, izz, false, ip1, ratiop);
}


inline double MicrodosimetricCalculator::sedfunc(double x, double depev, const double Apara[], size_t size) {
    double getfirst = 0.0, getsecond = 0.0, getthird = 0.0;

    if (Apara[0] > 0.0) {
        double tmp;
        if (depev == 0.0) {
            tmp = std::min(50.0, std::pow(std::abs(x - Apara[1]), Apara[2]) / (2 * Apara[1]));
            getfirst = Apara[0] * std::exp(-tmp);
        } else {
            double cst1 = depev / Apara[8];
            tmp = std::min(50.0, Apara[1] * (x - cst1 * Apara[2]));
            getfirst = Apara[0] * x / (std::exp(tmp) + 1) * (2.0 / std::pow(cst1 * Apara[2], 2));
        }
    }

    if (Apara[3] > 0.0) {
        double tmp = std::min(50.0, std::pow(std::abs(x - Apara[4]), Apara[5]) / (2 * Apara[4]));
        getsecond = Apara[3] * std::exp(-tmp);
    }

    if (Apara[6] > 0.0) {
        getthird = Apara[6] / (Apara[7] - 1.0) * std::pow((Apara[7] - 1.0) / Apara[7], x);
    }

    double sedfunc = getfirst + getsecond + getthird;
    if (sedfunc < 1.0e-10) {
        sedfunc = 0.0;
    }
    return sedfunc;
}

inline double MicrodosimetricCalculator::sedmean(double x, double depev, int ic1, int ie1, int ip1, double ratioc, double ratioe, double ratiop, double Apara[]) {
    double sedmean = 0.0;
    double A9 = 0.0;

    for (int ip = ip1; ip <= ip1 + 1; ip++) {
        double Rp = (ip == ip1) ? (1.0 - ratiop) : ratiop;
        for (int ie = ie1; ie <= ie1 + 1; ie++) {
            double Re = (ie == ie1) ? (1.0 - ratioe) : ratioe;
            for (int ic = ic1; ic <= ic1 + 1; ic++) {
                double Rc = (ic == ic1) ? (1.0 - ratioc) : ratioc;
                int index = ((ip-1) * 96) + ((ie-1) * 8) + (ic-1);
                for (int i = 0; i < mparased; i++) {
                    Apara[i] = IonData[index][i];
                }
                double wei = Rp * Re * Rc;
                double sedfuncResult = sedfunc(x, depev, Apara, mparased);
                sedmean += sedfuncResult * wei;
                A9 += Apara[8] * wei;
            }
        }
    }
    Apara[8] = A9;
    return sedmean;
}

void MicrodosimetricCalculator::setTSEDfilename(const std::string& filename) {
    fTSEDfilename = filename;
    loadIonData();
}

void MicrodosimetricCalculator::loadIonData() {
    std::ifstream file(fTSEDfilename);
    if (!file) Fatal("AMF: cannot open coefficient file " + fTSEDfilename);
    std::vector<std::vector<double>> parsed;
    std::string line;
    while (std::getline(file, line)) {
        std::istringstream stream(line);
        stream >> std::ws;
        if (stream.eof()) continue;
        std::vector<double> values(COLS);
        for (auto &value : values) {
            if (!(stream >> value) || !std::isfinite(value))
                Fatal("AMF: expected nine finite coefficients per row in " + fTSEDfilename);
        }
        stream >> std::ws;
        if (!stream.eof()) Fatal("AMF: extra coefficient column in " + fTSEDfilename);
        if (values[0] < 0 || values[3] < 0 || values[6] < 0 || values[8] <= 0 ||
            (values[0] > 0 && (values[1] <= 0 || values[2] <= 0)) ||
            (values[3] > 0 && (values[4] <= 0 || values[5] <= 0)) ||
            (values[6] > 0 && values[7] <= 1) ||
            (values[0] == 0 && values[3] == 0 && values[6] == 0))
            Fatal("AMF: invalid distribution coefficients in " + fTSEDfilename);
        parsed.push_back(std::move(values));
        if (parsed.size() > ROWS) Fatal("AMF: expected exactly 576 coefficient rows");
    }
    if (file.bad() || parsed.size() != ROWS) Fatal("AMF: expected exactly 576 coefficient rows");
    IonData = std::move(parsed);
}
