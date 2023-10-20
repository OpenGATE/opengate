import os
import sys
import shutil
import wget
import json
import zipfile
import requests
import colored

try:
    color_error = colored.fg("red") + colored.attr("bold")
except AttributeError:
    # new syntax in colored>=1.5
    color_error = colored.fore("red") + colored.style("bold")


# Check and download opengate tests data if not present:
def check_tests_data_folder():
    dataLocation = get_tests_data_folder()
    if not os.path.exists(dataLocation):
        print("No Opengate test data available in: " + dataLocation)
        print("I download it for you.")
        download_tests_data(dataLocation)
        print("")
        print("Done")
    else:
        # Check if the commit is correct if file HEAD is present
        if os.path.isfile(os.path.join(dataLocation, "..", "HEAD")):
            f = open(os.path.join(dataLocation, "..", "HEAD"), "r")
            checkoutReferenceDataGit = str(f.readline()).strip()
            if os.path.isfile(os.path.join(dataLocation, "sha.log")):
                f = open(os.path.join(dataLocation, "sha.log"), "r")
                checkoutRealDataGit = str(f.readline()).strip()
                if not checkoutReferenceDataGit == checkoutRealDataGit:
                    shutil.rmtree(dataLocation)
                    print("No correct Opengate test data version in: " + dataLocation)
                    print("I update it for you.")
                    download_tests_data(dataLocation)
                    print("")
                    print("Done")
            else:
                shutil.rmtree(dataLocation)
                print("No Opengate test data available in: " + dataLocation)
                print("I download it for you.")
                download_tests_data(dataLocation)
                print("")
                print("Done")
        # Check if the size of one .raw file is correct to detect lfs
        if "ct_4mm.raw" in os.listdir(dataLocation):
            filesize = os.stat(os.path.join(dataLocation, "ct_4mm.raw")).st_size
            if filesize < 4000000:
                print(
                    "It seems the test data in: "
                    + dataLocation
                    + " do not have the correct size"
                )
                print("Maybe you do not have git-lfs. Execute this:")
                print("Install git-lfs from https://git-lfs.com/")
                print("cd " + dataLocation)
                print("git-lfs pull")
                return False
        else:  # if the file is not present
            print(
                colored.stylize(
                    "The data are not present in: " + dataLocation,
                    color_error,
                )
            )
            print("Download them with:")
            print("git submodule update --init --recursive")
            return False
    return True


# Download opengate tests data:
def download_tests_data(dataLocation):
    os.mkdir(dataLocation)
    f = open(os.path.join(dataLocation, "..", "HEAD"), "r")
    checkoutDataGit = str(f.readline()).strip()
    url = (
        "https://gitlab.in2p3.fr/api/v4/projects/15155/repository/commits/"
        + checkoutDataGit
    )
    r = requests.get(url=url)
    js = r.json()
    idPipeline = str(js["last_pipeline"]["id"])
    url = (
        "https://gitlab.in2p3.fr/api/v4/projects/15155/pipelines/"
        + idPipeline
        + "/jobs"
    )
    r = requests.get(url=url)
    js = r.json()[0]
    idPipeline = str(js["id"])
    url = (
        "https://gitlab.in2p3.fr/api/v4/projects/15155/jobs/"
        + idPipeline
        + "/artifacts"
    )
    filename = wget.download(url)
    if filename == checkoutDataGit + ".zip":
        with zipfile.ZipFile(filename, "r") as zip_ref:
            zip_ref.extractall(dataLocation)
    os.remove(filename)
    with zipfile.ZipFile(
        os.path.join(dataLocation, "artifact_zip", checkoutDataGit + ".zip"), "r"
    ) as zip_ref:
        zip_ref.extractall(dataLocation)
    shutil.rmtree(os.path.join(dataLocation, "artifact_zip"))


# Return opengate tests data folder:
def get_tests_data_folder():
    packageLocation = os.path.dirname(os.path.realpath(__file__))
    dataLocation = ""
    if os.path.exists(os.path.join(packageLocation, "..", "opengate")):
        dataLocation = os.path.join(packageLocation, "..", "opengate", "tests", "data")
    elif os.path.exists(os.path.join(packageLocation, "..", "..", "opengate")):
        dataLocation = os.path.join(
            packageLocation, "..", "..", "opengate", "tests", "data"
        )
    else:
        print("Cannot find opengate folder near: " + packageLocation)
    return dataLocation
