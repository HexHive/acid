#!/bin/bash
runai submit \
  --name asm2vec-train-dataset1 \
  --image registry.rcp.epfl.ch/binary-similarity/rcp-asm2vec:latest \
  --gpu 1 \
  --environment WANDB_API_KEY="d9f347c9093bfa6517c8511f2fc87c786bc92842" \
  --environment PYTHONUSERBASE=/home/rfall/.local \
  --run-as-uid 246723 \
  --run-as-gid 83413 \
  --large-shm \
  --backoff-limit 0 \
  --existing-pvc claimname=hexhive-scratch,path=/mnt/hexhive \
  --interactive \
  --command \
  -- /bin/bash -c "python3 i2v.py -d --asm2vec --train -e1 -w4 --inputdir /mnt/hexhive/asm2vec/binary_function_similarity/DBs/Dataset-1/features/training/a2v_preprocessing_Dataset-1-training -o /mnt/hexhive/asm2vec/model --checkpoint_dir /mnt/hexhive/asm2vec/checkpoints"