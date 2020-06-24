# Copyright (C) 2019-2020 HERE Global B.V. and its affiliate(s).
# All rights reserved.
#
# This software and other materials contain proprietary information
# controlled by HERE and are protected by applicable copyright legislation.
# Any use and utilization of this software and other materials and
# disclosure to any third parties is conditional upon having a separate
# agreement with HERE for the access, use, utilization or disclosure of this
# software. In the absence of such agreement, the use of the software is not
# allowed.

"""This script is used to verify prerequisites for SDK, install and update the HERE OLP SDK for Python"""

import argparse
import json
import os
from os.path import exists, join, islink, isfile
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib
import zipfile
from shutil import which
from stat import S_IREAD
import atexit
from http.client import HTTPSConnection
from base64 import b64encode
import ssl
from textwrap import dedent

# Setting up some global variables
ENV_NAME = ""
# Minimum comptable conda version
MIN_REQ_CONDA_VERSION = "3.0.0"
SDK_VERSION = "1.5"
HOME = str(os.path.expanduser("~"))
FNULL = open(os.devnull, "w")
ARTIFACTORY_USER = ""
ARTIFACTORY_PASSWORD = ""
_CONDARC_FILE = ""
RUNNING_WINDOWS = True if "Windows" in platform.system() else False
ENV_ACTIVE = False

if not RUNNING_WINDOWS:
    _M2_SETTINGS_FILE = HOME + "/.m2/settings.xml"
    _IVY_SETTINGS_FILE = HOME + "/.here/ivy.settings.xml"

else:
    env_name = subprocess.check_output(
        ["echo", "%CONDA_DEFAULT_ENV%"], shell=True
    ).decode("utf8")
    if env_name != "base":
        ENV_ACTIVE = True
    _M2_SETTINGS_FILE = HOME + "\.m2\settings.xml"
    _IVY_SETTINGS_FILE = HOME + "\.here\ivy.settings.xml"

DESC = "This script is used to verify prerequisites for SDK, install and update the HERE OLP SDK for Python."

# argparse setup #
parser = argparse.ArgumentParser(description=DESC)
parser.add_argument(
    "-v",
    "--verify",
    action="store_true",
    help="To verify prerequisites for installing HERE OLP SDK for Python",
)
parser.add_argument(
    "-i",
    "--install",
    nargs="?",
    default=str(SDK_VERSION),
    help="version of SDK to be installed",
    const=str(SDK_VERSION),
    metavar="version",
)
parser.add_argument(
    "-n",
    "--name",
    help="Name of the conda environment to be created",
    metavar="NAME_OF_CONDA_ENV",
)
parser.add_argument(
    "-u",
    "--update",
    help=f"Update SDK to a specific version, default values for this parameter is {SDK_VERSION}, i.e the latest version of SDK",
    metavar="version",
    nargs="?",
    const=str(SDK_VERSION),
)
args = parser.parse_args()


def main():
    global ENV_NAME
    global SDK_VERSION
    global args
    call_install = False

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # If user wants just wants to verify
    if args.verify:
        validate_environment()
        sys.exit(0)

    # If user wants to update a specific conda environment
    if args.update:
        if args.name:

            if args.name == "":
                print(
                    "Please use --name or -n to pass the name of the conda environment"
                )
                sys.exit(1)

            if args.update != "":
                SDK_VERSION = args.update
            ENV_NAME = args.name
            update(ENV_NAME, SDK_VERSION)
            sys.exit(0)
        else:
            print("Please use --name or -n to pass the name of the conda environment")
            sys.exit(1)

    # If user has set install parameter then set the appropriate version if user has passed version along with it
    if args.install:
        call_install = True
        if args.install != "":
            SDK_VERSION = args.install

    # If user has set environment name parameter then set the appropriate environment name if user has passed
    # environment name along with it
    if args.name:
        ENV_NAME = args.name
    else:
        ENV_NAME = f"olp-sdk-for-python-{SDK_VERSION}-env"

    ENV_NAME = str(ENV_NAME)

    # Call to install function
    if call_install:
        install()
        sys.exit(0)


