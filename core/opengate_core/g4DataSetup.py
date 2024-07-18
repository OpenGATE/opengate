import os
import shutil
import tarfile
import platform
import sys
import requests
from time import sleep

# Data for Geant4
# Geant4 11.2.1
data_packages = [
    "https://cern.ch/geant4-data/datasets/G4NDL.4.7.tar.gz",
    "https://cern.ch/geant4-data/datasets/G4EMLOW.8.5.tar.gz",
    "https://cern.ch/geant4-data/datasets/G4PhotonEvaporation.5.7.tar.gz",
    "https://cern.ch/geant4-data/datasets/G4RadioactiveDecay.5.6.tar.gz",
    "https://cern.ch/geant4-data/datasets/G4PARTICLEXS.4.0.tar.gz",
    "https://cern.ch/geant4-data/datasets/G4PII.1.3.tar.gz",
    "https://cern.ch/geant4-data/datasets/G4RealSurface.2.2.tar.gz",
    "https://cern.ch/geant4-data/datasets/G4SAIDDATA.2.0.tar.gz",
    "https://cern.ch/geant4-data/datasets/G4ABLA.3.3.tar.gz",
    "https://cern.ch/geant4-data/datasets/G4INCL.1.2.tar.gz",
    "https://cern.ch/geant4-data/datasets/G4ENSDFSTATE.2.3.tar.gz",
]


def check_g4_data():
    # check if the G4 data folder is there
    dataLocation = get_g4_data_folder()
    if not os.path.exists(dataLocation):
        print("Geant4 data folder does not exist.")
        print("I will create it for you here: " + dataLocation)
        print("... and download the G4 data.")
        print("This will take a moment.")
        download_g4_data()
        print("")
        print("Done")
        return
    else:
        # Check if the G4 data folder is up to date
        consistent = check_consistency_g4_data_folders()
        if consistent is False:
            print("\nI will download a fresh G4 dataset for you.")
            print("This will take a moment.")
            download_g4_data()
            if check_consistency_g4_data_folders() is True:
                print("\nGeant4 data has been set up successfully.")
            else:
                print("There is (still) a problem with the Geant4 data.")
                print("Possibly, some data are missing.")


