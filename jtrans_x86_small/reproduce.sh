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
cd $dataset
echo -n '[' > tmp.txt
for f in $(find . -maxdepth 1 -type f ! -name '*.*'); do echo -n "\"$(basename $f)\", " >> tmp.txt; mv $(basename $f) droid-$(basename $f)-bla; done
sed '${s/..$//}' tmp.txt > opts.txt
echo ']' >> opts.txt
rm tmp.txt
source /home/rfall/miniconda3/bin/activate processing
/opt/idapro-9.0/idapyswitch --force-path /home/rfall/miniconda3/envs/processing/lib/libpython3.9.so
cd /home/rfall/jTrans/datautils
python3 run.py --ida_path=/opt/idapro-9.0/idat64 --dataset_dir=$dataset --strip_path=$dataset/dataset_strip --script_path=./process.py --save_root=$dataset/extract --log_dir=$dataset/log
cd ..
conda deactivate
python3 eval_save.py --dataset_path $dataset/extract --opts_path $dataset/opts.txt --experiment_path $dataset/jTrans.pkl
python3 fasteval.py  --opts_path $dataset/opts.txt --poolsize 27 --experiment_path $dataset/jTrans.pkl --log_path $dataset
# python3 add_versions_to_log.py --log_dir $dataset
# ./change_logs.sh $dataset > /mnt/hexhive/jtrans/results/fasteval_results/$(basename $dataset) # TODO fix to take latest file in directory
# echo "Saved in /mnt/hexhive/jtrans/results/fasteval_results/$(basename $dataset)"