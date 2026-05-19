// TODO: 需要自行清除 ang->fGlobalRotation，如果
// 复用GateGenericSource::PrepareNextRun()的话
// 每个线程各算各的粒子数
#include "GateWindowTurboSource.h"
#include "G4CallbackModel.hh"
#include "GateHelpersDict.h"
#include "GateSingleParticleSourceWindowTurbo.h"
#include "GateVSource.h"
#include <G4Colour.hh>
#include <G4Event.hh>
#include <G4Run.hh>
#include <G4RunManager.hh>
#include <G4String.hh>
#include <G4Threading.hh>
#include <G4Types.hh>
#include <Randomize.hh>
#include <pybind11/gil.h>
#include <pybind11/pytypes.h>

// G4bool GateWindowTurboSource::random_engine_initialized = false;

void GateWindowTurboSource::CreateSPS() {
  auto &ll = GetThreadLocalDataGenericSource();
  ll.fSPS = new GateSingleParticleSourceWindowTurbo(fAttachedToVolumeName);
}

void GateWindowTurboSource::InitializeUserInfo(py::dict &user_info) {
  GateGenericSource::InitializeUserInfo(user_info);
  // TBD: should these be addressed in python side?
  fWeight = -1;
  fWeightSigma = -1;
  fDirectionRelativeToAttachedVolume = false;
  if (G4Threading::IsMasterThread())
    fUserInfo = user_info;
}

// TBD: override update TAC?

double GateWindowTurboSource::CalcNextTime(double current_simulation_time) {
  GateSingleParticleSourceWindowTurbo *spswt =
      reinterpret_cast<GateSingleParticleSourceWindowTurbo *>(
          GetThreadLocalDataGenericSource().fSPS);
  G4double act_ratio;
  if (fSkip) {
    if (not spswt->PosGenerated()) {
      spswt->GeneratePos();
    }
    act_ratio = spswt->GetCurrentSolidAngle() / (4 * M_PI);
  } else
    act_ratio = fCurrentActRatio;

  double next_time = current_simulation_time;
  if ((fMaxN <= 0)) {
    next_time = current_simulation_time -
                log(G4UniformRand()) * (1.0 / fActivity / act_ratio);
  }
  return next_time;
}

void GateWindowTurboSource::CallOnceBeforeRun(
    G4int run_id, GateSingleParticleSourceWindowTurbo *spswt) {
  fCurrentRunId = run_id;
  fCurrentActRatio = GetValueThisRun(fActRatio, run_id);
  G4double max_solid_angle = GetValueThisRun(fMaxSolidAngle, run_id);
  if (max_solid_angle >= 0 and fCurrentActRatio >= 0)
    return;
  if (fSkip)
    return;
  G4double a1 = GetValueThisRun(fA1);
  G4double a2 = GetValueThisRun(fA2);
  G4double b1 = GetValueThisRun(fB1);
  G4double b2 = GetValueThisRun(fB2);
  G4double plane_distance = GetValueThisRun(fPlaneDistance);
  G4double plane_phi = GetValueThisRun(fPlanePhi);
  spswt->SetParameters(a1, a2, b1, b2, plane_distance, plane_phi);
  spswt->InitializeBeforeRun(fCurrentActRatio, max_solid_angle);
  SetValueThisRun(fActRatio, run_id, fCurrentActRatio);
  SetValueThisRun(fMaxSolidAngle, run_id, max_solid_angle);
  // G4cout << "CallOnceBeforeRun for run " << run_id
  //        << ", current act ratio: " << fCurrentActRatio
  //        << " current max solid angle: " << max_solid_angle << " thread id "
  //        << G4Threading::G4GetThreadId() << G4endl;
  py::gil_scoped_acquire acquire; // write back need to acquire gil
  auto direction = py::dict(fUserInfo["direction"]);
  direction["act_ratio"] = fActRatio;
  direction["max_solid_angle"] = fMaxSolidAngle;
}

void GateWindowTurboSource::PrepareNextRun() {
  GateGenericSource::PrepareNextRun();
  // TBD: voxelized source prepare next run here
  auto &ll = GetThreadLocalDataGenericSource();
  auto *ang = ll.fSPS->GetAngDist();
  auto *spswt =
      reinterpret_cast<GateSingleParticleSourceWindowTurbo *>(ll.fSPS);
  ang->fGlobalRotation = G4RotationMatrix();
  const G4int run_id =
      G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();

  // setup act ratio and max solid if needed with one of the worker thread
  std::call_once(GetInitializeBeforeRunFlag(run_id),
                 &GateWindowTurboSource::CallOnceBeforeRun, this, run_id,
                 spswt);

  G4double a1 = GetValueThisRun(fA1);
  G4double a2 = GetValueThisRun(fA2);
  G4double b1 = GetValueThisRun(fB1);
  G4double b2 = GetValueThisRun(fB2);
  G4double plane_distance = GetValueThisRun(fPlaneDistance);
  G4double plane_phi = GetValueThisRun(fPlanePhi);
  spswt->SetParameters(a1, a2, b1, b2, plane_distance, plane_phi);
  const G4double max_solid_angle = GetValueThisRun(fMaxSolidAngle);
  spswt->SetMaxSolidAngle(max_solid_angle);
}

