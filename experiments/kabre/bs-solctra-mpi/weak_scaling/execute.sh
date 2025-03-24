#!/bin/bash

# Strong scaling
#for i in 1 2 4 8
#for i in 8
#do
#  sed -e "s/{nodes}/${i}/g" -e "s/{reps}/5/g" strong_c.slurm.template | sbatch
#done

# Thread experiment
for i in 4 8
do
  echo ${i}
  sed -e "s/{nodes}/${i}/g" -e "s/{reps}/5/g" threads.slurm.template | sbatch
done
