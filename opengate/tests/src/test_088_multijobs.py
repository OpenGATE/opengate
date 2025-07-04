#!/usr/bin/env python
import argparse
import os
import itk
from multiprocessing import Pool

from opengate.tests import utility
import matplotlib.pyplot as plt
import opengate as gate
import glob
import numpy as np
import pyvista as pv
from scipy.optimize import curve_fit

from scipy.spatial.transform import Rotation as R
import spekpy as sp
#import critical_angle 
#import psutil
from test_088_vpg_tle_script import *
DEFAULT_OUTPUT = 'debug_new' #file name where single root file are stocked
DEFAULT_NUMBER_OF_JOBS = 1
DEFAULT_NUMBER_OF_PARTICLES = 1e6
DEFAULT_POSITION = [0, 0, 0]
DEFAULT_STEP_SIZE = float(1)
DEFAULT_WORLD = "G4_Galactic" #default material of the world volume
DEFAULT_SAMPLE = "Water3ppmPt"   #default material of the sample volume
DEFAULT_FILE_NAME = "prestep"
DEFAULT_BEAM_ENERGY = 130
DEFAULT_ACTOR = "VoxelizedPromptGammaAnalogActor"

path = utility.get_default_test_paths(__file__, output_folder=DEFAULT_OUTPUT)

def opengate_run(
    output=DEFAULT_OUTPUT,
    job_id=0,
    number_of_particles=DEFAULT_NUMBER_OF_PARTICLES,
    visu=True, 
    verbose=True,
    polarization=False,
    energy_type=False,
    world=DEFAULT_WORLD,
    sample_material=DEFAULT_SAMPLE,
    File_name=DEFAULT_FILE_NAME,
    collimation=False,
    energy = DEFAULT_BEAM_ENERGY,
    position=DEFAULT_POSITION,
    actor = DEFAULT_ACTOR,
     ):

    if verbose:
        print(f"Running MC… " + str(locals())) #locals = variable locales soit les paramètres de la fonction

        # Call the simulation function and retrieve sim and simulation_parameters
    sim, ct, vpg_actor, source = simulation(output, File_name, job_id, number_of_particles, visu, verbose, actor)

    sim.run()
    
    #visualization
    # === Charger le fichier VRML avec PyVista ===
    """print("📂 Chargement du fichier VRML pour affichage...")
    pl = pv.Plotter()
    pl.import_vrml("simulation.wrl")  # Charger la scène OpenGATE

    # === Ajouter des axes colorés pour l'orientation ===
    axes = pv.Axes()
    axes.axes_actor.total_length = [1, 1, 1]  # Taille des axes
    axes.axes_actor.x_axis_shaft_properties.color = (1, 0, 0)  # Rouge pour X
    axes.axes_actor.y_axis_shaft_properties.color = (0, 1, 0)  # Vert pour Y
    axes.axes_actor.z_axis_shaft_properties.color = (0, 0, 1)  # Bleu pour Z
    pl.add_actor(axes.axes_actor)

    # === Paramètres d'affichage ===
    pl.background_color = "black"  # Fond noir pour meilleur contraste
    pl.show_grid()  # Afficher une grille
    pl.show()  # Afficher la scène 3D"""

    
def itk_merge(
    output=DEFAULT_OUTPUT,
    verbose=False,
    File_name=DEFAULT_FILE_NAME,
    number_of_jobs=DEFAULT_NUMBER_OF_JOBS,
):
    def print_verbose(*args, **kwargs):
        if verbose:
            print(*args, **kwargs)
    if not os.path.exists(output):
        os.makedirs(output)
    if number_of_jobs == 1 : 
        print_verbose("Skipping merge, only one job was run.")
        return
    try:
        # Find all .nii.gz files matching the pattern
        file_pattern = os.path.join(f"/home/vguittet/Documents/G10/stage1.5/output/{output}/{File_name}_*.nii.gz")
        file_list = sorted(glob.glob(file_pattern))  # Get all matching files
        count = number_of_jobs
        if not file_list:
            raise FileNotFoundError(f"No .nii.gz files found matching pattern: {file_pattern}")
        actor_list = []
        type_list = []
        for file_path in file_list:
            base_name = os.path.basename(file_path)
            actor_name = base_name.split("_")[1]
            type_name = base_name.split("_")[3] + "_" + base_name.split("_")[4]  # e.g., neutr_e
            if actor_name not in actor_list:
                actor_list.append(actor_name)
            if type_name not in type_list:
                type_list.append(type_name)
            init = itk.imread(path.output/f"{File_name}_{actor_list[0]}_1_{type_list[0]}")
            init_arr = itk.array_from_image(init)
            merged_array = np.zeros_like(init_arr, dtype=np.float32) 
            for type_name in type_list:
                for actor_name in actor_list:
                    merged_array.fill(0) # Initialize the merged array
                    for i in range(count):
                        file_path = path.output/f"{File_name}_{actor_name}_{i + 1}_{type_name}"
                         # Check if the file exists
                        if not os.path.exists(file_path):
                            print(f"File not found: {file_path}")
                            continue
                        image = itk.imread(file_path)
                        array = itk.array_from_image(image)
                        merged_array = merged_array + array / count  # Accumulate the pixel values
                    merged_image = itk.image_from_array(merged_array)
                    merged_image.CopyInformation(init)  # Copy metadata from the initial image
                    output_file = path.output/f"{File_name}_{actor_name}_merged_{type_name}"
                    print_verbose(f"Saving merged image to: {output_file}")
                    itk.imwrite(merged_image, output_file)  
                    

    except FileNotFoundError as e:
        print(e)

