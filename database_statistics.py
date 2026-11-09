from packaging.version import Version
from datetime import datetime
import os
import sqlite3
import pandas as pd
import subprocess
import time
import numpy as np
import collections
import tempfile
from bisect import bisect_left

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


convert_hash = lambda x: x
convert_back_hash = lambda x: x

#not
if os.path.exists("custom_hashes_sections"):
    #find . | sort | parallel -j 32 'tmp=$(mktemp); a=$(aarch64-linux-gnu-objcopy -O binary --only-section=.text --only-section=.data --only-section=.rodata {} $tmp; sha256sum -b $tmp | cut -d" " -f1); echo $a $(basename {}) >> ../custom_hashes_sections; echo {}; rm $tmp'
    custom_hashes = []
    for line in open("custom_hashes_sections", "r").readlines():
        custom_hashes += [list(map(lambda x: x.strip(), line.split(' ')))]
    conversion_dict = {l[-1]: l[0] for l in custom_hashes}
    conversion_backdict = {l[0]: l[-1] for l in custom_hashes}
    convert_hash = lambda x: conversion_dict.get(x, x)
    convert_back_hash = lambda x: conversion_backdict.get(x, x)
    custom_hashes = pd.DataFrame(custom_hashes, columns=["new", "old"])
    custom_hashes = custom_hashes.drop_duplicates(subset='old', keep='first')
    newlibs = dfs['libs'].merge(custom_hashes, left_on="hash", right_on="old")
    onlynew = pd.DataFrame(newlibs['new'].unique(), columns=['new']).reset_index()
    mapping = newlibs.merge(onlynew, on="new")[["id", "index"]].rename(columns={"id": "old_id", "index":"new_id"})
    dfs['app_libs'] = dfs['app_libs'].merge(mapping, left_on="lib_id", right_on="old_id")[["app_id", "new_id"]].rename(columns={"new_id": "lib_id"})
    dfs['libs'] = onlynew.rename(columns={"index":"id", "new":"hash"})
    dfs['lib_names'] = dfs['lib_names'].merge(mapping, left_on="lib_id", right_on="old_id").drop(columns=["lib_id", "old_id"]).rename(columns={"new_id":"lib_id"})
    #
    dfs['maven_truth_hashes']
    newlibs = dfs['maven_truth_hashes'].merge(custom_hashes, left_on="hash", right_on="old")
    onlynew = pd.DataFrame(newlibs['new'].unique(), columns=['new']).reset_index()
    mapping = newlibs.merge(onlynew, on="new")[["id", "index"]].rename(columns={"id": "old_id", "index":"new_id"})
    dfs['maven_modules_hashes'] = dfs['maven_modules_hashes'].merge(mapping, left_on="hash_id", right_on="old_id")[["module_id", "new_id"]].rename(columns={"new_id": "hash_id"})   
    dfs['maven_truth_hashes'] = newlibs.merge(onlynew, on="new").drop_duplicates(subset="new", keep="first")[['index','relinked_hash','name','new']].rename(columns={"new":"hash", "index":"id"})
    #



app_libs = dfs['app_libs'].merge(dfs['libs'], left_on='lib_id', right_on='id').drop(columns=['id'])
app_libs = app_libs.merge(dfs['apps'][['id', 'app_name']], left_on='app_id', right_on='id').drop(columns=["id"])
non_duplicate_lib_names = dfs['lib_names'].drop_duplicates(subset='lib_id', keep='first')


print("SOME STATISTICS")
print("Total apps:", len(dfs['apps']))
print("Apps with libraries:", len(set(dfs['app_libs']['app_id'])))
print("Out of the ", len(dfs['app_libs']), "extracted libraires, ", len(dfs['libs']), " are unique")



# most popular hashes
most_popular_hashes = app_libs.groupby('hash').size().reset_index().sort_values(by=0).rename(columns={0:"count"})
assert(sum(most_popular_hashes["count"]) == len(app_libs))

print("Top 5 most popular hashes:", most_popular_hashes[-5:])
for x in [50, 500, 5000]:
    e = sum(most_popular_hashes["count"][-x:]) / sum(most_popular_hashes["count"]) * 100
    print(f"Top {x} library hashes account for ", e, "% of all native libraries")

# libs per app
libs_per_app = app_libs.groupby("app_name").size().reset_index().sort_values(by=0).rename(columns={0:"count"})
print("Top 3 apps with most libraries:", libs_per_app[-3:])


#### PLAYSTORE APPS
play_app_libs = app_libs.merge(dfs['playstore_metadata'], on='app_id')
print("Oldest 3 apps:", play_app_libs.sort_values('updatetimestamp')[['app_name', 'updatetimestamp', 'lastupdatedate']][:3])
print("Number of apps on playstore:", len(dfs['playstore_metadata'])) 


### MAVEN
maven = dfs['maven_modules_hashes'].merge(dfs['maven_truth_modules'].rename(columns={"name":"module_name"}), left_on='module_id', right_on='id').drop(columns=['id'])
maven = maven.merge(dfs['maven_truth_hashes'].rename(columns={"name":"lib_name"}), left_on='hash_id', right_on='id').drop(columns=['id'])
dfs['maven_source']['module_id'] = dfs['maven_source']['module_id'].astype(int) # terrible fix for some module_ids being strings
maven = maven.merge(dfs['maven_source'], on='module_id', how="left")
maven["timestamp"] = maven["date"].apply(lambda x: datetime.strptime(x.split(":")[0], "%Y-%m-%d %H").timestamp())
maven = maven.add_prefix("maven_")

print("Total maven modules (with at least one native lib?): ", len(dfs['maven_truth_modules']))
print("Total maven hashes (with at least one native lib?): ", len(dfs['maven_truth_hashes']))
print("Total maven modules (with at least one native lib?) ignoring versions: ", len(maven.groupby("maven_artifact").size()))
print("Most common libs on maven, by hash: ", maven.groupby("maven_hash").size().reset_index().sort_values(by=0).rename(columns={0:"count"})[-10:].merge(dfs['maven_truth_hashes'][["hash", "name"]], left_on="maven_hash", right_on="hash")[["hash", "name", "count"]])
print("Most common libs on maven, by name: ", maven.groupby("maven_lib_name").size().reset_index().sort_values(by=0).rename(columns={0:"count"})[-10:])


# maven duplicates
old_maven_len = len(maven)
maven = maven.sort_values(by="maven_date").drop_duplicates(subset="maven_hash", keep="first")
# for multiple lib names only grab biggest dev
maven_true = maven.copy()
lib_counts = maven_true.groupby('maven_lib_name').filter(lambda x: len(x['maven_developer'].unique()) > 1)
main_devs = (lib_counts.groupby(['maven_lib_name', 'maven_developer']).size().reset_index(name='count')
                        .sort_values('count', ascending=False).groupby('maven_lib_name').first())
mask = maven_true.apply(lambda x: not (x['maven_lib_name'] in main_devs.index and x['maven_developer'] != main_devs.loc[x['maven_lib_name']]['maven_developer']), axis=1)
maven_true = maven_true[mask]
print(len(maven_true))

# TODO: maybe add all hashes are the first seen 

print("\x1b[31;1mRemoving ", len(maven) - len(maven_true), "hashes because multiple modules using them!\x1b[0m (", (1. - len(maven_true) / len(maven)) * 100,"% of total)")



# maven stats
maven_libs_on_our_database = maven_true.merge(dfs['libs'].rename(columns={"id":"lib_id"}), left_on="maven_hash", right_on='hash').drop(columns=["maven_hash"])
print("Total individual hashes in our db we match from maven: ", len(maven_libs_on_our_database) / len(dfs['libs']) * 100, "%")
tot_play = set(play_app_libs['hash'].unique())
tot_maven = set(maven_true['maven_hash'].unique())
print("Total individual hashes in our db we match from maven (play store): ", len(tot_play.intersection(tot_maven)) / len(tot_play) * 100, "%")

