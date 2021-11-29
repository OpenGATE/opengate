import site
import os

def return_site_packages_dir():
    site_package = [p for p  in site.getsitepackages()
                    if "site-packages" in p][0]
    return(site_package)

def get_site_packages_dir():
    print(return_site_packages_dir())

def get_libG4processes_path():
    for element in os.listdir(os.path.join(return_site_packages_dir(), "gam_g4.libs")):
        if "libG4processes" in element:
            print(os.path.join(return_site_packages_dir(), "gam_g4.libs", element))

def get_libG4geometry_path():
    for element in os.listdir(os.path.join(return_site_packages_dir(), "gam_g4.libs")):
        if "libG4geometry" in element:
            print(os.path.join(return_site_packages_dir(), "gam_g4.libs", element))

