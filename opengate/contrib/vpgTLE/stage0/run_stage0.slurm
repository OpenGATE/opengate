#! /usr/bin/bash -lx
#SBATCH --output=Seq%j.out       # nom du fichier de sortie
#SBATCH --time=1-00:00:00
#SBATCH --ntasks=1
#SBATCH --mem=2000                    # Mémoire en MB par défaut
#SBATCH --error=Seq%A_%a.out        # nom du fichier d'erreur (ici en commun avec la sortie)

# sbatch --export=N=10000,P=proton,W=weight run_stage0.slurm

module load /pbs/software/modulefiles/redhat-9-x86_64/Compilers/gcc/13.2.0
module load /pbs/software/modulefiles/redhat-9-x86_64/Analysis/root/6.30.06
source /path/to/theG4used/geant4.11.2.1/bin/geant4make.sh

cd /path/to/your/outputfolder/geant-stage0/output
mkdir output_${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}
N=${1:-10000}
P=${2:-proton}
W=${3:-""}

cd /path/to/your/compilation/folder/bin
./stage0-vpgtle ${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID} -n ${N} -p ${P} ${W}



