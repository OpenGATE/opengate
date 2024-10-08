import opengate.engines
import opengate_core as g4

import opengate.physics
from opengate.utility import get_material_name_variants


def get_ions_generated_per_spot(simulation_engine):
    sources = [
        s
        for s in simulation_engine.source_engine.sources
        if s.type_name == "TreatmentPlanPBSource"
    ]
    generated_primaries = {}
    for i, s in enumerate(sources):
        print(s.user_info.name)
        generated_primaries[s.user_info.name + f"_{i}"] = s.get_generated_primaries()
    print(generated_primaries)


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


def user_hook_dump_material_properties(simulation_engine):
    print("*** In user hook dump_material_properties ***")
    for vol in simulation_engine.simulation.volume_manager.volumes.values():
        material_name = vol.g4_material.GetName()
        material_dict = opengate.physics.load_optical_properties_from_xml(
            simulation_engine.simulation.physics_manager.optical_properties_file,
            material_name,
        )
        print(f"Volume {vol.name} has material {material_name}")
        mpt = vol.g4_material.GetMaterialPropertiesTable()
        if mpt is not None and material_dict is not None:
            const_prop_names = mpt.GetMaterialConstPropertyNames()
            vector_prop_names = mpt.GetMaterialPropertyNames()
            if not set(material_dict["constant_properties"].keys()).issubset(
                set([str(n) for n in const_prop_names])
            ):
                print(
                    "NOT all constant_properties from file found in G4MaterialPropertiesTable"
                )
                simulation_engine.user_hook_log.append(False)
            else:
                simulation_engine.user_hook_log.append(True)
            if not set(material_dict["vector_properties"].keys()).issubset(
                set([str(n) for n in vector_prop_names])
            ):
                print(
                    "NOT all vector_properties from file found in G4MaterialPropertiesTable"
                )
                simulation_engine.user_hook_log.append(False)
            else:
                simulation_engine.user_hook_log.append(True)
        elif mpt is None and material_dict is not None:
            print(
                f"Geant4 does not find any MaterialPropertiesTable for this material "
                f"although it is defined in the optical_properties_file "
                f"{simulation_engine.simulation.physics_manager.optical_properties_file}"
            )
            simulation_engine.user_hook_log.extend([False, False])
    print("*** ------------------------------------- ***")


def user_hook_em_switches(simulation_engine):
    switches = {}
    switches["auger"] = simulation_engine.physics_engine.g4_em_parameters.Auger()
    switches["fluo"] = simulation_engine.physics_engine.g4_em_parameters.Fluo()
    switches["pixe"] = simulation_engine.physics_engine.g4_em_parameters.Pixe()
    switches["auger_cascade"] = (
        simulation_engine.physics_engine.g4_em_parameters.AugerCascade()
    )
    switches["deexcitation_ignore_cut"] = (
        simulation_engine.physics_engine.g4_em_parameters.DeexcitationIgnoreCut()
    )
    simulation_engine.user_hook_log.append(switches)
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
    simulation_engine.user_hook_log.append(active_regions)
