#!/bin/bash

OUTFILE=data.csv
DIRECTORY=$1
echo nodes,threads,time,language > $OUTFILE
for i in 4 8
do
  for file in $DIRECTORY/stderr*_${i}
  do
    export THREADS=`echo $file | awk -F '/' '{print $3}' | awk -F '_' '{print $4}'`
    grep Simulation $file | awk -v var="${i}" -v t="${THREADS}" -F ' ' '{print var,t,$6,"rust"}' | sed 's/ /,/g' >> $OUTFILE
  done
done
