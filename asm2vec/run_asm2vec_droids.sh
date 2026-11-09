#!/bin/bash

ls /libs/original | parallel ./extract_function.sh /libs/original/{}
python3 i2v_preprocessing.py -d -w4 -a2v -i /libs/acfg_disasm/ -o /libs/i2v_preprocessing/
python3 i2v_preprocessing.py -d -w4 -a2v -i /work/binary_function_similarity/DBs/Dataset-1/features/training/acfg_disasm_Dataset-1_training -o /work/binary_function_similarity/DBs/Dataset-1/features/training/a2v_preprocessing_Dataset-1-training
python3 i2v.py -d --asm2vec --train -e1 -w4 --inputdir /work/binary_function_similarity/DBs/Dataset-1/features/training/a2v_preprocessing_Dataset-1-training -o /libs/checkpoint
python3 i2v.py -d --asm2vec --inference -e1 -w4 --inputdir /libs/i2v_preprocessing -c /libs/checkpoint -o /libs/asm2vec_inference
