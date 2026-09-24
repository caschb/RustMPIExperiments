#!/bin/bash
# One-node smoke test under salloc: every PIC variant/style must validate and
# the BS-SOLCTRA LTO outputs must match the no-LTO outputs.
set -eu
. /opt/Modules/3.2.10/init/sh
module purge
module load mpich/3.3.2-gcc-9.3.0 gcc/9.3.0
cd /work/casch/RustMPIExperiments/lto/smoke
source ../pic-common.sh
echo "nodes=$SLURM_NNODES ntasks=$SLURM_NTASKS host=$(hostname)"
for style in GEOMETRIC SINUSOIDAL LINEAR PATCH; do
  pic_all_variants strong "$style" 0 $((12*102400))
done
solctra_all_variants 0 $((12*5120)) 20
echo "### smoke done"
