#!/bin/bash
runai submit \
  --name finetune-large-train \
  --image registry.rcp.epfl.ch/binary-similarity/rcp-jtrans:latest \
  --gpu 4 \
  --environment WANDB_API_KEY="d9f347c9093bfa6517c8511f2fc87c786bc92842" \
  --environment PYTHONUSERBASE=/home/rfall/.local \
  --run-as-uid 246723 \
  --run-as-gid 83413 \
  --large-shm \
  --backoff-limit 0 \
  --existing-pvc claimname=hexhive-scratch,path=/mnt/hexhive \
  --command \
  -- /bin/bash -c "cd /mnt/hexhive/jtrans/code/jTrans && python3 finetune.py --train_path /mnt/hexhive/jtrans/dataset/train --eval_path /mnt/hexhive/jtrans/dataset/test"