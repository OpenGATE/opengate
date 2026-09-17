#include "GateWindowTurboSource.h"
#include "G4CallbackModel.hh"
#include "GateGenericSource.h"
#include "GateHelpersDict.h"
#include "GateSingleParticleSourceWindowTurbo.h"
#include <G4Color.hh>
#include <G4Event.hh>
#include <G4ExceptionSeverity.hh>
#include <G4Run.hh>
#include <G4RunManager.hh>
#include <G4Scene.hh>
#include <G4String.hh>
#include <G4Threading.hh>
#include <G4Types.hh>
#include <G4UImanager.hh>
#include <G4VGraphicsScene.hh>
#include <G4VisAttributes.hh>
#include <G4VisManager.hh>
#include <Randomize.hh>
#include <pybind11/gil.h>
#include <pybind11/pytypes.h>

void GateWindowTurboSource::SetSharedCache(
    std::shared_ptr<GateWindowTurboSharedCache> cache) {
  fSharedCache = std::move(cache);
}

void GateWindowTurboSource::CreateSPS() {
  fSPS = new GateSingleParticleSourceWindowTurbo(fAttachedToVolumeName);
}

void GateWindowTurboSource::InitializeUserInfo(py::dict &user_info) {
  GateGenericSource::InitializeUserInfo(user_info);
  fWeight = -1;
  fWeightSigma = -1;
  fDirectionRelativeToAttachedVolume = false;
  fUserInfo = user_info;
}