maven_usages = maven_libs_on_our_database.merge(app_libs, on="lib_id")
print("Total usage of hashes we match from maven: ", len(maven_usages) / len(app_libs) * 100, "%")

play_maven_usages = maven_libs_on_our_database.merge(play_app_libs, on="lib_id")
print("Total usage of hashes we match from maven (play store): ", len(play_maven_usages) / len(play_app_libs) * 100, "%")


# popular libs
popular_hashes = app_libs.groupby('hash').size().reset_index().sort_values(by=0).rename(columns={0:"count"})
popular_libs = popular_hashes.merge(dfs['libs'], on='hash').rename(columns={"id":"lib_id"})
popular_libs = popular_libs.merge(non_duplicate_lib_names.drop(columns=["id"]), on="lib_id")

play_popular_hashes = play_app_libs.groupby('hash').size().reset_index().sort_values(by=0).rename(columns={0:"count"})
play_popular_libs = play_popular_hashes.merge(dfs['libs'], on='hash').rename(columns={"id":"lib_id"})
play_popular_libs = play_popular_libs.merge(non_duplicate_lib_names.drop(columns=["id"]), on="lib_id").sort_values(by="count")

assert(sum(list(popular_libs['count'])) == len(app_libs))
assert(sum(list(play_popular_libs['count'])) == len(play_app_libs))

print("Top 3 used hashes:", popular_libs[-3:][["hash","count","name"]])
print("Top 3 used hashes in the play store:", play_popular_libs[-3:][["hash","count","name"]])




# top hashes we do not match from maven
popular_libs['maven'] = list(popular_libs['hash'].isin(maven['maven_hash']))
play_popular_libs['maven'] = list(play_popular_libs['hash'].isin(maven_true['maven_hash']))
print("Top play store hashes not on maven:", play_popular_libs[play_popular_libs['maven'] == False][-20:])
play_popular_libs[-1000:].to_csv('output.csv', columns=['count','name','maven'], index=False)
print("Top play store lib names not on maven:", play_popular_libs[play_popular_libs['maven'] == False].groupby("name").agg(count=("count", "sum")).sort_values(by="count", ascending=False)[:20])



# #find most popular lib in maven_true
# maven_true.groupby("maven_lib_name").size().reset_index().sort_values(by=0).rename(columns={0:"count"})[-50:]
# #which maven module has libvlc.so?
# maven_true[maven_true["maven_lib_name"] == "libvlc.so"]["maven_groupname"].to_list()
# #librarian common libraries:
# librarian_maven_hashes = set(["4dbc1fcf2bb88eb0c6cd3ca2018b06bcd8f9d57f191c16b36e97a33267866a4f", "5a2ed3e86ecc7dc63a4bc7c5474312a36793dd20e611f18615b707d6a9c412a6", "66ee5d7ce1c867f14f600f3d57cf288dfa2d47e851ea14b252a7dff2d0a7cbae", "67adefffcabac71bb0147bb9cde6b78698a2581ef2cdd26402d75c967b60076e", "7fae32dc2ce78088fc5a4ad53bdaa383b979e451e8c1bf496d740fc3d643f64f", "979e1d74cc6a8934abeab24bb986f71b1a4f8f1168981ba80add914999ec7261", "9916c89d5edfd4a9e863d84de67426de07ab3db79e728aeec0e0141c4109afe5", "accedc08479c9184abcb9fe3ed87a0a4ef6876ff265709cd23b855df1c872777", "d467d64ca41358896bdac7186579df26dfc55c99cd757425c705f503274bd17f", "ff7f64c38493121af25069bca89096658b2c8ea08d5237bd81862bf827e95287"])
# maven_usages_librarian = maven_usages[maven_usages.apply(lambda x: x['hash_x'] in librarian_maven_hashes, axis=1)]
# print(maven_usages_librarian.groupby("hash_x").first().reset_index()[["hash_x", "maven_module_name", "maven_artifact", "maven_version", "maven_lib_name", "maven_date"]].to_string())



# HERE








##########################
### tables
##########################

# table of most popular maven artifacts used
popular_artifacts = play_maven_usages.groupby("maven_artifact").agg(count=("maven_artifact", "size"), developer=("maven_developer", "first")).sort_values(by="count").reset_index() # we should sum imagepipeline and imagepipeline-native (at least we did on the paper)
rows = "\n".join([row['developer'].title() + " & " + row['maven_artifact'] + " & " + f"{row['count']:,}" + " \\\\" for row in popular_artifacts[:-31:-1].iloc]) 
print(rows)

# table of ground truth sources
s = maven_usages.groupby("maven_source").agg(count=("maven_source", "size"), source=("maven_source", "first"))
s['playstore_count'] = play_maven_usages.groupby("maven_source").size()
s.loc["Unknown"] = [len(app_libs) - len(maven_usages), "Unknown", len(play_app_libs) - len(play_maven_usages)]
s['perc'] = s['count'] / s['count'].sum() * 100
s['playstore_perc'] = s['playstore_count'] / s['playstore_count'].sum() * 100
rows = "\n".join([f"{row['source'].title()} & {row['count']:,} & ({row['perc']:.2f}\\%) & {row['playstore_count']:,} & ({row['playstore_perc']:.2f}\\%) \\\\" for row in s.sort_values(by="count").iloc])
print(rows)



# experiment on incorrect library names on Maven (threats to validity)
# TODO: fix this as droids_maven is not defined yet
droids_lib_ids = set(droids_maven[droids_maven["maven_lib_name"] == "libpl_droidsonroids_gif.so"]["lib_id"].tolist())
droids_dev_names = dfs['lib_names'].query("lib_id in @droids_lib_ids")['name'].tolist()
counts = collections.defaultdict(int)
for lib in droids_dev_names: counts[lib] += 1
print("Number of renamed droids libraries:", dict(counts))


# experiment on static compilation (openssl greps)
with open("maven_openssl.txt", "r") as f:
    versions = {line.split(":")[0]:line.split(":")[1].strip() for line in f.readlines()}
versions_hashes = set(versions.keys())
ssl_lib_names = maven.query("maven_hash in @versions_hashes")["maven_lib_name"].reset_index()
ssl_lib_names_cnts = ssl_lib_names.groupby("maven_lib_name").size().sort_values().to_dict()
actually_named_ssl_cnts = list(filter(lambda k: "ssl" in k[0], ssl_lib_names_cnts.items()))
correct_name_total = sum([k[1] for k in actually_named_ssl_cnts])
any_name_total = sum(ssl_lib_names_cnts.values())
print(f"{any_name_total} openssl libraries in maven but only {correct_name_total} are called something like 'libssl.so'")
# continue from here
ssl_artifact_names = maven.query("maven_hash in @versions_hashes")["maven_artifact"].unique()
actual_ssl = list(filter(lambda x: "ssl" in x, list(ssl_artifact_names)))
print(f"{len(ssl_artifact_names)} artifacts that ship openssl in Maven but only {len(actual_ssl)} are named something like 'openssl'")




# fdroids
fdroids_sources = []
if not os.path.exists("fdroid_index.xml"):
    os.system("wget https://f-droid.org/repo/index.xml -O fdroid_index.xml")
import xml.etree.ElementTree as ET
root = ET.parse('fdroid_index.xml').getroot().findall('application')
for app in root:
    fdroids_sources += [[app.attrib['id'], app.find('source').text]]
fdroids_sources = pd.DataFrame(fdroids_sources, columns=["app_name", "app_repo"])

fdroids_generals = app_libs.merge(fdroids_sources, on="app_name")
fdroids_mavens = maven_usages.merge(fdroids_sources, on="app_name")
fdroids_not_in_maven = fdroids_generals.query("hash not in @maven_true['maven_hash']")

# fdroid stats 
print(f"Total apps in fdroid: {len(fdroids_sources)}")
print(f"Total apps in fdroid that use a native lib in our db: {len(fdroids_generals.groupby('app_name').size())}")
print(f"Total unique native libs in fdroid: {len(fdroids_generals.groupby('hash').size())}")
print(f"Total unique maven native libs in fdroid: {len(fdroids_mavens.groupby('hash_x').size())}")
print(f"Total native lib usages in fdroid: {len(fdroids_generals)}")
print(f"Total native lib usages in maven in fdroid: {len(fdroids_mavens)}")

