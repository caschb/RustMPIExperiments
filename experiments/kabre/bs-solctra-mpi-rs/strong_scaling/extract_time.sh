#!/bin/bash

OUTFILE=data.csv
DIRECTORY=$1
echo nodes,time,language > $OUTFILE
for i in 1 2 4 8
do
  for file in $DIRECTORY/stderr*_${i}
  do
    grep Simulation $file | awk -v var="${i}" -F ' ' '{print var,$6,"rust"}' | sed 's/ /,/g' >> $OUTFILE
  done
done
