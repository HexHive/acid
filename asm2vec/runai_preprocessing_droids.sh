#!/bin/bash
runai submit \
  --name asm2vec-preproc-droids-small-x86-ida \
  --image registry.rcp.epfl.ch/binary-similarity/rcp-asm2vec:latest \
  --gpu 0 \
  --node-pool v100 \
  --environment WANDB_API_KEY="d9f347c9093bfa6517c8511f2fc87c786bc92842" \
  --environment PYTHONUSERBASE=/home/rfall/.local \
  --run-as-uid 246723 \
  --run-as-gid 83413 \
  --large-shm \
  --backoff-limit 0 \
  --existing-pvc claimname=hexhive-scratch,path=/mnt/hexhive \
  --interactive \
  --command \
  -- /bin/bash -c "./preprocess_droids.sh"