def update(env_name, sdk_version):
    """
    Update the SDK with the version set by user in the specified conda environment.
    """

    validate_environment()
    read_repo_credentials()
    check_condarc_file()
    download_config_files(sdk_version)
    print(f"Updating conda environment '{env_name}' to version '{sdk_version}'")

    if not RUNNING_WINDOWS:
        cmd = [
            f"source $(conda info --base)/etc/profile.d/conda.sh && conda activate {env_name} && conda env update -n {env_name} -f tmp/conda-env-files/olp_sdk_for_python_env.yml"
        ]
    else:
        if ENV_ACTIVE:
            cmd = [
                "conda",
                "deactivate",
                "&&",
                "conda",
                "activate",
                env_name,
                "&&",
                "conda",
                "env",
                "update",
                "-n",
                env_name,
                "-f",
                "tmp/conda-env-files/olp_sdk_for_python_env.yml",
            ]
        else:
            cmd = [
                "conda",
                "activate",
                env_name,
                "&&",
                "conda",
                "env",
                "update",
                "-n",
                env_name,
                "-f",
                "tmp/conda-env-files/olp_sdk_for_python_env.yml",
            ]

    r = subprocess.call(cmd, stdout=FNULL, shell=True)
    if r != 0:
        print(
            f"There was some issue while updating conda environment '{env_name}' to version '{sdk_version}' please find the above error"
        )
    else:
        print(
            f"Completed updating conda environment '{env_name}' to version '{sdk_version}' !!!"
        )

    clean_up_tmp()


def install():
    """
    Install the SDK with the version set by user in the specified conda environment.
    """
    print(f"Installing version '{SDK_VERSION}' in conda environment '{ENV_NAME}'")
    validate_environment()
    read_repo_credentials()
    download_config_files(SDK_VERSION)
    init_environment()
    if "Windows" in platform.system():
        post_installation()
    check_after_install_files_requirement()
    clean_up_tmp()


def download_config_files(sdk_version):
    """
    Download the conda-env-files.zip for the appropriate version specified by the user.
    """

    ssl._create_default_https_context = ssl._create_unverified_context
    print("Downloading configuration file ...")
    conn = HTTPSConnection("repo.platform.here.com")
    payload = ""
    file_url = f"/artifactory/open-location-platform/com/here/platform/analytics/sdk/oasp/{sdk_version}/conda-env-files.zip"
    file_download_location = join(os.getcwd().rstrip(), "tmp")
    os.makedirs(file_download_location, exist_ok=True)
    start = time.time()
    user_and_pass = b64encode(
        f"{ARTIFACTORY_USER}:{ARTIFACTORY_PASSWORD}".encode("utf-8")
    ).decode("ascii")
    headers = {"Authorization": "Basic %s" % user_and_pass}
    conn.request("GET", file_url, payload, headers)
    res = conn.getresponse()
    with open(join(file_download_location, "conda-env-files.zip"), "wb") as f:
        shutil.copyfileobj(res, f)
    end = time.time()
    download_time = end - start
    if res.status == 404:
        print(f"Release version {sdk_version} cannot be found.")
        sys.exit(1)
    if 400 <= res.status:
        print(
            "There was an error while downloading configuration files. Please check the version provided or verify all "
            "the credentials files are correct. "
        )
        sys.exit(1)
    with zipfile.ZipFile(
        join(file_download_location, "conda-env-files.zip"), "r"
    ) as zip_ref:
        zip_ref.extractall(join(os.getcwd().rstrip(), "tmp"))
    print(f"Time taken to download the file: {download_time} secs.")
    print("Completed downloading configuration file ...")


