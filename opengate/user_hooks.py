from opengate_core import G4RegionStore


def check_production_cuts(simulation_engine):
    """Function to be called by opengate after initialization
    of the simulation, i.e. when G4 volumes and regions exist.
    The purpose is to check whether Geant4 has properly set
    the production cuts in the specific region.

    The value max_step_size is stored in the attribute hook_log
    which can be accessed via the output of the simulation.

    """
    print(f"Entered hook")
    rs = G4RegionStore.GetInstance()
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
