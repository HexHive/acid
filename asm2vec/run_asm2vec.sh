
docker run --rm -v <path_to_the_acfg_disasm_dir>:/input -v <path_to_the_output_dir>:/output -it asm2vec /code/i2v_preprocessing.py -d [--workers 4] [-a2v, -d2v] -i /input -o /output/

python3 i2v_preprocessing.py -d -w4 -a2v -i /libs/acfg_disasm/ -o /libs/i2v_preprocessing/


# Testing on Dataset-1

docker run --rm -v $(pwd)/../../DBs/Dataset-1/features/training/acfg_disasm_Dataset-1_training:/input -v $(pwd):/output -it asm2vec /code/i2v_preprocessing.py -d -w4 -d2v -i /input -o /output/d2v_preprocessing_Dataset-1-training
docker run --rm -v $(pwd)/../../DBs/Dataset-1/features/training/acfg_disasm_Dataset-1_training:/input -v $(pwd):/output -it asm2vec /code/i2v_preprocessing.py -d -w4 -a2v -i /input -o /output/a2v_preprocessing_Dataset-1-training

python3 i2v_preprocessing.py -d -w4 -a2v -i /work/binary_function_similarity/DBs/Dataset-1/features/training/acfg_disasm_Dataset-1_training -o /work/binary_function_similarity/DBs/Dataset-1/features/training/a2v_preprocessing_Dataset-1-training
python3 i2v_preprocessing.py -d -w4 -a2v -i /work/binary_function_similarity/DBs/Dataset-1/features/testing/acfg_disasm_Dataset-1_testing -o /work/binary_function_similarity/DBs/Dataset-1/features/testing/a2v_preprocessing_Dataset-1-testing

docker run --rm -v $(pwd)/a2v_preprocessing_Dataset-1-training:/input -v $(pwd):/output -it asm2vec /code/i2v.py -d --asm2vec --train -e1 -w4 --inputdir /input/ -o /output/asm2vec_train_Dataset-1-training
docker run --rm -v $(pwd)/a2v_preprocessing_Dataset-1-testing:/input -v $(pwd)/asm2vec_train_Dataset-1-training:/checkpoint -v $(pwd):/output -it asm2vec /code/i2v.py -d --asm2vec --inference -e1 -w4 --inputdir /input/ -c /checkpoint -o /output/asm2vec_inference_Dataset-1-testing

python3 i2v.py -d --asm2vec --train -e1 -w4 --inputdir /work/binary_function_similarity/DBs/Dataset-1/features/training/a2v_preprocessing_Dataset-1-training -o /work/binary_function_similarity/DBs/Dataset-1/features/training/asm2vec_train_Dataset-1-training
python3 i2v.py -d --asm2vec --inference -e1 -w4 --inputdir /work/binary_function_similarity/DBs/Dataset-1/features/testing/a2v_preprocessing_Dataset-1-testing -c /work/binary_function_similarity/DBs/Dataset-1/features/training/asm2vec_train_Dataset-1-training -o /work/binary_function_similarity/DBs/Dataset-1/features/testing/asm2vec_inference_Dataset-1-testing

docker run --rm -v $(pwd)/a2v_preprocessing_Dataset-1-testing:/input -v $(pwd)/asm2vec_train_Dataset-1-training:/checkpoint -v $(pwd):/output -it asm2vec /code/i2v.py -d --asm2vec --inference -e1 -w4 --inputdir /input/ -c /checkpoint -o /output/asm2vec_inference_Dataset-1-testing

docker run --rm -v $(pwd)/a2v_preprocessing_Dataset-1-training:/input -v $(pwd):/output -it asm2vec /code/i2v.py -d --asm2vec --train -e1 -w4 --inputdir /input/ -o /output/asm2vec_train_Dataset-1-training