print("Top fdroid native libs not found in maven:")
native_libs_not_in_maven = fdroids_not_in_maven.merge(non_duplicate_lib_names)
print(native_libs_not_in_maven.groupby("name").size().sort_values()[-10:])





# RQ1 manual fdroid evaluation
fdroids_mavens["download_lib"] = fdroids_mavens["hash_x"].apply(lambda x: "http://m00e04c1a3990.dyn.epfl.ch:7999/"+x)
fdroids_mavens["evaluated"] = -1 # -1: not checked, 0: bad result, 1: correct result

fdroids_hash_counts = fdroids_mavens.groupby("hash_x").size().reset_index().rename(columns={0:"count"})
fdroids_mavens = fdroids_mavens.merge(fdroids_hash_counts).sort_values(by=["count", "hash_x"], ascending=False)

if os.path.exists("fdroids_mavens_evaluated.csv"):
    manual_eval = pd.read_csv("fdroids_mavens_evaluated.csv")[["evaluated", "maven_lib_name", "download_lib"]]
    manual_eval["hash_x"] = manual_eval["download_lib"].apply(lambda x: x.split("/")[-1])
    manual_eval.drop(columns=["download_lib"], inplace=True)
    group_results = manual_eval.groupby("hash_x").agg(evaluated=("evaluated", "first"), name=("maven_lib_name", "first"), count=("hash_x", "size"))
    num_correct = group_results.query("evaluated == 1")
    num_correct_usages = manual_eval.query("evaluated == 1")
    print("Correctly evaluated: ", len(num_correct), "out of ", len(group_results), "ratio: ", len(num_correct) / len(group_results))
    print("Correctly evaluated (by usage): ", len(num_correct_usages), "out of ", len(manual_eval), "ratio: ", len(num_correct_usages) / len(manual_eval))
    print("Worst offenders: ")
    print(group_results.query("evaluated == 0").sort_values(by="count", ascending=False)[:15][["count", "name"]])
    print("Worst offenders by name: ")
    print(group_results.query("evaluated == 0").groupby("name").agg(count=("count", "sum")).sort_values(by="count", ascending=False)[:15])
    # update fdroids_mavens
    fdroids_mavens2 = fdroids_mavens.drop(columns=["evaluated", "count"])
    fdroids_mavens2 = fdroids_mavens2.merge(group_results, on="hash_x", how="left")


fdroids_mavens[["evaluated", "count", "app_name", "app_repo", "maven_groupname", "maven_repository", "maven_lib_name", "maven_artifact", "maven_version", "download_lib"]].to_csv("fdroids_mavens.csv")
fdroids_mavens2[["evaluated", "count", "app_name",	"app_repo",	"maven_groupname", "maven_repository",	"maven_lib_name",	"maven_artifact",	"maven_version",	"download_lib"]].to_csv("fdroids_mavens2.csv")


popular_fdroids = fdroids_generals.groupby('hash').size().reset_index().sort_values(by=0).rename(columns={0:"count"})
popular_fdroids['maven'] = list(popular_fdroids['hash'].isin(maven['maven_hash']))
print("Top fdroids hashes not on maven:", popular_fdroids[popular_fdroids['maven'] == False][-20:])


fdroids_mavens.query("maven_lib_name == 'libglog.so'")["app_repo"]


### "file" experiment

# find . | sort | parallel -j 32 'file {} >> ../file_results'



##### HERE



#########################################
#########################################
#########################################
# plots
#########################################
#########################################
#########################################
import seaborn as sns
import matplotlib.pyplot as plt
os.system("mkdir -p plots")
sns.set(style="whitegrid")
sns.set(font_scale=1.3)


### first plot: distribution of how popular hashes are
most_popular_hashes_plot = most_popular_hashes[-500:].copy().rename(columns={"hash":"hash_id"})
most_popular_hashes_plot['hash_id'] = range(len(most_popular_hashes_plot))
plt.figure(figsize=(10, 6))
ax = sns.lineplot(data=most_popular_hashes_plot.iloc[::-1], x='hash_id', y='count')
plt.xlabel("sha256(library)")
plt.ylabel("number of apps")
ax.invert_xaxis()
plt.xticks([])
plt.savefig("plots/popular_hashes.pdf", dpi=300)
#plt.show()
plt.clf() 

popular_play_maven_usages = play_maven_usages.query("downloads > 10000000000")
np.mean((time.time() - popular_play_maven_usages['maven_timestamp']) / (60*60*24*365))

### average age of the usage of a library
range_dloads = [1e3, 1e5, 1e7]
yrs_from_app_release,yrs_from_now = {}, {}
for dloads in range_dloads:
    popular_play_maven_usages = play_maven_usages.query("downloads > " + str(dloads))
    yrs_from_app_release[dloads] = (popular_play_maven_usages['updatetimestamp'] - popular_play_maven_usages['maven_timestamp']) / (60*60*24*365)
    yrs_from_now[dloads] = (time.time() - popular_play_maven_usages['maven_timestamp']) / (60*60*24*365)
    print("Average age of a library from app release: ", np.mean(yrs_from_app_release[dloads]), " years")
    print("Average age of a library from now: ", np.mean(yrs_from_now[dloads]), " years")

plt.figure(figsize=(10, 6))
for dloads in range_dloads:
    sns.kdeplot(data=yrs_from_now[dloads], bw_adjust=3, clip=(0, 1e10), fill=True, label=f"{int(dloads)} downloads")
plt.legend()
plt.xlabel("Years")
plt.ylabel("Density")
plt.title("Age of Android native libraries (Gaussian kernel estimation)")
plt.savefig("plots/library_age_kde.pdf", dpi=600)
# plt.show()
plt.clf() 

for dloads in range_dloads:
    sns.ecdfplot(data=list(filter(lambda x: x>0,yrs_from_now[dloads])), label=f"{int(dloads)} downloads")
plt.legend()
plt.xlabel("Years")
plt.ylabel("Probability")
plt.title("Age of a Android native libraries (Cumulative Distribution)")
plt.savefig("plots/library_age_ecdf.pdf", dpi=600)
# plt.show()
plt.clf() 


### pie chart of sources (play store)
#sources_dist = __play_maven_usages.groupby("maven_source").size()
#sources_dist["Unknown"] = len(_play_app_libs) - len(__play_maven_usages)
sources_dist = play_maven_usages.groupby("maven_source").size()
sources_dist["Unknown"] = len(play_app_libs) - len(play_maven_usages)
sources_dist = sources_dist.iloc[[0,3,1,4,2,5,6,7,8]]
pcts = sources_dist/sources_dist.sum()*100
labels = [f"{idx} ({pct:.2f}%)" for pct, val, idx in zip(pcts, sources_dist, sources_dist.index)]
plt.pie(sources_dist, labels=labels, explode=[0.05]*len(pcts), startangle=-20, wedgeprops={'linewidth': 1}, textprops={'fontsize':9})
#sources_dist.sort_values().plot(kind='pie',
#         figsize=(10, 8),
#         labels=labels,
#         textprops={'fontsize': 16}, # Increase font size of labels
#         title='Distribution of sources of native libraries in the Play Store',)
plt.savefig("plots/sources_pie_chart.pdf", dpi=600)
#plt.show()
plt.clf()



#########################################
#########################################
#########################################
# RQ4 how many apps are vulnerable
#########################################
#########################################
#########################################


