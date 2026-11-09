import pandas as pd
import sqlite3
from itertools import islice
from qdrant_client import QdrantClient
from qdrant_client import models
from collections import defaultdict
import uuid
import os
import numpy as np 
import json
import sys

def load_and_prepare_nomenclature():

    db_path = '../the_base_of_datas.sqlite'
    conn = sqlite3.connect(db_path)
    query = "SELECT name FROM sqlite_master WHERE type='table';"
    tables = pd.read_sql_query(query, conn)
    table_names = tables['name'].tolist()
    dfs = {}
    for table in table_names:
        dfs[table] = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    conn.close()
    print("done loading sqlite db")

    ### MAVEN
    maven = dfs['maven_modules_hashes'].merge(dfs['maven_truth_modules'].rename(columns={"name":"module_name"}), left_on='module_id', right_on='id').drop(columns=['id'])
    maven = maven.merge(dfs['maven_truth_hashes'].rename(columns={"name":"lib_name"}), left_on='hash_id', right_on='id').drop(columns=['id'])
    maven = maven.add_prefix("maven_")

    maven_unique = maven.sort_values(by="maven_date").drop_duplicates(subset="maven_hash", keep="first")

    replace_names = {}

    for m in maven_unique.iloc:
        replace_names[m['maven_hash']] = f"{m['maven_hash']} {m['maven_lib_name']} {m['maven_groupname']}.{m['maven_artifact']} {m['maven_version']}"

    print("Done loading names dictionary")
    return replace_names

def print_results_nomenclature(f, replace_names, bin, hashed_results):
    print(f"Matching: {replace_names[bin]}")
    f.write(f"Matching: {replace_names[bin]}\n")
    for k,v in hashed_results:
        print(replace_names[k], v)
        f.write(f"{replace_names[k]} {v}\n")


def create_and_fill():
    client.delete_collection("asm2vec_embeddings")

    client.create_collection(
        collection_name="asm2vec_embeddings",
        vectors_config=models.VectorParams(size=200, distance=models.Distance.COSINE),
        # optimizers_config=models.OptimizersConfigDiff(
        #     # indexing_threshold=0, # faster upload
        # ),
        # shard_number=4,
    )
    client.update_collection(
        collection_name="asm2vec_embeddings",
        hnsw_config = models.HnswConfigDiff(ef_construct=200, m=32),

    )

    BATCH_SIZE = 200
    batches = np.array_split(ebds, BATCH_SIZE)

    all_vectors = {}
    with open("asm2vec_ids.txt", "w") as f:
        for batch_id, batch in ebds.groupby(ebds.index // BATCH_SIZE):
            ids, vectors, payloads = [], [], []
            # print(batch)
            for point in batch.itertuples():
                id = str(uuid.uuid4())
                name = os.path.basename(point.idb_path)[:-4]
                f.write(f"{id} {name}_{point.fva}\n")
                ids.append(id)
                vec = np.array([float(x) for x in point.embeddings.split(";")])
                vectors.append(vec/np.linalg.norm(vec))
                payloads.append({"name": name, "func": point.fva})

            client.upsert(
                collection_name="asm2vec_embeddings",
                points=models.Batch(
                    ids=ids,
                    vectors=vectors,
                    payloads=payloads,
                ),
            )
client = QdrantClient(url="http://localhost:6333")

ebds = pd.read_csv('embeddings.csv')
# if len(sys.argv) > 1:
create_and_fill()

# replace_names = load_and_prepare_nomenclature()
names = ebds["idb_path"]
f = open('results.txt', 'w')
for mybin in set(names):
    mybin_name = os.path.basename(mybin)[:-4]
    hits = defaultdict(lambda: int(0))
    funcs = ebds[ebds["idb_path"] == mybin]
    for e in funcs.itertuples():
        vec = np.array([float(x) for x in e.embeddings.split(";")])
        func_embedding = vec/np.linalg.norm(vec)
        resp = client.query_points(
            collection_name="asm2vec_embeddings",
            query=func_embedding,
            search_params=models.SearchParams(hnsw_ef=128, exact=False),
            limit=500,
        ).points
        assert(len(resp) == 500)
        max_scores = [(r.payload['name'], r.score) for r in resp]
        lib_to_score = {k: max(v for _, v in max_scores if k == _) for k in set(k for k, _ in max_scores)}
        for lib,score in lib_to_score.items():
            hits[lib] += score
    h = sorted(hits.items(), key=lambda item: item[1])[::-1]

    print("done, converting results")
    # print_results_nomenclature(f, replace_names, mybin_name, h)
    print(f"Matching: {mybin_name}")
    f.write(f"Matching: {mybin_name}\n")
    for k,v in h:
        f.write(f"{k} {v}\n")
    f.write("\n")

f.close()
os.system("cat results.txt | ./change_logs.sh > version_results_x86.txt")
