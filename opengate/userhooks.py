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


def user_hook_dna_regions(simulation_engine):
    em = simulation_engine.physics_engine.g4_em_parameters
    dna_regions = {
        str(region_name): str(dna_type)
        for region_name, dna_type in zip(em.RegionsDNA(), em.TypesDNA())
    }
    volume_regions = {}
    for (
        volume_name,
        volume,
    ) in simulation_engine.simulation.volume_manager.volumes.items():
        region_name = None
        if volume.g4_region is not None:
            region_name = volume.g4_region.GetName()
        volume_regions[volume_name] = region_name

    print("Found the following DNA regions via the user hook:")
    for region_name, dna_type in dna_regions.items():
        print(f"Region {region_name}: {dna_type}")

    simulation_engine.user_hook_log.append(
        {
            "dna_regions": dna_regions,
            "volume_regions": volume_regions,
        }
    )


def user_hook_dna_region_models(simulation_engine):
    eV = g4.G4UnitDefinition.GetValueOf("eV")
    model_checks = {}
    for (
        volume_name,
        volume,
    ) in simulation_engine.simulation.volume_manager.volumes.items():
        model_checks[volume_name] = g4.check_em_model_in_volume(
            volume.g4_logical_volume,
            "e-",
            "e-_G4DNAIonisation",
            100.0 * eV,
        )

    print("Found the following DNA ionisation models via the user hook:")
    for volume_name, model_name in model_checks.items():
        print(f"Volume {volume_name}: {model_name}")

    simulation_engine.user_hook_log.append(model_checks)


def progress_status(filename):
    """
    Factory function returning a progress reporting hook that periodically writes simulation progress status to a JSON file.
    """
    import time
    from datetime import datetime
    from pathlib import Path
    from opengate.serialization import dump_json
    from opengate.utility import g4_units

    def progress_reporter(simulation_engine, status="running"):
        if hasattr(simulation_engine, "simulation"):
            simulation = simulation_engine.simulation
            source_engine = simulation_engine.source_engine
        else:
            # Called directly from source_engine
            source_engine = simulation_engine
            simulation = source_engine.simulation_engine.simulation

        if not hasattr(progress_reporter, "_start_wall_time"):
            progress_reporter._start_wall_time = time.time()
            progress_reporter._start_iso_time = datetime.now().isoformat()

        start_wall_time = progress_reporter._start_wall_time
        start_iso_time = progress_reporter._start_iso_time

        intervals = simulation.run_timing_intervals
        total_sim_time = (
            sum(interval[1] - interval[0] for interval in intervals) / g4_units.s
            if intervals
            else 0.0
        )

        current_wall_time = time.time()
        elapsed_sec = current_wall_time - start_wall_time
        current_iso_time = datetime.now().isoformat()

        # retrieve total number of events (summed on all threads and runs)
        total_events = 0
        if source_engine.g4_master_source_manager:
            total_events += (
                source_engine.g4_master_source_manager.GetTotalGeneratedEvents()
            )
        for mgr in source_engine.g4_thread_source_managers:
            total_events += mgr.GetTotalGeneratedEvents()

        expected_events = source_engine.expected_number_of_events

        events_per_sec = total_events / elapsed_sec if elapsed_sec > 0 else 0.0
        active_mgr = (
            source_engine.g4_thread_source_managers[0]
            if source_engine.g4_thread_source_managers
            else source_engine.g4_master_source_manager
        )
        raw_current_sim_time = (
            active_mgr.GetCurrentSimulationTime() / g4_units.s if active_mgr else 0.0
        )
        if raw_current_sim_time == 0.0 and expected_events and expected_events > 0:
            raw_current_sim_time = (total_events / expected_events) * total_sim_time

        if status == "completed":
            current_sim_time = total_sim_time
            progress_ratio = 1.0
        else:
            current_sim_time = raw_current_sim_time
            progress_ratio = (
                min(1.0, total_events / expected_events)
                if expected_events and expected_events > 0
                else 0.0
            )

        progress_pct = 100.0 if status == "completed" else progress_ratio * 100.0

        if status == "completed":
            current_run_idx = len(intervals) - 1 if intervals else 0
        else:
            current_run_idx = active_mgr.GetCurrentRunId() if active_mgr else 0

        time_pct = (
            100.0
            if status == "completed"
            else (
                (current_sim_time / total_sim_time * 100.0)
                if total_sim_time > 0
                else 0.0
            )
        )

        if status == "completed":
            estimated_remaining_sec = 0.0
        elif events_per_sec > 0 and expected_events and expected_events > total_events:
            remaining_events = expected_events - total_events
            estimated_remaining_sec = remaining_events / events_per_sec
        else:
            estimated_remaining_sec = 0.0

        report_data = {
            "status": status,
            "simulation_id": getattr(simulation, "simulation_id", "unknown"),
            "start_time": start_iso_time,
            "current_time": current_iso_time,
            "elapsed_time_seconds": round(elapsed_sec, 2),
            "estimated_time_remaining_seconds": round(estimated_remaining_sec, 2),
            "run_index": current_run_idx,
            "run_total": len(intervals) if intervals else 0,
            "simulation_time_current": round(current_sim_time, 4),
            "simulation_time_total": round(total_sim_time, 4),
            "simulation_time_progress": round(time_pct, 2),
            "events_total": total_events,
            "events_expected": expected_events,
            "events_progress": round(progress_pct, 2),
            "events_per_second": round(events_per_sec, 2),
        }

        out_path = Path(filename)
        if not out_path.is_absolute():
            out_path = simulation.output_dir / out_path

        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            tmp_path = out_path.with_suffix(".tmp")
            with open(tmp_path, "w") as f:
                dump_json(report_data, f)
            tmp_path.replace(out_path)
        except Exception:
            try:
                with open(out_path, "w") as f:
                    dump_json(report_data, f)
            except Exception:
                pass

        return report_data

    return progress_reporter
