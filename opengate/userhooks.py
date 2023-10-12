import opengate_core as g4


def check_production_cuts(simulation_engine):
    """Function to be called by opengate after initialization
    of the simulation, i.e. when G4 volumes and regions exist.
    The purpose is to check whether Geant4 has properly set
    the production cuts in the specific region.

    The value max_step_size is stored in the attribute hook_log
    which can be accessed via the output of the simulation.

    """
    print(f"Entered hook")
    rs = g4.G4RegionStore.GetInstance()
    print("Known regions are:")
    for i in range(rs.size()):
        print("*****")
        print(f"{rs.Get(i).GetName()}")
        reg = rs.Get(i)
        pcuts = reg.GetProductionCuts()
        if pcuts is not None:
            cut_proton = pcuts.GetProductionCut("proton")
            cut_positron = pcuts.GetProductionCut("e+")
            cut_electron = pcuts.GetProductionCut("e-")
            cut_gamma = pcuts.GetProductionCut("gamma")
            print("Cuts in this region:")
            print(f"gamma: {cut_gamma}")
            print(f"electron: {cut_electron}")
            print(f"proton: {cut_proton}")
            print(f"positron: {cut_positron}")
        else:
            print("Found no cuts in this region")


def user_hook_em_switches(simulation_engine):
    switches = {}
    switches["auger"] = simulation_engine.physics_engine.g4_em_parameters.Auger()
    switches["fluo"] = simulation_engine.physics_engine.g4_em_parameters.Fluo()
    switches["pixe"] = simulation_engine.physics_engine.g4_em_parameters.Pixe()
    switches[
        "auger_cascade"
    ] = simulation_engine.physics_engine.g4_em_parameters.AugerCascade()
    switches[
        "deexcitation_ignore_cut"
    ] = simulation_engine.physics_engine.g4_em_parameters.DeexcitationIgnoreCut()
    simulation_engine.hook_log.append(switches)
    print("Found the following em parameters via the user hook:")
    for k, v in switches.items():
        print(f"{k}: {v}")


def user_hook_active_regions(simulation_engine):
    active_regions = {}
    active_regions["world"] = g4.check_active_region("DefaultRegionForTheWorld")
    active_regions["world"] = g4.check_active_region("DefaultRegionForTheWorld")
    for region in simulation_engine.simulation.physics_manager.regions.values():
        active_regions[region.name] = g4.check_active_region(region.name)
    print(f"Found the following em switches via the user hook:")
    for r, s in active_regions.items():
        print(f"Region {r}:")
        print(f"    deexcitation activated: {s[0]}")
        print(f"    auger activated: {s[1]}")
    simulation_engine.hook_log.append(active_regions)
