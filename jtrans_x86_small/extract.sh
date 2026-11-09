#!/bin/bash
source /home/rfall/miniconda3/bin/activate processing
cd /home/rfall/jtrans/datautils
python3 run.py --ida_path=/opt/idapro-9.0/idat64 --dataset_dir=/libs/original/ --strip_path=./dataset_strip --script_path=./process.py --save_root=./extract