def post_installation():
    """
    Function to execute all the steps of post-installation.bat file (only for Windows).
    """

    output = subprocess.check_output(["conda", "env", "list"], shell=True).decode(
        "utf8"
    )
    conda_prefix = re.findall(f"^base\s\s*(.*)", output, re.MULTILINE)[0]
    conda_prefix = conda_prefix.replace(" ", "").replace("*", "").strip()

    conda_prefix = f"{conda_prefix}/envs/{ENV_NAME}"

    if exists(f"{conda_prefix}/etc/conda/activate.d/env_vars.bat"):
        os.unlink(f"{conda_prefix}/etc/conda/activate.d/env_vars.bat")

    # Check nagini version
    nagini_version = str(
        json.loads(
            re.search(
                "\[([^\]]*)\]",
                subprocess.check_output(
                    [
                        "conda",
                        "activate",
                        ENV_NAME,
                        "&&",
                        "conda",
                        "list",
                        "nagini",
                        "--json",
                    ],
                    shell=True,
                ).decode("utf8"),
            ).group()
        )[0]["version"]
    ).rstrip()

    # Check emr version
    emr_version = str(
        json.loads(
            re.search(
                "\[([^\]]*)\]",
                subprocess.check_output(
                    [
                        "conda",
                        "activate",
                        ENV_NAME,
                        "&&",
                        "conda",
                        "list",
                        "emr",
                        "--json",
                    ],
                    shell=True,
                ).decode("utf8"),
            ).group()
        )[0]["version"]
    ).rstrip()

    # Check olp-sdk-for-python version
    olp_sdk_version = str(
        json.loads(
            re.search(
                "\[([^\]]*)\]",
                subprocess.check_output(
                    [
                        "conda",
                        "activate",
                        ENV_NAME,
                        "&&",
                        "conda",
                        "list",
                        "olp-sdk-for-python",
                        "--json",
                    ],
                    shell=True,
                ).decode("utf8"),
            ).group()
        )[0]["version"]
    ).rstrip()

    os.chmod(
        f"{conda_prefix}/nagini-{nagini_version}/tutorial-notebooks".rstrip(), S_IREAD,
    )
    os.chmod(
        f"{conda_prefix}/nagini-{nagini_version}/api-reference".rstrip(), S_IREAD,
    )

    if not islink(f"{conda_prefix}/bin/emr-init.lnk"):
        print(f"Creating link {conda_prefix}/bin/emr-init.lnk")
        os.symlink(
            f"{conda_prefix}/lib/olp-emr/bin/init.bat",
            f"{conda_prefix}/bin/emr-init.lnk",
        )

    if not islink(f"{conda_prefix}/bin/emr-provision.lnk"):
        print(f"Creating link {conda_prefix}/bin/emr-provision.lnk")
        os.symlink(
            f"{conda_prefix}/lib/olp-emr/bin/deploy.bat",
            f"{conda_prefix}/bin/emr-provision.lnk",
        )

    if not islink(f"{conda_prefix}/bin/emr-deprovision.lnk"):
        print(f"Creating link {conda_prefix}/bin/emr-deprovision.lnk")
        os.symlink(
            f"{conda_prefix}/lib/olp-emr/bin/destroy.bat",
            f"{conda_prefix}/bin/emr-deprovision.lnk",
        )

    olp_sdk_docs_conda = f"{conda_prefix}/olp-sdk-for-python-{olp_sdk_version}"
    olp_sdk_docs_home = f"{HOME}/olp-sdk-for-python-{olp_sdk_version}"

    os.chmod(f"{conda_prefix}/emr-{emr_version}/tutorial-notebooks", S_IREAD)
    os.chmod(
        f"{conda_prefix}/spark-{emr_version}/tutorial-notebooks", S_IREAD,
    )
    os.chmod(olp_sdk_docs_conda, S_IREAD)

    # Cleaning the soft links in HOME directory
    if islink(olp_sdk_docs_home):
        os.unlink(olp_sdk_docs_home)

    olp_sdk_docs_conda_tut = f"{olp_sdk_docs_conda}/tutorial-notebooks"
    # Link the tutorials
    if not islink(f"{olp_sdk_docs_conda_tut}/emr"):
        print(f"Creating link {olp_sdk_docs_conda_tut}/emr")
        os.symlink(
            f"{conda_prefix}/emr-{emr_version}/tutorial-notebooks",
            f"{olp_sdk_docs_conda_tut}/emr",
        )

    if not islink(f"{olp_sdk_docs_conda_tut}/spark"):
        print(f"Creating link {olp_sdk_docs_conda_tut}/spark")
        os.symlink(
            f"{conda_prefix}/spark-{emr_version}/tutorial-notebooks",
            f"{olp_sdk_docs_conda_tut}/spark",
        )

    if not islink(f"{olp_sdk_docs_conda_tut}/python"):
        print(f"Creating link {olp_sdk_docs_conda_tut}/python")
        os.symlink(
            f"{conda_prefix}/nagini-{nagini_version}/tutorial-notebooks",
            f"{olp_sdk_docs_conda_tut}/python",
        )

    # Link the documentation
    os.makedirs(
        f"{olp_sdk_docs_conda}/documentation", exist_ok=True,
    )

    if not islink(
        f"{olp_sdk_docs_conda}/documentation/OLP SDK for Python API Reference.html"
    ):
        print(
            f"Creating link {olp_sdk_docs_conda}/documentation/OLP SDK for Python API Reference.html"
        )
        os.symlink(
            f"{conda_prefix}/nagini-{nagini_version}api-reference/index.html",
            f"{olp_sdk_docs_conda}/documentation/OLP SDK for Python API Reference.html",
        )

    # Creating the folder entrypoint at user's HOME folder
    if not islink(olp_sdk_docs_home):
        print(f"Creating link {olp_sdk_docs_home}")
        os.symlink(
            olp_sdk_docs_conda, olp_sdk_docs_home,
        )

    os.makedirs(f"{conda_prefix}/etc/conda/activate.d", exist_ok=True)

    os.makedirs(f"{conda_prefix}/etc/conda/deactivate.d", exist_ok=True)

    with open(f"{conda_prefix}/etc/conda/activate.d/env_vars.bat", "w+") as fp:
        fp.write(f"set PYTHONPATH={conda_prefix}/Lib/python3.7/site-packages")