# droids cve
#droids_maven = maven_usages[maven_usages["maven_lib_name"] == 'libpl_droidsonroids_gif.so']
droids_maven = maven_usages[maven_usages["maven_artifact"] == 'android-gif-drawable']
droids_vulns = droids_maven[droids_maven["maven_version"].apply(Version) < Version("1.2.18")]
droids_maven_playstore = droids_maven.merge(dfs['playstore_metadata'], on="app_id")
droids_vulns_playstore = droids_vulns.merge(dfs['playstore_metadata'], on="app_id").sort_values(by="downloads")
print(f"{len(set(droids_vulns['app_name']))}/{len(set(droids_maven['app_name']))} {len(set(droids_vulns['app_name'])) / len(set(droids_maven['app_name'])) * 100:.2f}% are vulnerable to droids on roids")
print(f"{len(set(droids_vulns_playstore['app_name']))}/{len(set(droids_maven_playstore['app_name']))} {len(set(droids_vulns_playstore['app_name'])) / len(set(droids_maven_playstore['app_name'])) * 100:.2f}% are vulnerable to droids on roids on the playstore")


# pdfium cve
pdfium_maven = maven_usages.query("maven_artifact.str.lower().str.contains('pdfium')")
cve_2018_6120 = pdfium_maven.query(f"maven_timestamp <= {datetime.strptime('2018-03-10', '%Y-%m-%d').timestamp()}")
play_pdfium_maven = play_maven_usages.query("maven_artifact.str.lower().str.contains('pdfium')")
play_cve_2018_6120 = play_pdfium_maven.query(f"maven_timestamp <= {datetime.strptime('2018-03-10', '%Y-%m-%d').timestamp()}")
print(f"{len(set(cve_2018_6120['app_name']))}/{len(set(pdfium_maven['app_name']))} {len(set(cve_2018_6120['app_name'])) / len(set(pdfium_maven['app_name'])) * 100:.2f}%  apps are vulnerable to CVE-2018-6120")
print(f"{len(set(play_cve_2018_6120['app_name']))}/{len(set(play_pdfium_maven['app_name']))} {len(set(play_cve_2018_6120['app_name'])) / len(set(play_pdfium_maven['app_name'])) * 100:.2f}%  apps are vulnerable to CVE-2018-6120 on the playstore")


# ucrop libpng cve
ucrop_vulns = maven_usages.query('maven_artifact.str.lower() == \'ucrop\'')
ucrop_vulns_playstore = play_maven_usages.query('maven_artifact.str.lower() == \'ucrop\'')
print(f"100% of {len(ucrop_vulns)} are vulnerable to ucrop")
print(f"100% of {len(ucrop_vulns_playstore)} in the playstore are vulnerable to ucrop")


# webp cve
webp_libnames = dfs['lib_names'].query("name == 'libwebp.so'").drop_duplicates(subset='lib_id', keep='first')
webp_apps = webp_libnames.merge(app_libs, on="lib_id")[["hash", "app_id", "app_name"]]
webp_apps_playstore = webp_apps.merge(dfs['playstore_metadata'])
webp_libs_hashes = list(set(webp_apps['hash'].to_list()))
open("hashes_to_copy.txt", "w").write("\n".join(map(convert_back_hash, webp_libs_hashes)))
# rsync -azv --files-from=hashes_to_copy.txt luca@10.0.0.14:acid/libs/ libs/

vuln_hashes = []
for f in webp_libs_hashes:
    version = subprocess.check_output(f"r2 -qc 's 0; s sym.WebPGetDecoderVersion; aei; aeim; aes 3; aer x0' libs/{convert_back_hash(f)} 2>/dev/null", shell=True)
    if len(version.decode().split("\n")) > 2: continue
    int_version = int(version, 16)
    version = Version(f"{int_version >> 16}.{(int_version >> 8) & 0xff}.{int_version & 0xff}")
    print(version)
    if version < Version("1.0.1"):
        vuln_hashes += [f]

webp_vulns = webp_apps[webp_apps['hash'].isin(vuln_hashes)]
webp_vulns_playstore = webp_vulns.merge(dfs['playstore_metadata'][['app_id', 'downloads']], how='left').fillna({"downloads":-1})
webp_vulns_playstore[["app_name", "downloads"]].sort_values(by="downloads")[-40:]
print(f"{len(set(webp_vulns['app_name']))}/{len(set(webp_apps['app_name']))} {len(set(webp_vulns['app_name'])) / len(set(webp_apps['app_name'])) * 100:.2f}% are vulnerable to webp on roids")
print(f"{len(set(webp_vulns_playstore.query('downloads != -1')['app_name']))}/{len(set(webp_apps_playstore['app_name']))} {len(set(webp_vulns_playstore.query('downloads != -1')['app_name'])) / len(set(webp_apps_playstore['app_name'])) * 100:.2f}% are vulnerable to webp on roids on the playstore")


# react native folly cve
folly_maven = maven_usages.query("maven_artifact == 'folly'")
folly_maven = folly_maven[~folly_maven["maven_version"].str.contains('rc0')]
folly_vulns = folly_maven[folly_maven["maven_version"].apply(Version) < Version("2021.07.22.00")]
folly_maven_playstore = folly_maven.merge(dfs['playstore_metadata'], on="app_id")
folly_vulns_playstore = folly_vulns.merge(dfs['playstore_metadata'], on="app_id").sort_values(by="downloads")
folly_vulns_playstore[["app_name", "downloads"]]
print(f"{len(set(folly_vulns['app_name']))}/{len(set(folly_maven['app_name']))} {len(set(folly_vulns['app_name'])) / len(set(folly_maven['app_name'])) * 100:.2f}% are vulnerable to folly on roids")
print(f"{len(set(folly_vulns_playstore['app_name']))}/{len(set(folly_maven_playstore['app_name']))} {len(set(folly_vulns_playstore['app_name'])) / len(set(folly_maven_playstore['app_name'])) * 100:.2f}% are vulnerable to folly on roids on the playstore")



libs = [
("libdroidsonroids",  "CVE-2019-11932", droids_vulns_playstore, droids_maven_playstore),
("libpdfium", "CVE-2020-6513", play_cve_2018_6120, play_pdfium_maven),
("uCrop", "CVE-2017-12652", ucrop_vulns_playstore, ucrop_vulns_playstore),
("libwebp", "CVE-2018-25013", webp_vulns_playstore, webp_apps_playstore),
("libfolly", "CVE-2021-2403", folly_vulns_playstore, folly_maven_playstore),
]


rows = "\n".join([f"{l[0]} & {l[1]} & {' & '.join([f"{len(l[2].query(f"downloads > {x}")['app_name'].unique()):,}" for x in [1e8, 1e7, 1e6, -1]])} & ({len(l[2].query("downloads != -1")['app_name'].unique())/len(l[3].query("downloads != -1")['app_name'].unique())*100:.2f}\\%) & {len(l[3]['app_name'].unique()):,} \\\\" for l in libs]) 
print(rows)



# ffmpeg CVE

vuln_hashes = []
ffmpeg_libnames = dfs['lib_names'].query("name.str.lower().str.contains('ffmpeg')").drop_duplicates(subset='lib_id', keep='first')
ffmpeg_apps = ffmpeg_libnames.merge(app_libs, on="lib_id")[["hash", "app_id", "app_name"]]
ffmpeg_apps_playstore = ffmpeg_apps.merge(dfs['playstore_metadata'])
ffmpeg_libs_hashes = list(set(ffmpeg_apps['hash'].to_list()))
open("hashes_to_copy.txt", "w").write("\n".join(ffmpeg_libs_hashes))
vuln_hashes = []
for f in ffmpeg_libs_hashes:
    version = subprocess.check_output(f"r2 -qc 's 0; s sym.avformat_version; aei; aeim; aes 3; aer x0' libs/{f} 2>/dev/null", shell=True)
    if len(version.decode().split("\n")) > 2: continue
    int_version = int(version, 16)
    if int_version == 0: continue
    version = Version(f"{int_version >> 16}.{(int_version >> 8) & 0xff}.{int_version & 0xff}")
    print(f)
    print(version)
    # TODO if version <  x.x.x
    # but you would need to correlate versions with dates

