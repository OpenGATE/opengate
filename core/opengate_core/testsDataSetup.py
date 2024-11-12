import os
import shutil
import zipfile
import requests
import colored
from pathlib import Path
from .g4DataSetup import *

color_error = colored.fore("red") + colored.style("bold")


# Check and download opengate tests data if not present:
def check_tests_data_folder():
    data_location = get_tests_data_folder()
    if not data_location.exists():
        print("No Opengate test data available in: " + str(data_location))
        print("I download it for you.")
        download_tests_data(data_location)
        print("")
        print("Done")
    else:
        # Check if the commit is correct if file HEAD is present
        if (data_location.parent / "HEAD").exists():
            with (data_location.parent / "HEAD").open("r") as f:
                checkout_reference_data_git = f.readline().strip()
            if (data_location / "sha.log").exists():
                with (data_location / "sha.log").open("r") as f:
                    checkout_real_data_git = f.readline().strip()
                if checkout_reference_data_git != checkout_real_data_git:
                    shutil.rmtree(data_location)
                    print(
                        "No correct Opengate test data version in: "
                        + str(data_location)
                    )
                    print("I update it for you.")
                    download_tests_data(data_location)
                    print("")
                    print("Done")
            else:
                shutil.rmtree(data_location)
                print("No Opengate test data available in: " + str(data_location))
                print("I download it for you.")
                download_tests_data(data_location)
                print("")
                print("Done")
        # Check if the size of one .raw file is correct to detect lfs
        if (data_location / "ct_4mm.raw").is_file():
            filesize = (data_location / "ct_4mm.raw").stat().st_size
            if filesize < 4000000:
                print(
                    "It seems the test data in: "
                    + str(data_location)
                    + " do not have the correct size"
                )
                print("Maybe you do not have git-lfs. Execute this:")
                print("Install git-lfs from https://git-lfs.com/")
                print("cd " + str(data_location))
                print("git-lfs pull")
                return False
        else:  # if the file is not present
            print(
                colored.stylize(
                    "The data are not present in: " + str(data_location),
                    color_error,
                )
            )
            print("Download them with:")
            print("git submodule update --init --recursive")
            return False
    return True


# Download opengate tests data:
def download_tests_data(data_location: Path):
    data_location.mkdir(parents=True, exist_ok=True)
    with (data_location.parent / "HEAD").open("r") as f:
        checkout_data_git = str(f.readline()).strip()
    url = (
        "https://gitlab.in2p3.fr/api/v4/projects/15155/repository/commits/"
        + checkout_data_git
    )
    r = requests.get(url=url)
    js = r.json()
    id_pipeline = str(js["last_pipeline"]["id"])
    url = (
        "https://gitlab.in2p3.fr/api/v4/projects/15155/pipelines/"
        + id_pipeline
        + "/jobs"
    )
    r = requests.get(url=url)
    js = r.json()[0]
    id_pipeline = str(js["id"])
    url = (
        "https://gitlab.in2p3.fr/api/v4/projects/15155/jobs/"
        + id_pipeline
        + "/artifacts"
    )

    # download the archive (with resume if the connexion failed)
    filename = url.split("/")[-1]
    out = data_location / filename
    download_with_resume(url, out)

    if filename == "artifacts":
        with zipfile.ZipFile(data_location / filename, "r") as zip_ref:
            zip_ref.extractall(data_location)
    os.remove(data_location / filename)

    with zipfile.ZipFile(
        data_location / "artifact_zip" / f"{checkout_data_git}.zip",
        "r",
    ) as zip_ref:
        zip_ref.extractall(str(data_location))
    shutil.rmtree(data_location / "artifact_zip", ignore_errors=True)


# Return opengate tests data folder:
def get_tests_data_folder() -> Path:
    package_location = Path(__file__).resolve().parent
    data_location = package_location.parent / "opengate" / "tests" / "data"
    for parent in package_location.parents:
        if (parent / "opengate").exists():
            data_location = parent / "opengate" / "tests" / "data"
            break
    if not data_location:
        print("Cannot find opengate folder near: " + str(package_location))
    return data_location
