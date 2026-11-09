#!/bin/bash
ls /mnt/hexhive/asm2vec/ground_truth_libs | parallel ./extract_function.sh /mnt/hexhive/asm2vec/ground_truth_libs/{} /mnt/hexhive/asm2vec/ground_truth_libs