#ffmpeg_vulns = ffmpeg_apps[ffmpeg_apps['hash'].isin(vuln_hashes)]
#ffmpeg_vulns_playstore = ffmpeg_vulns.merge(dfs['playstore_metadata'][['app_id', 'downloads']], how='left').fillna({"downloads":-1})
#ffmpeg_vulns_playstore[["app_name", "downloads"]].sort_values(by="downloads")[-40:]
#print(f"{len(ffmpeg_vulns)}/{len(ffmpeg_apps)} {len(ffmpeg_vulns) / len(ffmpeg_apps) * 100:.2f}% are vulnerable to ffmpeg")
#print(f"{len(ffmpeg_vulns_playstore.query('downloads != -1'))}/{len(ffmpeg_apps_playstore)} {len(ffmpeg_vulns_playstore.query('downloads != -1')) / len(ffmpeg_apps_playstore) * 100:.2f}% are vulnerable to ffmpeg on roids on the playstore")



### checksec histogram
#  checksec --dir=libs > checksec_results
# this is broken if you use the custom hashes as it uses real file hashes to compare. i
if not os.path.exists("checksec_results"):
    os.system("checksec --dir=libs > checksec_results")
else:
    lines = open("checksec_results", "r").readlines()
    mylist = []
    for l in lines[1:]:
        hash = convert_hash(l.split("libs/")[1].strip())
        canary = "Canary" in l
        nx = "NX enabled" in l
        relro = "Full RELRO" in l
        fortify = "[32mYes" in l
        mylist += [[hash, canary, nx, relro, fortify]]
    checksec_data = pd.DataFrame(mylist, columns=["hash", "canary", "nx", "relro", "fortify"])
    checksec_play_app_libs = play_app_libs.merge(checksec_data, on="hash")
    perc_no_canary  = len(checksec_play_app_libs.query("canary  == False")) / len(checksec_play_app_libs) * 100
    perc_no_relro   = len(checksec_play_app_libs.query("relro == False")) / len(checksec_play_app_libs) * 100
    perc_no_nx      = len(checksec_play_app_libs.query("nx  == False")) / len(checksec_play_app_libs) * 100
    perc_no_fortify = len(checksec_play_app_libs.query("fortify == False")) / len(checksec_play_app_libs) * 100
    print(f"Percentages {perc_no_canary=}% {perc_no_nx=}% {perc_no_relro=}% {perc_no_fortify=}%")
    mylist = [perc_no_nx, perc_no_canary, perc_no_relro, perc_no_fortify]
    #
    plot_code = "\\pgfplotsset{testbar/.style={\n xbar stacked,\n width=.45\\textwidth,\n xmin=0,xmax=100,\n ytick = data, yticklabels = {NX,Canary,Full RELRO,Fortify},\n bar width=5mm, y=7mm,\n nodes near coords={%\n \\pgfmathfloatparse{\\pgfplotspointmeta}%\n \\pgfmathfloattofixed{\\pgfmathresult}%\n \\ifdim\\pgfmathresult pt<5.0pt %\n \\else\n \\pgfmathprintnumber{\\pgfplotspointmeta}\\%\n \\fi\n }, \n enlarge y limits=0.2, \n axis line style={draw=none}, \n xmajorticks=false,\n yticklabel style={xshift=-0.5em}, \n }}\n\n \\begin{tikzpicture}\n \\begin{axis}[testbar]\n"
    plot_code += f"\\addplot[draw=blue, fill=blue!30] coordinates{{{' '.join([f"({100-x:.1f}, {e})" for e,x in enumerate(mylist)])}}};"
    plot_code += f"\\addplot[draw=red, fill=red!30] coordinates{{{' '.join([f"({x:.1f}, {e})" for e,x in enumerate(mylist)])}}};"
    plot_code += "\\end{axis}\n \\end{tikzpicture}\n"
    #
    open("plots/checksec.tex", "w").write(plot_code)






###########################
#### CENTRAL FIGURE
###########################
final_plot_data = []

if not os.path.exists("libpng_grep_libs.txt"):
    print("error: you need to run the greps.sh script first!")
else:
    if not os.path.exists("libpng_versions.csv"):
        with tempfile.TemporaryDirectory() as tmpdirname:
            os.system(f"git clone --bare --filter=blob:none https://github.com/pnggroup/libpng {tmpdirname}; pushd {tmpdirname}; git log --tags --simplify-by-decoration --pretty='format:%ct %D' | sed 's/ tag: ./,/' > libpng_versions.csv; popd; cp {tmpdirname}/libpng_versions.csv ./")
    lines = open("libpng_versions.csv", "r").readlines()
    libpng_versions = {l.split(",")[1].strip() : l.split(",")[0].strip() for l in lines if "," in l}
    libpng_libs = {line.split(":")[0]: line.split(":")[1].strip() for line in open("libpng_grep_libs.txt", "r")}
    plot_data = pd.DataFrame([
        [convert_hash(binary), int(timestamp), version]
        for binary, version in libpng_libs.items()
        if (timestamp := libpng_versions.get(version, "0")) != "0"
        ], columns=["hash", "timestamp", "version"])
    plot_data = plot_data.sort_values(by="timestamp").drop_duplicates(subset="hash", keep="first")
    plot_data = plot_data.merge(play_app_libs, on="hash")
    data = sorted(plot_data['timestamp'].tolist())
    cves = [("CVE-2017-12652", "2017-08-07"), ("CVE-2019-7317", "2019-02-04")]
    cves = [("CVE-2019-7317", "2019-02-04")]
    perc_vuln = bisect_left(data, datetime.strptime(cves[-1][1],"%Y-%m-%d").timestamp()) / len(data) * 100
    versions = plot_data.groupby("timestamp").agg(count=("timestamp", "size"), version=("version", "first")).sort_values(by="count")[-2:].to_records(index=True)
    final_plot_data += [{"name":"LibPNG", "data":data, "cves":cves, "perc_vuln":perc_vuln, "versions":versions}]


if not os.path.exists("jpegturbo_grep_libs.txt"):
    print("error: you need to run the greps.sh script first!")
else:
    if not os.path.exists("jpegturbo_versions.csv"):
        with tempfile.TemporaryDirectory() as tmpdirname:
            os.system(f"git clone --bare --filter=blob:none https://github.com/libjpeg-turbo/libjpeg-turbo {tmpdirname}; pushd {tmpdirname}; git log --tags --simplify-by-decoration --pretty='format:%ct %D' | sed 's/ tag: /,/' > jpegturbo_versions.csv; popd; cp {tmpdirname}/jpegturbo_versions.csv ./")
    lines = open("jpegturbo_versions.csv", "r").readlines()
    jpegturbo_versions = {l.split(",")[1].strip() : l.split(",")[0].strip() for l in lines if "," in l}
    jpegturbo_libs = {line.split(":")[0]: line.split(":")[1].strip() for line in open("jpegturbo_grep_libs.txt", "r")}
    plot_data = pd.DataFrame([
        [convert_hash(binary), int(timestamp), version]
        for binary, version in jpegturbo_libs.items()
        if (timestamp := jpegturbo_versions.get(version, "0")) != "0"
        ], columns=["hash", "timestamp", "version"])
    plot_data = plot_data.sort_values(by="timestamp").drop_duplicates(subset="hash", keep="first")
    plot_data = plot_data.merge(play_app_libs, on="hash")
    data = sorted(plot_data['timestamp'].tolist())
    cves = [("CVE-2020-17541", "2020-08-13"), ("CVE-2023-2804", "2023-05-19")]
    cves = [("CVE-2023-2804", "2023-05-19")]
    perc_vuln = bisect_left(data, datetime.strptime(cves[-1][1],"%Y-%m-%d").timestamp()) / len(data) * 100
    versions = plot_data.groupby("timestamp").agg(count=("timestamp", "size"), version=("version", "first")).sort_values(by="count")[-3:].to_records(index=True)
    final_plot_data += [{"name":"Jpeg Turbo", "data":data, "cves":cves, "perc_vuln":perc_vuln, "versions":versions}]


