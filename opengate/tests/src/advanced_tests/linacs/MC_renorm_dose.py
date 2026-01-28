import numpy as np
import matplotlib.pyplot as plt
import itk
import os,sys,glob
import opengate
from opengate.contrib.linacs import dicomrtplan as rtplan
from box import Box
import click
import json
import pymedphys



def isocenter_area_norm_factor(array,isocenter_idx,size):
    sum_voxel_area = np.sum(array[isocenter_idx[0] - int(size/2):isocenter_idx[0] + int(size/2) + 1,isocenter_idx[1] - int(size/2):isocenter_idx[1] + int(size/2) + 1,isocenter_idx[2] - int(size/2):isocenter_idx[2] + int(size/2) + 1])
    return sum_voxel_area


def read_mhd_img(img_name,return_img_dim=False):
    img = itk.imread(img_name)
    array= itk.GetArrayFromImage(img)
    if not return_img_dim:
        return array,img
    else :
        offset = np.array(img.GetOrigin())
        dim = np.array(img.GetLargestPossibleRegion().GetSize())
        spacing = np.array(img.GetSpacing())
        return array,img,[offset,dim,spacing]


class MC_img:

    def __init__(self,name,array,header,**kwargs):
        self.array = array
        if "img" in kwargs.keys():
            self.img = kwargs["img"]
        self.name = name
        if type(header) == list:
            self.header = Box({"offset": header[0], "dim": header[1], "spacing": header[2]})
        else :
            self.header = header
        self.img_to_norm = []


    def add_array_to_norm(self,name,array,img):
        new_img = MC_img(name,array,self.header,img = img)
        self.img_to_norm.append(new_img)

    def add_norm_factor(self,isocenter):
        pos_isocenter = np.array(((isocenter - self.header.offset) / self.header.spacing), dtype=int)[::-1]

        self.norm = isocenter_area_norm_factor(self.array, pos_isocenter, 11)
        print("isocenter:",pos_isocenter, "name:", self.name,"norm factor:",self.norm)


@click.command()
@click.option('--path', default="./data", help='path to the patient folder')
def norm_img(path):
    the_path = path
    init_path = os.getcwd()
    folder_list = [the_path]
    for the_path in folder_list:
        os.chdir(init_path)
        os.chdir(the_path)

        mask_name = "mask.mhd"
        TPS_name = "TPS.mhd"
        rt_plan_path = "rt_plan.dcm"
        rt_plan_parameters = rtplan.read(rt_plan_path,"all_cp")
        isocenter = rt_plan_parameters["isocenter"][0]

        list_of_simulated_data = []

        name_tle_MC_img = "../output/MC-tle-dose.mhd"
        name_MC_img = "../output/MC-dose.mhd"
        mask_img = itk.imread(mask_name)
        mask_array = itk.GetArrayFromImage(mask_img)


        if os.path.isfile( name_tle_MC_img):
            array_MC,img_MC,headers_MC= read_mhd_img( name_tle_MC_img,return_img_dim=True)
            array_MC = MC_img("tle_all", array_MC, headers_MC)
            array_MC.array *= mask_array
            array_MC.add_array_to_norm(name_tle_MC_img, array_MC.array,img=img_MC)
            array_MC.add_norm_factor(isocenter)
            list_of_simulated_data.append(array_MC)


        if os.path.isfile( name_MC_img):
            array_MC,img_MC,headers_MC= read_mhd_img( name_MC_img,return_img_dim=True)
            array_MC = MC_img("all", array_MC, headers_MC)
            array_MC.array *= mask_array
            array_MC.add_array_to_norm(name_MC_img,array_MC.array,img=img_MC)
            array_MC.add_norm_factor(isocenter)
            list_of_simulated_data.append(array_MC)



        array_TPS,img_TPS,headers_TPS = read_mhd_img(TPS_name,return_img_dim=True)
        array_TPS = MC_img(TPS_name,array_TPS,headers_TPS)
        array_TPS.add_norm_factor(isocenter)


        TPS_norm_factor = array_TPS.norm
        for MC_array in list_of_simulated_data:
            norm_factor = MC_array.norm
            arrays_to_norm = MC_array.img_to_norm
            for array_to_norm in arrays_to_norm:
                array_name = array_to_norm.name
                normed_array = array_to_norm.array * TPS_norm_factor/norm_factor
                normed_img = itk.GetImageFromArray(normed_array)
                normed_img.CopyInformation(array_to_norm.img)
                itk.imwrite(normed_img, array_name[:-8] + "norm-dose.mhd")
                img_err_MC = itk.imread( array_name[:-4] + "-uncertainty.mhd")
                itk.imwrite(img_err_MC,  array_name[:-8] + "norm-dose-uncertainty.mhd")

if __name__ == '__main__':
    norm_img()


