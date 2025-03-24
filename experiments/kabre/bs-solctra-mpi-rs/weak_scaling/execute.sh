#!/bin/bash


# Weak scaling
for i in 1 2 4 8
do
  sed -e "s/{nodes}/${i}/g" -e "s/{reps}/5/g" weak.slurm.template | sbatch
done
