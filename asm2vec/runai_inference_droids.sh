#!/bin/bash
runai submit \
  --name asm2vec-inference-droids-small-x86-ida \
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
  -- /bin/bash -c "python3 i2v.py -d --asm2vec --inference -e1 -w4 --inputdir /mnt/hexhive/asm2vec/ground_truth_libs/i2v_preprocessing -c /mnt/hexhive/asm2vec/model -o /mnt/hexhive/asm2vec/ground_truth_libs/asm2vec_inference --checkpoint_dir /mnt/hexhive/asm2vec/ground_truth_libs/checkpoints"