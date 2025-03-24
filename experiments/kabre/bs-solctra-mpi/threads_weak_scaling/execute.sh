#!/bin/bash

# Thread scaling
for i in 4 8
do
  sed -e "s/{nodes}/${i}/g" -e "s/{reps}/5/g" threads.slurm.template | sbatch
done
