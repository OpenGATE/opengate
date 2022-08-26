import os
import sys
import git
import shutil


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
            folderGit = git.Repo(dataLocation)
            sha = folderGit.head.object.hexsha
            if not str(sha) == checkoutReferenceDataGit:
                shutil.rmtree(dataLocation)
                print("No correct Opengate test data version in: " + dataLocation)
                print("I update it for you.")
                download_tests_data(dataLocation)
                print("")
                print("Done")


# Download opengate tests data:
def download_tests_data(dataLocation):
    os.mkdir(dataLocation)
    f = open(os.path.join(dataLocation, "..", "HEAD"), "r")
    checkoutDataGit = str(f.readline()).strip()
    folderGit = git.Git(dataLocation)
    folderGit.clone(
        "https://gitlab.in2p3.fr/opengamgate/gam_tests_data.git", dataLocation
    )
    folderGit.checkout(checkoutDataGit)


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