double GateWindowTurboSource::CalcNextTime(double current_simulation_time) {
  GateSingleParticleSourceWindowTurbo *spswt =
      reinterpret_cast<GateSingleParticleSourceWindowTurbo *>(fSPS);
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

void GateWindowTurboSource::InitializeSharedCache(py::dict &user_info) {
  if (!fSharedCache->fActRatio.empty())
    return;
  std::lock_guard<std::mutex> lock(fSharedCache->fMutex);
  if (py::isinstance<py::float_>(user_info["act_ratio"])) {
    fSharedCache->fActRatio = {DictGetDouble(user_info, "act_ratio")};
    fSharedCache->fMaxSolidAngle = {
        DictGetDouble(user_info, "max_solid_angle")};
  } else {
    fSharedCache->fActRatio = DictGetVecDouble(user_info, "act_ratio");
    fSharedCache->fMaxSolidAngle =
        DictGetVecDouble(user_info, "max_solid_angle");
  }
}

void GateWindowTurboSource::WriteBackUserInfo() {
  if (!fUserInfo)
    return;
  py::gil_scoped_acquire acquire; // write back needs to acquire gil
  auto direction = py::dict(fUserInfo["direction"]);
  direction["act_ratio"] = fSharedCache->fActRatio;
  direction["max_solid_angle"] = fSharedCache->fMaxSolidAngle;
  direction["init_duration"] = fSharedCache->fInitDuration;
}

void GateWindowTurboSource::PrepareSharedBeforeRun() {
  fCurrentRunId = G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
  GateSingleParticleSourceWindowTurbo *spswt =
      reinterpret_cast<GateSingleParticleSourceWindowTurbo *>(fSPS);
  fCurrentActRatio = GetValueThisRun(fSharedCache->fActRatio);
  G4double max_solid_angle = GetValueThisRun(fSharedCache->fMaxSolidAngle);
  if (max_solid_angle >= 0 and fCurrentActRatio >= 0)
    return;
  if (fSkip)
    return;

  std::lock_guard<std::mutex> lock(fSharedCache->fMutex);

  G4double a1 = GetValueThisRun(fA1);
  G4double a2 = GetValueThisRun(fA2);
  G4double b1 = GetValueThisRun(fB1);
  G4double b2 = GetValueThisRun(fB2);
  G4double plane_distance = GetValueThisRun(fPlaneDistance);
  G4double plane_phi = GetValueThisRun(fPlanePhi);
  spswt->SetParameters(a1, a2, b1, b2, plane_distance, plane_phi);
  G4double duration_sec =
      spswt->InitializeBeforeRun(fCurrentActRatio, max_solid_angle);

  fSharedCache->fInitDuration.push_back(duration_sec);
  SetValueThisRun(fSharedCache->fActRatio, fCurrentActRatio);
  SetValueThisRun(fSharedCache->fMaxSolidAngle, max_solid_angle);
  WriteBackUserInfo();
}

void GateWindowTurboSource::PrepareNextRun() {
  GateGenericSource::PrepareNextRun();
  // TBD: voxelized source prepare next run here
  auto *ang = fSPS->GetAngDist();
  auto *spswt = reinterpret_cast<GateSingleParticleSourceWindowTurbo *>(fSPS);
  ang->fGlobalRotation = G4RotationMatrix();

  // setup act ratio and max solid angle once per shared cache/run
  PrepareSharedBeforeRun();

  G4double a1 = GetValueThisRun(fA1);
  G4double a2 = GetValueThisRun(fA2);
  G4double b1 = GetValueThisRun(fB1);
  G4double b2 = GetValueThisRun(fB2);
  G4double plane_distance = GetValueThisRun(fPlaneDistance);
  G4double plane_phi = GetValueThisRun(fPlanePhi);
  spswt->SetParameters(a1, a2, b1, b2, plane_distance, plane_phi);
  const G4double max_solid_angle =
      GetValueThisRun(fSharedCache->fMaxSolidAngle);
  spswt->SetMaxSolidAngle(max_solid_angle);
}

void GateWindowTurboSource::Visualize() const {
  if (G4Threading::GetNumberOfRunningWorkerThreads() > 0 and fVisCount > 0) {
    G4Exception("GateWindowTurboSource::Visualize", "VisualizeWTSourceInMTMode",
                JustWarning,
                "Visualize for GateWindowTurboSource is not supported in MT "
                "mode. The origin of the source will be wrong.");
  }
  GateGenericSource::Visualize();
  if (visualization_window_color.size() > 0) {
    for (size_t i = 0; i < visualization_window_color.size(); i++) {
      VisualizeOneWindow(visualization_window_color[i],
                         visualization_window_width[i],
                         visualization_window_run_id[i]);
    }
  }
}

void GateWindowTurboSource::InitializeDirection(py::dict puser_info) {

  auto *ang = fSPS->GetAngDist();
  ang->SetAngDistType("iso");
  auto user_info = py::dict(puser_info["direction"]);
  if (py::isinstance<py::float_>(user_info["a1"])) {
    fA1 = {DictGetDouble(user_info, "a1")};
    fA2 = {DictGetDouble(user_info, "a2")};
    fB1 = {DictGetDouble(user_info, "b1")};
    fB2 = {DictGetDouble(user_info, "b2")};
    fPlaneDistance = {DictGetDouble(user_info, "plane_distance")};
    fPlanePhi = {DictGetDouble(user_info, "plane_phi")};
  } else {
    fA1 = DictGetVecDouble(user_info, "a1");
    fA2 = DictGetVecDouble(user_info, "a2");
    fB1 = DictGetVecDouble(user_info, "b1");
    fB2 = DictGetVecDouble(user_info, "b2");
    fPlaneDistance = DictGetVecDouble(user_info, "plane_distance");
    fPlanePhi = DictGetVecDouble(user_info, "plane_phi");
  }
  InitializeSharedCache(user_info);

  fSkip = DictGetBool(user_info, "skip_mode");

  GateSingleParticleSourceWindowTurbo *spswt =
      reinterpret_cast<GateSingleParticleSourceWindowTurbo *>(fSPS);
  spswt->InitializeUserInfo(user_info);
  if (fAAManager == nullptr) {
    fAAManager = new GateAcceptanceAngleManager;
    fSPS->SetAAManager(fAAManager);
  }
  if (fFDManager == nullptr) {
    fFDManager = new GateForcedDirectionManager;
    fSPS->SetFDManager(fFDManager);
  }
}
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

namespace {
G4Color GetColor(const py::handle &color_py) {
  if (py::isinstance<py::str>(color_py)) {
    G4Color color;
    const std::string color_str = color_py.cast<std::string>();
    G4Color::GetColor(color_str, color);
    return color;
  }

  const auto rgba = color_py.cast<std::vector<G4double>>();

  if (rgba.size() == 3)
    return {rgba[0], rgba[1], rgba[2], 1.0};
  return {rgba[0], rgba[1], rgba[2], rgba[3]};
}
std::vector<G4Color> DictGetVecColor(py::dict &user_info,
                                     const std::string &key) {
  std::vector<G4Color> l;
  auto color_list = py::list(user_info[key.c_str()]);
  for (const auto color : color_list) {
    l.push_back(GetColor(color));
  }
  return l;
}

} // namespace

void GateWindowTurboSource::InitializeVisualization(py::dict puser_info) {
  GateGenericSource::InitializeVisualization(puser_info);
  auto user_info = py::dict(puser_info["visualization"]);
  visualization_window_run_id = DictGetVecInt(user_info, "window_run_id");
  visualization_window_width = DictGetVecDouble(user_info, "window_width");
  visualization_window_color = DictGetVecColor(user_info, "window_color");
}

void GateWindowTurboSource::VisualizeOneWindow(G4Color color, G4double width,
                                               int run_id) const {
  G4ThreeVector pos1, pos2, pos3, pos4;
  GetWindowVertex(pos1, pos2, pos3, pos4, run_id);

  VisWindow *window = new VisWindow(pos1, pos2, pos3, pos4, color, width);
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
  G4cout << "Visualizing window for run " << run_id << ": " << description
         << G4endl;

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
                                            G4Color color, G4double width) {

  fPolyline.push_back(pos1);
  fPolyline.push_back(pos3);
  fPolyline.push_back(pos4);
  fPolyline.push_back(pos2);
  fPolyline.push_back(pos1);
  G4VisAttributes va;
  va.SetLineWidth(width);
  va.SetColor(color);
  fPolyline.SetVisAttributes(va);
}

void GateWindowTurboSource::VisWindow::operator()(
    G4VGraphicsScene &sceneHandler, const G4ModelingParameters *) {
  sceneHandler.BeginPrimitives();
  sceneHandler.AddPrimitive(fPolyline);
  sceneHandler.EndPrimitives();
}
