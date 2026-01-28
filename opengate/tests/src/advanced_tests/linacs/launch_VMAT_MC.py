import opengate as gate
import numpy as np
import click
import VMAT_MC as t
import time
import os, sys, glob, shutil
import json

# @click.option('--file', default='/home/mjacquet/Documents/Simulation_RT_plan/patient_data/IGR/AGORL_CLB_P1toP20/AGORL_P1/RP.1.2.752.243.1.1.20200108145259306.1700.75605.dcm', help='Pathname to the .xml filenames')
# @click.option('--file', default='./data/DICOM/2.16.840.1.114337.1.20808.1660037786.0.dcm', help='Pathname to the .xml filenames')


@click.command()
@click.option("--nt", default=1, help="number of thread")
@click.option("--nb_part", default=1, help="Number_of_particle_to_simulate")
@click.option(
    "--dcm_file",
    default="./data/Patients_IGR/P1/RTPlan_P1.dcm",
    help="Pathname to the .dcm filenames",
)
@click.option(
    "--arc_id",
    default=None,
    help="ID of the beam sequence to reproduce. If None, all the beam sequences will be simulated",
)
@click.option(
    "--path_img", default="./data/Patients_IGR/P1/", help="img to put in the simulation"
)
@click.option("--img", default="CT_P1_40mm.mhd", help="img to put in the simulation")
@click.option("--output_name", default="water_tank.mhd", help="Dose actor name")
@click.option("--path_output", default="./output", help="Dose actor name")
@click.option(
    "--path_phsp",
    default="/home/mjacquet/Documents/phsp/",
    help="path of the phsp_source",
)
@click.option(
    "--phsp_name", default="phsp_6.4MeV_sx_1.15_sy_0.8.root", help="phsp source name"
)
@click.option("--vis", default=False, help="Use the simulation visualisation")
@click.option(
    "--mode", default=1, help="Define how actors are applied : 0 for normal, 1 for TLE"
)
@click.option(
    "--tle_type",
    default=0,
    help="tle type to apply a cutoff : 0 for an energy threshold (energy),1 for the max range of sec part threshold (max range) or 2 for the average range of sec part threshold (average range)",
)
@click.option(
    "--tle_threshold",
    default=1.6,
    help="threshold on ekin (MeV) or range (mm) depending on the tle_type",
)
@click.option(
    "--ratio",
    default=1,
    help="string information in case of ratio mix between no int on int",
)
@click.option(
    "--shielding", default=True, help="boolean to put a shielding around the LINAC"
)
@click.option(
    "--lead_thickness",
    default=4,
    help="the thickness in cm of the lead part above the jaw",
)
@click.option("--json_input", default=True, help="use a json to define all the input")
@click.option(
    "--json_name",
    default="./data/header.json",
    help="json input name if they are provided via a json file",
)
def launch_simulation(
    nt,
    nb_part,
    dcm_file,
    arc_id,
    path_img,
    img,
    output_name,
    path_output,
    path_phsp,
    phsp_name,
    mode,
    vis,
    tle_type,
    tle_threshold,
    ratio,
    shielding,
    lead_thickness,
    json_input,
    json_name,
):
    nb_jobs = 1
    if json_input:
        f = open(f"./{json_name}")
        json_file = json.load(f)
        print(json_file)
        nt = json_file["nt"]
        nb_part = json_file["nb_part"]
        nb_jobs = json_file["nb_jobs"]
        dcm_file = json_file["dcm_file"]
        arc_id = json_file["arc_id"]
        path_img = json_file["path_img"]
        img = json_file["img"]
        mode = json_file["mode"]
        vis = json_file["vis"]
        tle_type = json_file["tle_type"]
        tle_threshold = json_file["tle_threshold"]
        path_phsp = json_file["path_phsp"]
        phsp_name = json_file["phsp_name"]
        output_name = json_file["output_name"]
        ratio = json_file["ratio"]
        shielding = json_file["shielding"]
        lead_thickness = json_file["lead_thickness"]

    sim, rt_plan_params = t.init_simulation(
        dcm_file,
        arc_id,
        path_img,
        img,
        mode,
        vis=vis,
        tle_type=tle_type,
        tle_threshold=tle_threshold,
        shielding=shielding,
        lead_thickness=lead_thickness,
    )
    if vis:
        sim.visu = True
    sim.number_of_threads = nt
    source = sim.get_source_user_info("phsp_source_global")
    source.phsp_file = path_phsp + phsp_name
    source.batch_size = 100000
    source.n = np.round(rt_plan_params["weight"] * nb_part / nt)
    start_ID = np.random.randint(0, 10**9, 1)
    if nt > 1:
        entry_start = []
        for i in range(nt):
            val = start_ID + i * nb_part / nt
            entry_start.append(val[0])
        source.entry_start = entry_start
    else:
        source.entry_start = start_ID[0]
    actors_list = sim.actor_manager.actors.keys()
    sim.output_dir = path_output
    dose_stat_file_name = ""
    tle_dose_stat_file_name = ""
    dose_json = ""
    tle_dose_json = ""
    if not os.path.isdir(path_output + "/stats_files"):
        os.mkdir(path_output + "/stats_files")
    if not os.path.isdir(path_output + "/tle-stats_files"):
        os.mkdir(path_output + "/tle-stats_files")

    if "dose" in actors_list:
        dose_actor = sim.actor_manager.get_actor("dose")
        dose_actor.dose.output_filename = "./" + output_name[:-4] + "-dose.mhd"
        dose_actor.edep.output_filename = "./" + output_name[:-4] + "-edep.mhd"
        dose_actor.dose_uncertainty.output_filename = (
            "./" + output_name[:-4] + "-dose-uncertainty.mhd"
        )
        dose_actor.edep_uncertainty.output_filename = (
            "./" + output_name[:-4] + "-edep-uncertainty.mhd"
        )
        dose_actor.dose_squared.output_filename = (
            "./" + output_name[:-4] + "-dose-squared.mhd"
        )
        dose_actor.edep_squared.output_filename = (
            "./" + output_name[:-4] + "-edep-squared.mhd"
        )
        dose_stat_file_name = path_output + "/stats_files/stats_file.txt"
        dose_json = path_output + "/header.json"
        print(dose_actor.dose.output_filename)

    if "tle_dose_actor" in actors_list:
        tle_dose_actor = sim.actor_manager.get_actor("tle_dose_actor")
        tle_dose_actor.dose.output_filename = "./" + output_name[:-4] + "-tle-dose.mhd"
        tle_dose_actor.edep.output_filename = "./" + output_name[:-4] + "-tle-edep.mhd"
        tle_dose_actor.dose_uncertainty.output_filename = (
            "./" + output_name[:-4] + "-tle-dose-uncertainty.mhd"
        )
        tle_dose_actor.edep_uncertainty.output_filename = (
            "./" + output_name[:-4] + "-tle-edep-uncertainty.mhd"
        )
        tle_dose_actor.dose_squared.output_filename = (
            "./" + output_name[:-4] + "-tle-dose-squared.mhd"
        )
        tle_dose_actor.edep_squared.output_filename = (
            "./" + output_name[:-4] + "-tle-edep-squared.mhd"
        )
        tle_dose_stat_file_name = path_output + "/tle-stats_files/tle-stats_file.txt"
        tle_dose_json = path_output + "/tle-header.json"

    sim.run()
    nb_event = np.sum(np.round(rt_plan_params["weight"] * nb_part / nt))
    stats = sim.get_actor("stats")
    print(path_output)
    for filename in [dose_stat_file_name, tle_dose_stat_file_name]:
        if filename != "":
            file = open(filename, "w")
            file.write(str(stats))
            file.close()

    for filename in [dose_json, tle_dose_json]:
        if filename != "":
            dict_data = {}
            dict_data["nt"] = nt
            dict_data["nb_part"] = nb_part
            dict_data["nb_event"] = nb_event
            dict_data["dcm_file"] = dcm_file
            dict_data["arc_id"] = arc_id
            dict_data["path_img"] = path_img
            dict_data["img"] = img
            dict_data["output_name"] = output_name
            dict_data["path_output"] = path_output
            dict_data["path_phsp"] = path_phsp
            dict_data["phsp_name"] = phsp_name
            dict_data["vis"] = vis
            dict_data["mode"] = mode
            dict_data["tle_type"] = tle_type
            dict_data["tle_threshold"] = tle_threshold
            dict_data["ratio"] = ratio
            dict_data["nb_jobs"] = nb_jobs
            dict_data["shielding"] = shielding
            dict_data["lead_thickness"] = lead_thickness
            file = open(filename, "w")
            json.dump(dict_data, file, indent=4)

    print(stats)


if __name__ == "__main__":
    launch_simulation()