def opengate_pool_run(
    output,
    number_of_jobs, #mettre autant que de positions sinon on ne simule pas toutes les particules
    number_of_particles,
    visu,
    verbose,
    polarization,
    energy_type,
    world,
    sample_material,
    File_name,
    collimation,
    energy,
    #step,
    #size,
):

    with Pool(maxtasksperchild=1) as pool:

        results = []
        
        
        number_of_particles_per_job = int(number_of_particles / number_of_jobs)
        mm = gate.g4_units.mm
        um = gate.g4_units.um
        cm = gate.g4_units.cm
        position = [0, 0, 20*cm] #position initiale à 30um -> trop proche de la source
        #delta_x = 0.1*mm #pas du raster scan pour passer d'un pixel à l'autre
        #delta_x = step*mm
        #delta_y = -step*mm
        job_id = 0
        #image_size = size

        """ for y in range(image_size) : #lignes
            for x in range(image_size) : #colonnes
                job_id += 1
                 # Calcule la nouvelle position à partir de la base
                position = [
                    x * delta_x,
                    y * delta_y,
                    position[2]
                ] 
                #le carré décrit est balayé de gauche à droite et de haut en bas
                
                copied_position = position.copy()
                print(f"launching job #{job_id}/{number_of_jobs} with position x={copied_position[0]/mm:.2f} mm, y={copied_position[1]/mm:.2f} mm")

                result = pool.apply_async(opengate_run, kwds={
                'output': output,
                'job_id': job_id, 
                'number_of_particles': number_of_particles_per_job,
                'visu': visu,
                'verbose': verbose,
                'position': copied_position
                #'position' : position 
                })
                results.append(result)"""



        
        for i in range(number_of_jobs):
            
                job_id = i+1
                #copied_position = position.copy()
                print(f"launching job #{job_id}/{number_of_jobs}")
                #print(f"launching job #{job_id}/{number_of_jobs} with position x={copied_position[0]/mm:.2f} mm")
                result = pool.apply_async(opengate_run, kwds={
                'output': output,
                'job_id': job_id, 
                'number_of_particles': number_of_particles_per_job,
                'visu': visu,
                'verbose': verbose,
                'position' : position,
                'polarization': polarization,
                'energy_type': energy_type,
                'world' : world,
                'sample_material' : sample_material,
                'File_name': File_name,
                'collimation' : collimation,
                'energy' : energy,
                #'position' : copied_position,
                })
                results.append(result)
                #position[0] += delta_x

            
        

        pool.close()
        pool.join()

        for result in results:
            result.wait()
            if not result.successful():
                print("Failure in MC simulation")
                exit(1)





    itk_merge(
        output=output,
        verbose=verbose,
        File_name=File_name,
        number_of_jobs=number_of_jobs,
    )
                
def main():

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--output', help="Path of outputs", default=DEFAULT_OUTPUT)
    parser.add_argument('-j', '--number-of-jobs', help="Number of jobs", default=DEFAULT_NUMBER_OF_JOBS, type=int)
    parser.add_argument('-n', '--number-of-particles', help="Number of generated particles (total)", default=DEFAULT_NUMBER_OF_PARTICLES, type=float)
    parser.add_argument('--visu', help="Visualize Monte Carlo simulation", default=False, action='store_true')
    parser.add_argument('--verbose', '-v', help="Verbose execution", default=False, action='store_true')
    parser.add_argument('-p', '--polarization', help="Polarization of the beam", default=False, action='store_true')
    parser.add_argument('--energy_type', help="Type of energy distribution", default=False, action='store_true')#True active le mode polychromatique, rendre la commande plus clair après
    parser.add_argument('-w', '--world', help="World's material", default=DEFAULT_WORLD, type=str)#pas besoin de mettre les guillemets au moment de la commande
    parser.add_argument('-s', '--sample_material', help="sample's material", default=DEFAULT_SAMPLE, type=str)
    parser.add_argument('-f', '--File_name', help="name of the output file", default=DEFAULT_FILE_NAME, type=str)
    parser.add_argument('-c', '--collimation', help="collimation of the beam", default=False, action='store_true')
    parser.add_argument('-e', '--energy', help="Energy of the beam in keV", default=DEFAULT_BEAM_ENERGY, type= int)
    #parser.add_argument('-step', '--step', help="size of a step between two succesive positions en mm", default=DEFAULT_STEP_SIZE, type=float)
    #parser.add_argument('-size', '--size', help="number of pixels in lines/columns", default=DEFAULT_STEP_SIZE, type=int)
    #parser.add_argument('-pos', '--number-of-positions', help="Number of positions to simulate", default=DEFAULT_NUMBER_OF_POSITIONS, type=int)
    #argument position initiale ?     
    #argument pour le nombre de position à couvrir (taille de l'image à balayer en gros)
    args_info = parser.parse_args()

    opengate_pool_run(**vars(args_info))
    #opengate_run(output, 1, number_of_particles, visu, verbose)
if __name__ == '__main__':
    main()