std::once_flag &
GateWindowTurboSource::GetInitializeBeforeRunFlag(G4int run_id) {
  std::lock_guard<std::mutex> lock(fInitializeBeforeRunMutex);
  auto it = fInitializeBeforeRunFlags.try_emplace(run_id).first;
  return it->second;
}

// void GateWindowTurboSource::GeneratePrimaries(
//     G4Event *event, const double current_simulation_time) {
//   GateGenericSource::GeneratePrimaries(event, current_simulation_time);
// auto &ll = GetThreadLocalDataGenericSource();
// GateSingleParticleSourceWindowTurbo *sps =
//     reinterpret_cast<GateSingleParticleSourceWindowTurbo *>(ll.fSPS);
// if (fSkip) {
//   G4double current_solid_angle = sps->GetCurrentSolidAngle();
//   ll.fCurrentSkippedEvents += 4 * M_PI / current_solid_angle - 1;
//   ll.fEffectiveEventTime +=
//       G4RandGamma::shoot(ll.fCurrentSkippedEvents, fActivity);
// }
// TODO:finish this
// }

void GateWindowTurboSource::InitializeDirection(py::dict puser_info) {

  auto &ll = fThreadLocalDataGenericSource.Get();
  auto *ang = ll.fSPS->GetAngDist();
  ang->SetAngDistType("iso");
  auto user_info = py::dict(puser_info["direction"]);
  if (py::isinstance<py::float_>(user_info["a1"])) {
    fA1 = {DictGetDouble(user_info, "a1")};
    fA2 = {DictGetDouble(user_info, "a2")};
    fB1 = {DictGetDouble(user_info, "b1")};
    fB2 = {DictGetDouble(user_info, "b2")};
    fPlaneDistance = {DictGetDouble(user_info, "plane_distance")};
    fPlanePhi = {DictGetDouble(user_info, "plane_phi")};
    fActRatio = {DictGetDouble(user_info, "act_ratio")};
    fMaxSolidAngle = {DictGetDouble(user_info, "max_solid_angle")};
  } else {
    fA1 = DictGetVecDouble(user_info, "a1");
    fA2 = DictGetVecDouble(user_info, "a2");
    fB1 = DictGetVecDouble(user_info, "b1");
    fB2 = DictGetVecDouble(user_info, "b2");
    fPlaneDistance = DictGetVecDouble(user_info, "plane_distance");
    fPlanePhi = DictGetVecDouble(user_info, "plane_phi");
    fActRatio = DictGetVecDouble(user_info, "act_ratio");
    fMaxSolidAngle = DictGetVecDouble(user_info, "max_solid_angle");
  }
  {
    std::lock_guard<std::mutex> lock(fInitializeBeforeRunMutex);
    fInitializeBeforeRunFlags.clear();
  }
  fSkip = DictGetBool(user_info, "skip_mode");

  GateSingleParticleSourceWindowTurbo *spswt =
      reinterpret_cast<GateSingleParticleSourceWindowTurbo *>(ll.fSPS);
  spswt->InitializeUserInfo(user_info);
  if (ll.fAAManager == nullptr) {
    ll.fAAManager = new GateAcceptanceAngleManager;
    ll.fSPS->SetAAManager(ll.fAAManager);
  }
  if (ll.fFDManager == nullptr) {
    ll.fFDManager = new GateForcedDirectionManager;
    ll.fSPS->SetFDManager(ll.fFDManager);
  }
}

// void GateWindowTurboSource::LoadVoxelizedPhantom(G4String filename) {
//   if (m_posSPS)
//     delete m_posSPS;
//   m_posSPS = new GateVoxelizedPosDistribution(filename);
//   m_angSPS->SetPosDistribution(m_posSPS);
// }

// void GateWindowTurboSource::SetPhantomPosition(G4ThreeVector pos) {
//   GateVoxelizedPosDistribution *posDist =
//       dynamic_cast<GateVoxelizedPosDistribution *>(m_posSPS);
//   if (posDist)
//     posDist->SetPosition(pos);
//   else
//     G4cout << "Can't use this command unless a voxelized phantom has already
//     "
//               "been loaded."
//            << G4endl;
// }