if not os.path.exists("opencv_grep_libs.txt"):
    print("error: you need to run the greps.sh script first!")
else:
    if not os.path.exists("opencv_versions.csv"):
        with tempfile.TemporaryDirectory() as tmpdirname:
            os.system(f"git clone --bare --filter=blob:none https://github.com/opencv/opencv {tmpdirname}; pushd {tmpdirname}; git log --tags --simplify-by-decoration --pretty='format:%ct %D' | sed 's/ tag: /,/' > opencv_versions.csv; popd; cp {tmpdirname}/opencv_versions.csv ./")
    lines = open("opencv_versions.csv", "r").readlines()
    opencv_versions = {l.split(",")[1].strip() : l.split(",")[0].strip() for l in lines if "," in l}
    opencv_libs = {line.split(":")[0]: line.split(":")[1].strip() for line in open("opencv_grep_libs.txt", "r")}
    plot_data = pd.DataFrame([
        [convert_hash(binary), int(timestamp), version]
        for binary, version in opencv_libs.items()
        if (timestamp := opencv_versions.get(version, "0")) != "0"
        ], columns=["hash", "timestamp", "version"])
    plot_data = plot_data.sort_values(by="timestamp").drop_duplicates(subset="hash", keep="first")
    plot_data = plot_data.merge(play_app_libs, on="hash")
    data = sorted(plot_data['timestamp'].tolist())
    cves = [("CVE-2019-5063", "2019-01-04")]
    perc_vuln = bisect_left(data, datetime.strptime(cves[-1][1],"%Y-%m-%d").timestamp()) / len(data) * 100
    versions = plot_data.groupby("timestamp").agg(count=("timestamp", "size"), version=("version", "first")).sort_values(by="count")
    versions = versions.iloc[[-5, -4, -2, -1]].to_records(index=True)
    final_plot_data += [{"name":"OpenCV", "data":data, "cves":cves, "perc_vuln":perc_vuln, "versions":versions}]


if not os.path.exists("ffmpeg_grep_libs.txt"):
    print("error: you need to run the greps.sh script first!")
else:
    if not os.path.exists("ffmpeg_versions.csv"):
        with tempfile.TemporaryDirectory() as tmpdirname:
            os.system(f"git clone --bare --filter=blob:none https://git.ffmpeg.org/ffmpeg.git {tmpdirname}; pushd {tmpdirname}; git log --tags --simplify-by-decoration --pretty='format:%ct %D' | sed 's/ tag: ./,/' > ffmpeg_versions.csv; popd; cp {tmpdirname}/ffmpeg_versions.csv ./")
    lines = open("ffmpeg_versions.csv", "r").readlines()
    # we skip the first letter of each version as it begins with n or v or something
    ffmpeg_versions = {l.split(",")[1].strip() : l.split(",")[0].strip() for l in lines if "," in l}
    ffmpeg_libs = {line.split(":")[0]: line.split(":")[1].strip() for line in open("ffmpeg_grep_libs.txt", "r")}
    plot_data = pd.DataFrame([
        [convert_hash(binary), int(timestamp), version]
        for binary, version in ffmpeg_libs.items()
        if (timestamp := ffmpeg_versions.get(version, "0")) != "0"
        ], columns=["hash", "timestamp", "version"])
    plot_data = plot_data.sort_values(by="timestamp").drop_duplicates(subset="hash", keep="first")
    plot_data = plot_data.merge(play_app_libs, on="hash")
    data = sorted(plot_data['timestamp'].tolist())
    cves = [("CVE-2017-9993", "2017-06-28"), ("CVE-2020-12284", "2020-04-28")]
    cves = [("CVE-2020-12284", "2020-04-18")]
    perc_vuln = bisect_left(data, datetime.strptime(cves[-1][1],"%Y-%m-%d").timestamp()) / len(data) * 100
    versions = plot_data.groupby("timestamp").agg(count=("timestamp", "size"), version=("version", "first")).sort_values(by="count")[-3:].to_records(index=True)
    final_plot_data += [{"name":"FFmpeg", "data":data, "cves":cves, "perc_vuln":perc_vuln, "versions":versions}]


##### droids data
droids_maven = maven_usages[maven_usages["maven_artifact"] == 'android-gif-drawable']
droids_maven_playstore = droids_maven.merge(dfs['playstore_metadata'], on="app_id")
data = droids_maven_playstore['maven_timestamp']
cves = [("CVE-2019-11932", "2019-06-13")]
perc_vuln = bisect_left(data, datetime.strptime(cves[-1][1],"%Y-%m-%d").timestamp()) / len(data) * 100
versions=droids_maven_playstore.groupby("maven_timestamp").agg(count=("maven_timestamp", "size"), version=("maven_version", "first")).sort_values(by="count")
versions = versions.iloc[[-1,-2,-3,-4,-6,-8]].to_records(index=True)
final_plot_data += [{"name":"Android Gif Drawable", "data":data, "cves":cves, "perc_vuln":perc_vuln, "versions":versions}]


##### pdfium data
# pdfium_maven = maven_usages.query("maven_artifact.str.lower().str.contains('pdfium')")
# cve_2018_6120 = pdfium_maven.query(f"maven_timestamp <= {datetime.strptime('2020-01-18', '%Y-%m-%d').timestamp()}")
# play_pdfium_maven = play_maven_usages.query("maven_artifact.str.lower().str.contains('pdfium')")
# play_cve_2018_6120 = play_pdfium_maven.query(f"maven_timestamp <= {datetime.strptime('2020-01-18', '%Y-%m-%d').timestamp()}")
# data = play_cve_2018_6120['maven_timestamp']
# cves = [("CVE-2018-6120", "2018-06-13")]
#
# final_plot_data += [{"name":"PDFium", "data":data, "cves":cves, "perc_vuln":perc_vuln, "versions":versions}]

##### mega central figure
##### here be dragons
##### plot code
from scipy.stats import gaussian_kde
from collections import Counter
x_min = datetime.strptime("2012-06","%Y-%m").timestamp()
x_max = datetime.strptime("2025-08","%Y-%m").timestamp()
y_min, y_max = 0, 1.1  # 10% padding
# ECDF
for e,library in enumerate(final_plot_data):
    #result_ecdf = ecdf(np.array(library["data"]))
    #y = result_ecdf.cdf.probabilities
    #x = result_ecdf.cdf.quantiles
    #x = list(filter(lambda a: a > x_min, x))
    x = sorted(np.array(library["data"]))
    x = list(filter(lambda a: a > x_min, x))
    # Extract unique numbers and their counts
    compressed_numbers = Counter(x)
    unique_numbers = list(compressed_numbers.keys())
    counts = list(compressed_numbers.values())
    # Sort the unique numbers and their counts
    sorted_indices = np.argsort(unique_numbers)
    sorted_numbers = np.array(unique_numbers)[sorted_indices]
    sorted_counts = np.array(counts)[sorted_indices]
    # Calculate cumulative sum and normalize
    cumulative_counts = np.cumsum(sorted_counts)
    cdf = cumulative_counts / cumulative_counts[-1]
    # Get result as (number, CDF value) pairs
    points = list(zip(sorted_numbers, cdf))
    #points=list(zip(x,y))
    points = [(x_min, 0)] + points + [(x_max, 1.0)]
    final_plot_data[e]["data_ecdf"] = points
# KDE
for e,library in enumerate(final_plot_data):
    kde = gaussian_kde(np.array(library["data"]), bw_method=0.06)
    x = np.linspace(x_min, x_max, 1000)
    density = kde(x)
    density *= (1.0/max(density)) # normalize 
    density_scale = 1/2
    density *= (len(library["data"]) * density_scale)
    points = list(zip(x, density))
    final_plot_data[e]["data_kde"] = points
    last_cve = datetime.strptime(final_plot_data[e]["cves"][-1][1],"%Y-%m-%d").timestamp()
    final_plot_data[e]["data_kde_precve"] = list(filter(lambda x: x[0] < last_cve, points))
    final_plot_data[e]["data_kde_postcve"] = list(filter(lambda x: x[0] > last_cve, points))
    final_plot_data[e]["versions"] = [(datetime.fromtimestamp(v[0]).strftime('%Y-%m-%d'), density[bisect_left(x, v[0])]/max(density)*density_scale, v[2]) for v in library.get("versions", [])]

