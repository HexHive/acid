#!/bin/bash
runai submit \
  --name debug-x86 \
  --image registry.rcp.epfl.ch/binary-similarity/rcp-jtrans:latest \
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
  -- /bin/bash -c 'bash reproduce.sh $(pwd);sleep 10d'
