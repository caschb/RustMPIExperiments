#!/bin/bash

OUTFILE=data.csv
DIRECTORY=$1

# Strong scaling experiment
#echo nodes,time,language > $OUTFILE
#for i in 1 2 4 8
#do
#  for file in $DIRECTORY/stdout*-${i}_*
#  do
#    # grep Total $file | awk -v var="${i}" -F '=' '{print var,$2,"c"}' | grep -oP '[[:digit:]]+.[[:digit:]]+' >> $OUTFILE
#    grep Total $file | grep -oP '[[:digit:]]+.[[:digit:]]+' | awk -v var="${i}" '{print var,$1,"c"}' | sed 's/ /,/g' >> $OUTFILE
#  done
#done

echo nodes,threads,time,language > $OUTFILE
for i in 4 8
do
  for t in 1 10 20 40
  do
    for file in $DIRECTORY/stdout*-${i}_*_${t}_*
    do
#      # grep Total $file | awk -v var="${i}" -F '=' '{print var,$2,"c"}' | grep -oP '[[:digit:]]+.[[:digit:]]+' >> $OUTFILE
      grep Total $file | grep -oP '[[:digit:]]+.[[:digit:]]+' | awk -v var="${i}" -v thr="${t}" '{print var,thr,$1,"c"}' | sed 's/ /,/g' >> $OUTFILE
    done
  done
done