#
# Generate TikZ code for the KDE plot
tikz_code = "\\begin{tikzpicture}"
tikz_code += f"""
\\pgfplotsset{{date coordinates in=x,
width=16cm, height=2.7cm,
ymin={y_min:.12f}, ymax={y_max:.12f},
xmin={datetime.fromtimestamp(x_min).strftime('%Y-%m-%d')},
xmax={datetime.fromtimestamp(x_max).strftime('%Y-%m-%d')},
xtick={{{",".join([f"{x}-01-01" for x in range(2010, 2026)])}}},
xticklabels={{{",".join([f"\\shortstack{{{x}\\\\\\tiny({2025-x} yrs old)}}" if x%2==0 else f"{x}" for x in range(2010, 2026)])}}},
y tick label style={{font=\\tiny,color=black!75}},
y label style={{at={{(-0.045,0.5)}}}},
axis lines=left,
scaled y ticks=false,
y axis line style={{-}}, x axis line style={{-}}, clip=false,
}}
"""
for e,library in enumerate(final_plot_data):
    tikz_code += f"""
\\begin{{axis}}[name=plot{e}, 
{f"at={{(plot{e-1}.north)}}, yshift=1.5em, anchor=south," if e > 0 else "yshift=0em,"}
{"xticklabel=\\empty," if e != 0 else "%"}
axis y line=right,
y axis line style={{-}},
ymin=0, ymax={len(library["data"])*1.1},
ytick={{0,{len(library["data"])/4},...,{len(library["data"])}}},
yticklabels={{0,{",".join([f"{len(library['data'])*x/4/1000:.0f}k" for x in range(1,5)])}}},
ylabel={{\\tiny number of apps}}, 
grid=major, grid style={{draw=gray!30}}, 
xmajorgrids=false,
]
\\addplot[color=red!30, thick, fill=red!25, fill opacity=0.5] coordinates {{
{"".join(["("+datetime.fromtimestamp(a).strftime('%Y-%m-%d')+", "+f"{b:.12f})" for a,b in library["data_kde_precve"]])}
}} \\closedcycle;
\\addplot[color=teal!30, thick, fill=green!20!white, fill opacity=0.5] coordinates {{
{"".join(["("+datetime.fromtimestamp(a).strftime('%Y-%m-%d')+", "+f"{b:.12f})" for a,b in library["data_kde_postcve"]])}
}} \\closedcycle;
\\end{{axis}}
%
\\begin{{axis}}[name=plot{e}_cumulative, 
{f"at={{(plot{e}.north)}}, anchor=north,"}
hide x axis=true,
yticklabel=\\pgfmathparse{{\\tick*100}}$\\mathsf{{\\pgfmathprintnumber{{\\pgfmathresult}}}}$\\,\\%, 
ytick={{0,0.25,...,1}},
ylabel={{\\tiny cumulative}}, 
]
\\addplot[color=blue, thick, name path=cumulativeline{e}] coordinates {{
{"".join(["("+datetime.fromtimestamp(a).strftime('%Y-%m-%d')+", "+f"{b:.12f})" for a,b in library["data_ecdf"]])}
}};
{"\n".join([f"\\draw[red,thick,densely dotted,name path=cve{e}{i}] (axis cs:{cve[1]},{y_max}) -- (axis cs:{cve[1]},-0.1) node[at start, anchor=south] {{\\sffamily\\scriptsize {cve[0]}}};\n\\path[name intersections={{of=cumulativeline{e} and cve{e}{i}, by=intersection{e}{i}}}];\n\\draw[red,fill=red] (intersection{e}{i}) circle[radius=1pt];" for i,cve in enumerate(library.get("cves", []))])}
{"\n".join([f"\\draw[black!20] (axis cs:{v[0]},{v[1] + 0.1}) -- (axis cs:{v[0]},{v[1]}) node[at start, anchor=south, inner sep=1pt, black, fill=black!10, fill opacity=0.8, text opacity=1.0] {{\\sffamily\\tiny \\scalebox{{0.7}}{{v{v[2]}}}}};" for i,v in enumerate(library.get("versions", []))])}
\\end{{axis}}
{"\n".join([f"\\draw[red,densely dotted,thick] let \\p1=(intersection{e}{i}) in (\\x1,{y_max})++(plot{e}.south west)++(0,0.07)++(-0.7,0) -- ++(1.4,0);" for i,cve in enumerate(library.get("cves", []))])}
        \\node[anchor=east, text width=1.6cm, align=center, xshift=-2.7em, execute at begin node=\\setlength{{\\baselineskip}}{{0.7em}}] at (plot{e}.west) {{\\small {library["name"]}\\\\ \\tiny{len(library["data"]):,} apps \\\\ ({library["perc_vuln"]:.1f}\\% vulnerable)}};
    """
tikz_code += """
\\node[black!70, text width=4.0cm, anchor=west, align=left, text badly ragged, execute at begin node=\\setlength{\\baselineskip}{0.5em} ] (tooltip) at ($(intersection40)+(1.4,0.9)$) 
{\\scriptsize 60.18\\% of apps using Gif Drawable are using a version released before 13/5/2019, when CVE-2019-11932 was registered.};
\\draw[red,thick,->] (tooltip.west) -- ($(intersection40)+(0.1,0.1)$) ;
\\draw[red,very thick] (tooltip.west) -- ++(0,0.3) -- ++(0,-0.6);
%
\\node[right] (legend0) at ($(plot4_cumulative.north west) + (-1.0,0.7)$) {\\scriptsize Legend:};
\\node[draw, rectangle, fill=blue!40] (legend1) at ($(legend0.east) + (0.24,0.00)$) {};
\\node[right] (legend1box) at (legend1.east) {\\scriptsize Cumulative usage};
\\node[draw, rectangle, fill=red!20] (legend2) at ($(legend1box.east) + (0.1, 0)$) {};
\\node[right] (legend2box) at (legend2.east) {\\scriptsize Potentially vulnerable apps};
\\node[draw, rectangle, fill=green!20!white] (legend3) at ($(legend2box.east) + (0.1, 0)$) {};
\\node[right] (legend3box) at (legend3.east) {\\scriptsize Patched apps};
\\draw[gray!30, fill=gray!20, fill opacity=0.2] (legend0.north west) rectangle (legend3box.south east);
"""
tikz_code += "\\end{tikzpicture}"
open("plots/ffmpeg_versions_kde.tex", "w").write(tikz_code)
open("../acid-paper/plots/ffmpeg_versions_kde.tex", "w").write(tikz_code)
open("../acid-paper2/plots/ffmpeg_versions_kde.tex", "w").write(tikz_code)







### XXX: wrong timestamps on Maven? or Play Store?
a = play_maven_usages.query("updatetimestamp < ( maven_timestamp )")
a.groupby('maven_lib_name').size().sort_values()
### XXX ucrop debugging

maven_usages.query("maven_artifact == 'ucrop'")["maven_developer"]

#  dfs['app_libs'].merge(dfs['apps'], left_on="app_id", right_on="id")['hash'].unique()[:1000].to_csv("wow.csv") dfs['app_libs'].merge(dfs['apps'], left_on="app_id", right_on="id")['hash'].unique()[:1000].to_csv("wow.csv")



if not os.path.exists("openssl_grep_libs.txt"):
    print("error: you need to run the greps.sh script first!")
