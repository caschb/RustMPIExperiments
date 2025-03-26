#!/bin/sh

export OUT_DIR=strong_runs_log/
tar -cvzf output_strong_scaling.tar.gz std* data.csv ${OUT_DIR}
