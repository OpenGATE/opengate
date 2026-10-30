#!/bin/bash
# Example: one job of a campaign split by opengate_jobs, run by slurm.
# Copy this file and slurm.json, adapt them to your cluster, then:
#   opengate_jobs split campaign -j 100
#   opengate_jobs run campaign --backend-options /path/to/slurm.json
# opengate_jobs run calls "sbatch <options> opengate_job.slurm" once per job,
# with JOBDIR (the folder of the job) added to --export.
# Options for one campaign (they replace the #SBATCH lines below):
#   opengate_jobs run campaign --backend-options slurm.json \
#       --submit-args "--time=04:00:00 --cpus-per-task=4"

#SBATCH --job-name=opengate
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1      # = number_of_threads of the simulation
#SBATCH --time=10:00:00
#SBATCH --output=slurm_%j.out  # in the campaign folder: only the slurm messages (time limit, memory)
# Site specific, e.g.:
##SBATCH --account=my_account
##SBATCH --partition=my_partition
##SBATCH --mem-per-cpu=4G

# The output of the job goes to job.log in its folder (as with the local
# backends): opengate_jobs status shows its end for a failed job.
exec >> "${JOBDIR:?unknown JOBDIR}/job.log" 2>&1

# Environment with opengate installed, e.g.:
# module load python
# source /path/to/venv/bin/activate

export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=1

echo "$(date) $(hostname) slurm job ${SLURM_JOB_ID} JOBDIR=${JOBDIR}"
echo "Using $(which python)"
cd "${JOBDIR}/.." || exit 1
opengate_job_runner --backend slurm "${JOBDIR}"
status=$?
echo "$(date) exit status ${status}"
exit ${status}
