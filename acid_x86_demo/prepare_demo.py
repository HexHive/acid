from packaging.version import Version
import os
import sqlite3
import pandas as pd

# db_path = 'old.sqlite'
db_path = 'the_base_of_datas.sqlite'
print("USING DB", db_path)
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
maven_unique = maven_unique.dropna(subset=["maven_module_name"]) # drop nan values
print(len(maven_unique))


list_of_droids =  maven_unique[maven_unique["maven_artifact"].str.contains("android-gif-drawable")]
# list_of_droids =  maven_unique[maven_unique["maven_lib_name"].str.contains("libvlc.so")]
# list_of_droids =  maven_unique[maven_unique["maven_lib_name"].str.contains("libsignal_jni.so")]
os.system("tar cvf droids.tar "+" ground_truth_libs/".join([""]+list(list_of_droids["maven_hash"])))
os.system("cd ground_truth_libs; tar cvf ../bash.tar "+" ".join([""]+list(list_of_droids["maven_hash"])))

bash = "#!/bin/bash\nsed "
for m in list_of_droids.iloc:
    bash += f"-e \"s/{m['maven_hash']}/{m['maven_lib_name']} {m['maven_groupname']}.{m['maven_artifact']} {m['maven_version']}/g\" "
with open("change_logs.sh", "w") as f:
    f.write(bash)

print("Made a droids.tar with len ", len(list_of_droids))

print("Preparing python to score")
hashes_versions = []
for m in list_of_droids.iloc:
    hashes_versions.append((m['maven_hash'], (m['maven_lib_name'],Version(m['maven_version'].replace("-eap", ".0.")))))
hashes_versions = sorted(hashes_versions, key=lambda x: x[1])

python_script = f"""
import json
import sys
sorted_hashes = {[x[0] for x in hashes_versions]}
j = json.load(open(sys.argv[1]))
score = 0
for hash,closest in j.items():
    if "i64" in hash: hash = hash.split("/")[-1].split(".")[0]
    idx = sorted_hashes.index(hash)
    if closest[0] == hash: closest = closest[1:]
    idx_tentative = sorted_hashes.index(closest[0])
    if idx_tentative-1 <= idx <= idx_tentative+1:
        score += 1
    else:
        print(f"{{sorted_hashes[idx]}} at idx {{idx}} is not close to {{sorted_hashes[idx_tentative]}} at idx {{idx_tentative}}")
print(f"Final score: {{score}}/{{len(j)}}")
"""

with open("score.py", "w") as f:
    f.write(python_script)
