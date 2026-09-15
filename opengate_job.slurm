#!/bin/bash -x
#SBATCH --mem=20000               # Memory in MB per default
#SBATCH --time=10:00:00
#SBATCH --ntasks=1
#SBATCH --output=Seq%j.out       # nom du fichier de sortie
#SBATCH --error=Seq%j.out        # nom du fichier d'erreur (ici en commun avec la sortie)



function error {
    echo "ERROR: $1"
    exit 1
}

function warning {
    echo "WARNING: $1"
}

date
test -f ${HOME}/.bashrc && echo "Sourcing bashrc" && source ${HOME}/.bashrc
set -u

echo "Checking"
uname -a
echo "JOBDIR=${JOBDIR:?"unknown JOBDIR"}"

echo Using $(which python)
test -d "${JOBDIR}"  || error "invalid macro"


# Enforce one thread
ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=1

echo "Lauching macro"
date
cd ${JOBDIR}
cd ..
opengate_job_runner --backend "slurm" ${JOBDIR} || error "gate failed"
date

echo "Success!!!"
