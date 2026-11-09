import os
import subprocess
import multiprocessing
import time
from util.pairdata import pairdata
import argparse

ida_path = "/opt/idapro-9.0/idat64"
work_dir = os.path.abspath('.')
dataset_dir = '/mnt/hexhive/jtrans/new_droids/ground_truth_libs'
strip_path = "/mnt/hexhive/jtrans/new_droids/ground_truth_libs/dataset_strip"
script_path = f"./process.py"
SAVE_ROOT = "/mnt/hexhive/jtrans/new_droids/ground_truth_libs/extract"

def getTarget(path, prefixfilter=None):
    target = []
    for file in os.listdir(path):
        full_path = os.path.join(path, file)
        if os.path.isfile(full_path):
            if prefixfilter is None:
                target.append(full_path)
            else:
                for prefix in prefixfilter:
                    if file.startswith(prefix):
                        target.append(full_path)
    return target

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="jTrans-feature-extraction")
    parser.add_argument('--ida_path', type=str, default=ida_path, help='ida pro path')
    parser.add_argument('--log_dir', type=str, default='log', help='log directory')
    parser.add_argument('--dataset_dir', type=str, default=dataset_dir, help='dataset directory')
    parser.add_argument('--strip_path', type=str, default=strip_path, help='strip path')
    parser.add_argument('--script_path', type=str, default=script_path, help='script path')
    parser.add_argument('--save_root', type=str, default=SAVE_ROOT, help='save root')
    args = parser.parse_args()
    ida_path = args.ida_path
    dataset_dir = args.dataset_dir
    strip_path = args.strip_path
    script_path = args.script_path
    SAVE_ROOT = args.save_root
    if not os.path.exists(SAVE_ROOT):
        os.makedirs(SAVE_ROOT)
    if not os.path.exists(args.log_dir):
        os.makedirs(args.log_dir)
    if not os.path.exists(strip_path):
        os.makedirs(strip_path)
    
    # prefixfilter = ['libcap-git-setcap']
    start = time.time()
    target_list = getTarget(dataset_dir)
    print(f"[+] Target List: {target_list}")
    pool = multiprocessing.Pool(processes=8)
    for target in target_list:
        filename = target.split('/')[-1]
        # filename_strip = filename  + '.strip'
        # ida_input = os.path.join(strip_path, filename_strip)
        # os.system(f"strip -s {target} -o {ida_input}")
        # print(f"strip -s {target} -o {ida_input}")
        ida_input = target

        # cmd_str = f'{ida_path} -Llog/{filename}.log -c -A -S{script_path} -o{target} {ida_input}'
        # print(cmd_str)
        cmd = [ida_path, 
               f'-L{args.log_dir}/{filename}.log', 
               '-c', 
               '-A', 
               f'-S{script_path}',
               f'-Oextract:{dataset_dir}:{SAVE_ROOT}', 
               f'-o{target}', 
               f'{ida_input}']
        print(f"[*] Running command: {' '.join(cmd)}")
        pool.apply_async(subprocess.call, args=(cmd,))
    pool.close()
    pool.join()
    print('[*] Features Extracting Done')
    pairdata(SAVE_ROOT)
    end = time.time()
    print(f"[*] Time Cost: {end - start} seconds")
