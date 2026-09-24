#!/bin/bash
#SBATCH --partition=kura-wide
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err
#SBATCH --time=01:30:00
#SBATCH --ntasks-per-node=20
#SBATCH --cpus-per-task=1
#SBATCH --exclusive
#SBATCH --nodes 4
#SBATCH --job-name lto-4
#SBATCH --mail-type=END,FAIL
. /opt/Modules/3.2.10/init/sh
module purge
module load mpich/3.3.2-gcc-9.3.0 gcc/9.3.0
cd /work/casch/RustMPIExperiments/lto/4
source ../pic-common.sh
echo "### job=$SLURM_JOB_ID nodes=$SLURM_NNODES ntasks=$SLURM_NTASKS nodelist=$SLURM_JOB_NODELIST start=$(date -Is)"
echo "### job=$SLURM_JOB_ID nodes=$SLURM_NNODES ntasks=$SLURM_NTASKS nodelist=$SLURM_JOB_NODELIST start=$(date -Is)" >&2
md5sum pic pic-lto pic-mpi pic-mpi-lto bs-solctra-multinode bs-solctra-multinode-lto bs-solctra-rs bs-solctra-rs-lto

PIC_REPS=10
SOL_REPS=5
for (( rep = 0; rep < PIC_REPS; rep++ )); do
  for style in GEOMETRIC SINUSOIDAL LINEAR PATCH; do
    pic_all_variants strong "$style" "$rep" $((12*102400))
  done
done
for (( rep = 0; rep < PIC_REPS; rep++ )); do
  for style in GEOMETRIC SINUSOIDAL LINEAR PATCH; do
    pic_all_variants weak "$style" "$rep" $((SLURM_NTASKS*102400))
  done
done
for (( rep = 0; rep < SOL_REPS; rep++ )); do
  solctra_all_variants "$rep" $((12*5120)) 1000
done
echo "### end=$(date -Is)"
echo "### end=$(date -Is)" >&2
