#! /usr/bin/bash -lx
#SBATCH --output=Seq%j.out       # nom du fichier de sortie
#SBATCH --time=1-00:00:00
#SBATCH --ntasks=1
#SBATCH --mem=2000                    # Mémoire en MB par défaut
#SBATCH --error=Seq%A_%a.out        # nom du fichier d'erreur (ici en commun avec la sortie)

# sbatch run_stage0.slurm

module load /pbs/software/modulefiles/redhat-9-x86_64/Compilers/gcc/13.2.0
module load /pbs/software/modulefiles/redhat-9-x86_64/Analysis/root/6.30.06
source /sps/creatis/vguittet/geant4.11.2.1/bin/geant4make.sh

cd /sps/creatis/vguittet/geant-stage0/output
mkdir output_${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}


cd /sps/creatis/vguittet/geant-stage0/bin
./stage0 ${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}