def init_environment():
    """
    Create the required files for the SDK.
    """
    print("Initializing the SDK configuration files ...")
    # read_repo_credentials()
    prepare_conda_credentials_file_and_environment()
    prepare_ivy_settings_file()
    print("- Installation completed successfully ! Generated files:")
    print(f"  {_CONDARC_FILE}")
    print(f"  {_IVY_SETTINGS_FILE}")


def read_repo_credentials():
    """
    Read repository credentails from settings.xml.
    """
    global ARTIFACTORY_USER
    global ARTIFACTORY_PASSWORD
    global _M2_SETTINGS_FILE
    if isfile(_M2_SETTINGS_FILE):
        f = open(_M2_SETTINGS_FILE, "r")
        m2_data = f.read()
        ARTIFACTORY_USER = re.search("<username>(.*)<\/username>", m2_data).group(1)
        ARTIFACTORY_PASSWORD = re.search("<password>(.*)<\/password>", m2_data).group(1)
        if ARTIFACTORY_USER == "" or ARTIFACTORY_PASSWORD == "":
            print(
                "Your maven settings ($HOME/.m2/settings.xml) does not have a configured HERE Repository (HERE_PLATFORM_REPO)"
            )
            sys.exit(1)
    else:
        print("Your HERE Repo maven settings ($_M2_SETTINGS_FILE) was not found.")
        sys.exit(1)