def download_with_resume(url, out, retries=5, delay=10):
    temp_file = out + ".part"
    headers = {}
    if os.path.exists(temp_file):
        file_size = os.path.getsize(temp_file)
        headers["Range"] = f"bytes={file_size}-"

    for attempt in range(retries):
        try:
            with requests.get(url, headers=headers, stream=True) as r:
                r.raise_for_status()
                with open(temp_file, "ab") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            os.rename(temp_file, out)
            print(f"Downloaded {url} successfully.")
            return
        except requests.exceptions.RequestException as e:
            print(f"Download attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                print(f"Retrying in {delay} seconds...")
                sleep(delay)
            else:
                print(f"Exceeded maximum retries for {url}.")
                raise e


# Download Geant4 data:
def download_g4_data():
    data_location = get_g4_data_folder()
    if not os.path.exists(data_location):
        os.mkdir(data_location)
    folder_names_from_tar = set()
    for i, package in enumerate(data_packages):
        print(f"\nDownloading {i + 1}/{len(data_packages)} {package}")

        # download the archive (with resume if the connexion failed)
        package_archive = package.split("/")[-1]
        out = os.path.join(data_location, package_archive)
        download_with_resume(package, out)
        # packageArchive = wget.download(package, out=dataLocation)
        package_archive = out

        with tarfile.open(package_archive) as tar:
            # extract the base folder from the tar archive
            # into which the G4 data will be extracted
            extract_to_folder = sorted(tar.getnames(), key=lambda n: len(n))[0]
            folder_names_from_tar.update([extract_to_folder])
            extract_to_path = os.path.join(data_location, extract_to_folder)
            # remove the directory into which tar wants extract if it
            # already exists to avoid permission error
            if os.path.exists(extract_to_path):
                print(f"\nNeed to extract into {extract_to_path},")
                print("but that directory already exists.")
                print("I need to remove it.")
                shutil.rmtree(os.path.join(data_location, extract_to_folder))
            print("Extracting the data archive (tar) ...")
            tar.extractall(path=data_location)
            print("done")
        os.remove(package_archive)
    check_for_non_required_files_folders()


def check_for_non_required_files_folders():
    """Check if there are old data folders and inform the user."""
    dataLocation = get_g4_data_folder()
    required_paths = set(get_g4_data_paths().values())
    existing_paths = set(
        [os.path.join(dataLocation, f) for f in os.listdir(dataLocation)]
    )
    outdated_paths = existing_paths.difference(required_paths)
    if len(outdated_paths) > 0:
        print("\n" + 10 * "*")
        print(f"The following files and folders in {dataLocation}")
        print(f"are not required and can be safely deleted:\n")
        for f in outdated_paths:
            print(os.path.basename(f))
        print("\n" + 10 * "*")


def check_consistency_g4_data_folders():
    dataLocation = get_g4_data_folder()
    required_paths = set(get_g4_data_paths().values())
    existing_paths = set(
        [os.path.join(dataLocation, f) for f in os.listdir(dataLocation)]
    )
    missing_paths = required_paths.difference(existing_paths)
    if len(missing_paths) > 0:
        print("\nSome Geant4 data folder seem to be missing, namely:")
        for p in missing_paths:
            print(p)
        return False
    else:
        return True


# Return Geant4 data folder:
def get_g4_data_folder():
    packageLocation = os.path.dirname(os.path.realpath(__file__))
    dataLocation = os.path.join(packageLocation, "geant4_data")
    return dataLocation


# Return Geant4 data path:
def get_g4_data_paths():
    dataLocation = get_g4_data_folder()
    # 11.1
    g4_data_path = {
        "G4NEUTRONHPDATA": os.path.join(dataLocation, "G4NDL4.7"),
        "G4LEDATA": os.path.join(dataLocation, "G4EMLOW8.5"),
        "G4LEVELGAMMADATA": os.path.join(dataLocation, "PhotonEvaporation5.7"),
        "G4RADIOACTIVEDATA": os.path.join(dataLocation, "RadioactiveDecay5.6"),
        "G4PARTICLEXSDATA": os.path.join(dataLocation, "G4PARTICLEXS4.0"),
        "G4PIIDATA": os.path.join(dataLocation, "G4PII1.3"),
        "G4REALSURFACEDATA": os.path.join(dataLocation, "RealSurface2.2"),
        "G4SAIDXSDATA": os.path.join(dataLocation, "G4SAIDDATA2.0"),
        "G4ABLADATA": os.path.join(dataLocation, "G4ABLA3.3"),
        "G4INCLDATA": os.path.join(dataLocation, "G4INCL1.2"),
        "G4ENSDFSTATEDATA": os.path.join(dataLocation, "G4ENSDFSTATE2.3"),
    }
    return g4_data_path


# Set Geant4 data paths:
def set_g4_data_path():
    g4_data_path = get_g4_data_paths()
    for key, value in g4_data_path.items():
        os.environ[key] = value
    s = platform.system()
    g4_lib_folder = None

    if s == "Linux" or s == "Windows":
        g4_lib_folder = os.path.join(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "..", "opengate_core.libs"
            )
        )
    elif s == "Darwin":
        g4_lib_folder = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), ".dylibs"
        )

    if s == "Windows":
        os.add_dll_directory(g4_lib_folder)
    else:
        sys.path.append(g4_lib_folder)

    if not "LD_LIBRARY_PATH" in os.environ:
        os.environ["LD_LIBRARY_PATH"] = ""
    os.environ["LD_LIBRARY_PATH"] = g4_lib_folder + ":" + os.environ["LD_LIBRARY_PATH"]
