#!/bin/bash
ls /mnt/hexhive/asm2vec/ground_truth_libs | parallel ./create_acfg.sh /mnt/hexhive/asm2vec/ground_truth_libs/{} /mnt/hexhive/asm2vec/ground_truth_libs