def prepare_conda_credentials_file_and_environment():
    """
    Generate .condarc file and create the environment for the SDK and install SDK.
    """
    # check if env exists if not create
    if not RUNNING_WINDOWS:
        output = subprocess.check_output(["conda env list"], shell=True).decode("utf8")
    else:
        output = subprocess.check_output(["conda", "env", "list"], shell=True).decode(
            "utf8"
        )
    env_paths = re.findall(f"^{ENV_NAME}\s\s*(.*)", output, re.MULTILINE)
    if len(env_paths) == 0:
        print(f"Creating conda environment with name {ENV_NAME}")
        if not RUNNING_WINDOWS:
            cmd = [f"conda create -y --force -n {ENV_NAME}"]
        else:
            cmd = ["conda", "create", "-y", "--force", "-n", ENV_NAME]
        r = subprocess.call(cmd, stdout=FNULL, shell=True)
    check_condarc_file()
    print(f"Installing SDK in conda environment with name '{ENV_NAME}'")
    print("- Started installing SDK ...")
    if not RUNNING_WINDOWS:
        cmd = [
            f"source $(conda info --base)/etc/profile.d/conda.sh && conda activate {ENV_NAME} && conda env update -n {ENV_NAME} -f tmp/conda-env-files/olp_sdk_for_python_env.yml"
        ]
    else:
        if ENV_ACTIVE:
            cmd = [
                "conda",
                "deactivate",
                "&&",
                "conda",
                "activate",
                ENV_NAME,
                "&&",
                "conda",
                "env",
                "update",
                "-n",
                ENV_NAME,
                "-f",
                "tmp/conda-env-files/olp_sdk_for_python_env.yml",
            ]
        else:
            cmd = [
                "conda",
                "activate",
                ENV_NAME,
                "&&",
                "conda",
                "env",
                "update",
                "-n",
                ENV_NAME,
                "-f",
                "tmp/conda-env-files/olp_sdk_for_python_env.yml",
            ]
    r = subprocess.call(cmd, stdout=FNULL, shell=True)
    if r != 0:
        print(
            f"There was some issue while creating conda environment {ENV_NAME} please check the above error."
        )
        sys.exit(1)
    print("- Completed installing SDK ...")


def prepare_ivy_settings_file():
    """
    Generate ivy.settings.xml file.
    """
    print(f"- Writing OLP Repository credentials into {_IVY_SETTINGS_FILE} ...")
    ivy_settings_template = """\
    <ivysettings>
        <settings defaultResolver="main" />
        <credentials host="repo.platform.here.com" realm="Artifactory Realm" username="{username}" passwd="{password}" />
        <resolvers>
            <ibiblio name="here" m2compatible="true" root="https://repo.platform.here.com/artifactory/open-location-platform" />
            <ibiblio name="maven" root="https://repo1.maven.org/maven2" m2compatible="true" />
            <ibiblio name="bintray" root="https://dl.bintray.com/jroper/maven/" m2compatible="true" />
            <chain name="main">
                <resolver ref="here"/>
                <resolver ref="maven"/>
                <resolver ref="bintray"/>
            </chain>
        </resolvers>
    </ivysettings>
    """
    var_value = {"username": ARTIFACTORY_USER, "password": ARTIFACTORY_PASSWORD}
    with open(_IVY_SETTINGS_FILE, "w+") as fp:
        fp.write(dedent(ivy_settings_template.format(**var_value)))


def validate_environment():
    """
    Verify all the software requirements and configuration files for the SDK.
    """
    print("Validating environment ...")
    check_software_requirements()
    check_files_requirement()
    print(
        "- The files are properly configured and ready for the installation of the SDK !"
    )


