#!/bin/bash
set -e
if [ "$#" -eq 0 ]; then
    echo "No arguments provided. Please provide the absolute path to the directory containing your droids.tar"
    exit 1
fi
mkdir /home/runai-home/.idapro
cp /home/rfall/.idapro/ida.reg /home/runai-home/.idapro/ida.reg
cd $1
tar -xvf droids.tar
dataset="$1/ground_truth_libs"
ls $dataset | parallel ./extract_function.sh $dataset{}
python3 i2v_preprocessing.py -d -w4 -a2v -i $dataset/acfg_disasm/ -o $dataset/i2v_preprocessing/
python3 i2v_preprocessing.py -d -w4 -a2v -i /mnt/hexhive/asm2vec/binary_function_similarity/DBs/Dataset-1/features/training/acfg_disasm_Dataset-1_training -o /mnt/hexhive/asm2vec/binary_function_similarity/DBs/Dataset-1/features/training/a2v_preprocessing_Dataset-1-training
python3 i2v.py -d --asm2vec --train -e1 -w4 --inputdir /mnt/hexhive/asm2vec/binary_function_similarity/DBs/Dataset-1/features/training/a2v_preprocessing_Dataset-1-training -o  /mnt/hexhive/asm2vec/checkpoint
python3 i2v.py -d --asm2vec --inference -e1 -w4 --inputdir $dataset/i2v_preprocessing -c  /mnt/hexhive/asm2vec/checkpoint -o $dataset/asm2vec_inference