void GateWindowTurboSource::GetWindowVertex(G4ThreeVector &pos1,
                                            G4ThreeVector &pos2,
                                            G4ThreeVector &pos3,
                                            G4ThreeVector &pos4,
                                            G4int run_id) const {
  G4double a1 = GetValueThisRun(fA1, run_id);
  G4double a2 = GetValueThisRun(fA2, run_id);
  G4double b1 = GetValueThisRun(fB1, run_id);
  G4double b2 = GetValueThisRun(fB2, run_id);
  G4double plane_distance = GetValueThisRun(fPlaneDistance, run_id);
  G4double plane_phi = GetValueThisRun(fPlanePhi, run_id);
  pos1 = {plane_distance, a1, b1};
  pos2 = {plane_distance, a1, b2};
  pos3 = {plane_distance, a2, b1};
  pos4 = {plane_distance, a2, b2};
  // rotate with plane_phi
  G4double s = sin(plane_phi);
  G4double c = cos(plane_phi);
  G4RotationMatrix rot({{c, s, 0}, {-s, c, 0}, {0, 0, 1}});
  pos1 = rot * pos1;
  pos2 = rot * pos2;
  pos3 = rot * pos3;
  pos4 = rot * pos4;
}

void GateWindowTurboSource::VisualizeWindowWithColourName(G4String colour_name,
                                                          G4double width,
                                                          int run_id) const {
  G4Colour colour;
  G4Colour::GetColour(colour_name, colour);
  VisualizeWindow(colour, width, run_id);
}

void GateWindowTurboSource::VisualizeWindowWithRGBA(std::vector<G4double> rgba,
                                                    G4double width,
                                                    int run_id) const {
  G4Colour colour(rgba[0], rgba[1], rgba[2], rgba[3]);
  VisualizeWindow(colour, width, run_id);
}

void GateWindowTurboSource::VisualizeWindow(G4Colour colour, G4double width,
                                            int run_id) const {
  G4ThreeVector pos1, pos2, pos3, pos4;
  GetWindowVertex(pos1, pos2, pos3, pos4, run_id);

  VisWindow *window = new VisWindow(pos1, pos2, pos3, pos4, colour, width);
  G4VModel *model =
      new G4CallbackModel<GateWindowTurboSource::VisWindow>(window);
  model->SetType("Turbo Window");
  model->SetGlobalTag("Turbo Window");
  G4String description = "Turbo Window: ";
  description += "(" + std::to_string(pos1.x()) + " " +
                 std::to_string(pos1.y()) + " " + std::to_string(pos1.z()) +
                 "), ";
  description += "(" + std::to_string(pos2.x()) + " " +
                 std::to_string(pos2.y()) + " " + std::to_string(pos2.z()) +
                 "), ";
  description += "(" + std::to_string(pos3.x()) + " " +
                 std::to_string(pos3.y()) + " " + std::to_string(pos3.z()) +
                 "), ";
  description += "(" + std::to_string(pos4.x()) + " " +
                 std::to_string(pos4.y()) + " " + std::to_string(pos4.z()) +
                 ")";
  model->SetGlobalDescription(description);

  G4VisManager *fpVisManager = G4VisManager::GetInstance();
  G4Scene *pScene = fpVisManager->GetCurrentScene();
  const G4String &currentSceneName = pScene->GetName();
  G4bool successful = pScene->AddRunDurationModel(model, true);
  G4UImanager::GetUIpointer()->ApplyCommand("/vis/scene/notifyHandlers");
}

GateWindowTurboSource::VisWindow::VisWindow(const G4Vector3D &pos1,
                                            const G4Vector3D &pos2,
                                            const G4Vector3D &pos3,
                                            const G4Vector3D &pos4,
                                            G4Colour colour, G4double width) {

  fPolyline.push_back(pos1);
  fPolyline.push_back(pos3);
  fPolyline.push_back(pos4);
  fPolyline.push_back(pos2);
  fPolyline.push_back(pos1);
  G4VisAttributes va;
  va.SetLineWidth(width);
  va.SetColour(colour);
  fPolyline.SetVisAttributes(va);
}

void GateWindowTurboSource::VisWindow::operator()(
    G4VGraphicsScene &sceneHandler, const G4ModelingParameters *) {
  sceneHandler.BeginPrimitives();
  sceneHandler.AddPrimitive(fPolyline);
  sceneHandler.EndPrimitives();
}