def check_condarc_file():
    """
    To check before update that .condarc file exists if not then create one.
    """
    global _CONDARC_FILE
    print("Checking .condarc file")

    if not RUNNING_WINDOWS:
        output = subprocess.check_output(["conda env list"], shell=True).decode("utf8")
    else:
        output = subprocess.check_output(["conda", "env", "list"], shell=True).decode(
            "utf8"
        )
    env_paths = re.findall(f"^{ENV_NAME}\s\s*(.*)", output, re.MULTILINE)

    env_paths[0] = env_paths[0].replace(" ", "").replace("*", "").strip()

    if len(env_paths) == 0:
        print(
            "There was a error with conda environment name "
            + ENV_NAME
            + " please provide an another conda environment name."
        )
        sys.exit(1)
    env_home = str(env_paths[0]).rstrip()
    _CONDARC_FILE = join(env_home, ".condarc")
    # create condarc file if does not exist
    condarc_template = """\
    channels:
        - defaults
        - https://conda.anaconda.org/conda-forge
        - https://{username}:{password}@repo.platform.here.com/artifactory/api/conda/olp_analytics/analytics_sdk
    channel_priority: strict
    ssl_verify: true
    anaconda_upload: false
    safety_checks: disabled
    """
    var_value = {
        "username": ARTIFACTORY_USER,
        "password": urllib.parse.quote_plus(ARTIFACTORY_PASSWORD),
    }
    if not isfile(_CONDARC_FILE):
        print(f"- Writing OLP Repository credentials into {_CONDARC_FILE} ...")
        with open(_CONDARC_FILE, "w+") as fp:
            fp.write(dedent(condarc_template.format(**var_value)))
    else:
        print(f"- Found .condarc file at {_CONDARC_FILE} ...")


def check_software_requirements():
    """
    Verify all the software requirements are satisfied.
    """
    print("- Checking software requirements ...")
    # check python version
    if platform.python_version() < "3.6":
        print("Sorry, requires minimum Python 3.6")
        sys.exit(1)
    # checking conda
    if which("conda") is not None:
        # check that the installed conda version is greater than 3
        if not RUNNING_WINDOWS:
            installed_conda_version = subprocess.check_output(
                ["conda --version"], shell=True
            ).decode("utf8")
        else:
            installed_conda_version = subprocess.check_output(
                ["conda", "--version"], shell=True
            ).decode("utf8")
        if installed_conda_version.split()[1] < MIN_REQ_CONDA_VERSION:
            print()
            print(f"The required conda version is {MIN_REQ_CONDA_VERSION} or greater.")
            sys.exit(1)
    else:
        print()
        print("Conda is not installed.")
        sys.exit(1)


def check_files_requirement():
    """
    Verify all the credentails file requirements are satisfied.
    """

    print("- Checking existence of configuration files ...")
    # check if the credentials files are in place
    files_path_list = []
    if not RUNNING_WINDOWS:
        files_path_list.append(f"{HOME}/.here/credentials.properties")
        files_path_list.append(f"{HOME}/.here/hls_credentials.properties")
    else:
        files_path_list.append(f"{HOME}/.here/credentials.properties")
        files_path_list.append(f"{HOME}/.here/hls_credentials.properties")
    files_path_list.append(_M2_SETTINGS_FILE)
    _missing_creds = ""

    for file in files_path_list:
        if not isfile(file):
            _missing_creds += f"\n{file}"

    if _missing_creds != "":
        print("The following file(s) are not properly configured:-")
        print(_missing_creds)
        sys.exit(1)


def check_after_install_files_requirement():
    """
    Verify all the file generate by installation script are present.
    """
    print("- Verifying installed configuration files ...")
    # check if the credentials files are in place
    _missing_creds = ""

    if not isfile(_IVY_SETTINGS_FILE):
        _missing_creds = f"\n{_IVY_SETTINGS_FILE}"

    if _missing_creds != "":
        print("The following file(s) are not properly configured:-")
        print(_missing_creds)
        sys.exit(1)

    print("Successfully installed SDK !!!")


def clean_up_tmp():
    """
    Remove the conda environment downloaded by the script.
    """
    if exists(join(os.getcwd().rstrip(), "tmp")):
        shutil.rmtree(join(os.getcwd().rstrip(), "tmp"))


if __name__ == "__main__":
    atexit.register(clean_up_tmp)
    main()