else:
    if not os.path.exists("openssl_versions.csv"):
        with tempfile.TemporaryDirectory() as tmpdirname:
            os.system(f"git clone --bare --filter=blob:none https://github.com/openssl/openssl {tmpdirname}; pushd {tmpdirname}; git log --tags --simplify-by-decoration --pretty='format:%ct %D' | sed 's/ tag: OpenSSL_/,/' | sed 's/ tag: openssl-/,/' | grep ',' | tr '_' '.' > openssl_versions.csv; popd; cp {tmpdirname}/openssl_versions.csv ./")
    lines = open("openssl_versions.csv", "r").readlines()
    openssl_versions = {l.split(",")[1].strip() : l.split(",")[0].strip() for l in lines if "," in l}
    openssl_libs = {line.split(":")[0]: line.split(":")[1].strip() for line in open("openssl_grep_libs.txt", "r")}
    plot_data = pd.DataFrame([
        [convert_hash(binary), int(timestamp), version]
        for binary, version in openssl_libs.items()
        if (timestamp := openssl_versions.get(version, "0")) != "0"
        ], columns=["hash", "timestamp", "version"])
    plot_data = plot_data.sort_values(by="timestamp").drop_duplicates(subset="hash", keep="first")
    plot_data = plot_data.merge(play_app_libs, on="hash")
    data = sorted(plot_data['timestamp'].tolist())
    versions = plot_data.groupby("timestamp").agg(count=("timestamp", "size"), version=("version", "first")).sort_values(by="count")[-2:].to_records(index=True)
    cves = [("CVE-XXXX-XXXX", "2020-01-21")]
    perc_vuln = bisect_left(data, datetime.strptime(cves[-1][1],"%Y-%m-%d").timestamp()) / len(data) * 100
    #final_plot_data += [{"name":"OpenSSL", "data":data, "cves":cves, "perc_vuln":perc_vuln, "versions":versions}]









# a = droids_vulns_playstore.merge(dfs['apps'], on="app_name").sort_values(by="downloads")
# for row in a[-50:].iloc:
#     os.makedirs("apkpure_downloader/apps/" + row['app_name'], exist_ok=True)
#     print(f"wget -q -O {row['app_name']}.apk 'https://androzoo.uni.lu/api/download?apikey={ANDROZOO_API_KEY}&sha256={row['hash']}' &")
#     # os.system(f"wget -q -O apkpure_downloader/apps/{row['app_name']}/{row['app_name']}.apk 'https://androzoo.uni.lu/api/download?apikey={ANDROZOO_API_KEY}&sha256={row['hash']}' &")
# os.system("wait")  # wait for all downloads to finish
#
# apk_files = []
# for root, dirs, files in os.walk("apkpure_downloader/apps"):
#     for file in files:
#         print(file)
#         if file.endswith(".apk"):
#             apk_files.append(os.path.join(root, file))
#
# for apk_path in apk_files:
#     apk_dir = os.path.dirname(apk_path)
#     apk_name = os.path.splitext(os.path.basename(apk_path))[0]
#     # Check if already decompiled (look for sources folder)
#     output_dir = os.path.join(apk_dir, f"{apk_name}_decompiled")
#     sources_dir = os.path.join(output_dir, "sources")
#     if not os.path.exists(sources_dir):
#         print(f"Decompiling {apk_path}...")
#         try:
#             subprocess.run([ "jadx", "--show-bad-code", "-j", "16", "-d", output_dir, apk_path ])
#         except subprocess.CalledProcessError as e:
#             print(f"Warning: Decompilation failed for {apk_path}: {e}")
#     else:
#         print(f"Already decompiled: {apk_path}")
#



###########################################
#### get vuln lib names for claude analysis
###########################################
#droids
send_to_claude = droids_vulns_playstore.sort_values(by='downloads', ascending=False)[['app_name']].drop_duplicates(subset="app_name", keep="first")
send_to_claude.to_csv("apkpure_downloader/apps.txt", index=False, header=False)
#pdfium
send_to_claude = play_cve_2018_6120.sort_values(by='downloads', ascending=False)[['app_name']].drop_duplicates(subset="app_name", keep="first")
send_to_claude.to_csv("apkpure_downloader/apps.txt", index=False, header=False)
#webp 
send_to_claude = webp_vulns_playstore.sort_values(by='downloads', ascending=False)[['app_name']].drop_duplicates(subset="app_name", keep="first")
send_to_claude.to_csv("apkpure_downloader/apps.txt", index=False, header=False)




##### SCRATCH (delete)
curls = dfs['lib_names'].query("name == 'libcurl.so'")
app_libs.merge(curls, on="lib_id").groupby("app_name").size()
play_app_libs.merge(curls, on="lib_id", how="inner").sort_values(by="downloads")[['app_name', 'downloads']]


# libcurl version analysis
# curl_libs = curls.merge(app_libs, on="lib_id")
curl_play_libs = curls.merge(dfs['playstore_metadata'], on="app_id")
print(f"Total curl libraries: {len(curl_libs)}")
print(f"Total curl libraries in play store: {len(curl_play_libs)}")

# Extract version information from curl libraries
curl_versions = []
for hash_val in curl_libs['hash'].unique():
    try:
        version_output = subprocess.check_output(
            f"strings libs/{convert_back_hash(hash_val)} | grep -E 'libcurl/[0-9]+\\.[0-9]+\\.[0-9]+' | head -1",
            shell=True, stderr=subprocess.DEVNULL
        )
        if version_output:
            version_str = version_output.decode().strip()
            version = version_str.split('/')[-1].split(' ')[0]
            curl_versions.append([hash_val, version])
    except subprocess.CalledProcessError:
        continue

if curl_versions:
    curl_version_df = pd.DataFrame(curl_versions, columns=['hash', 'version'])
    curl_with_versions = curl_play_libs.merge(curl_version_df, on='hash')
    print("Most common curl versions:")
    print(curl_with_versions.groupby('version').size().sort_values()[-10:])



a = play_app_libs.merge(non_duplicate_lib_names, on="lib_id", how="inner")
b = a.query("name.str.lower().str.contains('quickjs')")

vuln_apps = ["com.recorder.screenrecorder.capture", "com.screenrecorder.recorder.editor", "com.blushmark.android", "photo.gallery.imageeditor", "org.mariotaku.twidere", "serie.diaryturk2021",]
play_maven_usages.query("app_name in @vuln_apps")[['app_name', 'downloads']]



icuuc_libnames = dfs['lib_names'].query("name.str.lower().str.contains('libv8')").drop_duplicates(subset='lib_id', keep='first')
icuuc_apps = icuuc_libnames.merge(app_libs, on="lib_id")[["hash", "app_id", "app_name"]]
icuuc_apps_playstore = icuuc_apps.merge(dfs['playstore_metadata']).sort_values(by="downloads", ascending=False)
icuuc_apps_playstore[['app_name', 'downloads']]
hashes = list(set(icuuc_apps_playstore['hash'].to_list()))
open("hashes_to_copy.txt", "w").write("\n".join(map(convert_back_hash, hashes)))
# rsync -azv --files-from=hashes_to_copy.txt luca@10.0.0.14:acid/libs/ libs/
# rsync -azv --files-from=hashes_to_copy.txt luca@10.0.0.14:acid/ground_truth_libs/ libs/
vuln_hashes = []
for f in hashes[:]:
    version = subprocess.check_output(f"r2 -qc 'pv2 @ obj.v8::internal::Version::major_; pv2 @ obj.v8::internal::Version::minor_; pv2 @ obj.v8::internal::Version::build_; pv2 @ obj.v8::internal::Version::pathc_;' libs/{convert_back_hash(f)} 2>/dev/null", shell=True)
    versions = version.decode().strip().split("\n")
    if len(versions) < 2: continue
    versions = ".".join(map(lambda x: str(int(x, 16)), versions))
    version = Version(versions)
    print(version)
    if version < Version("9.4"):
        vuln_hashes += [f]

v8_vulns = icuuc_apps[icuuc_apps['hash'].isin(vuln_hashes)]
v8_vulns_playstore = v8_vulns.merge(dfs['playstore_metadata'][['app_id', 'downloads']], how='left').fillna({"downloads":-1})
v8_vulns_playstore[["app_name", "downloads"]].sort_values(by="downloads")[-40:]












