import sqlite3
import pandas as pd
import IPython

db_path = 'old.sqlite'
conn = sqlite3.connect(db_path)
query = "SELECT name FROM sqlite_master WHERE type='table';"
tables = pd.read_sql_query(query, conn)
table_names = tables['name'].tolist()
dfs = {}
for table in table_names:
    dfs[table] = pd.read_sql_query(f"SELECT * FROM {table}", conn)
conn.close()
print("done loading sqlite db")


a = dfs['app_libs'].merge(dfs['libs'], left_on='lib_id', right_on='id')
dfs['new_names'] = dfs['lib_names'].drop_duplicates(subset='lib_id', keep='first')

b = a.merge(dfs['new_names'], left_on='lib_id', right_on='lib_id')
c = b.merge(dfs['apps'], left_on='app_id', right_on='id')
c = c.drop(columns=['id_x'])
c = c.drop(columns=['id'])
c = c.drop(columns=['hash_y'])
c = c.drop(columns=['id_y'])

print("SOME STATISTICS")
print("Total apps:", len(dfs['apps']))
print("Apps with libraries:", len(set(dfs['app_libs']['app_id'])))
print("Out of the ", len(dfs['app_libs']), "extracted libraires, ", len(dfs['libs']), " are unique")

d = c.groupby('lib_id').size().reset_index().merge(dfs['new_names'], left_on='lib_id', right_on='lib_id')
print("Most popular hashes (by name):", d.sort_values(by=0)[[0,'name']])

e = sum(c.groupby('lib_id').size().reset_index().merge(dfs['new_names'], left_on='lib_id', right_on='lib_id').sort_values(by=0)[0][-10000:]) / len(c) * 100
print("Top 10000 library hashes account for ", c, "% of all native libraries")

print(e)



#### PLAYSTORE APPS

z = dfs['apps'].merge(dfs['playstore_metadata'], left_on='id', right_on='app_id').drop(columns=['id', 'hash'])
print("Oldest apps:", z.sort_values('updatetimestamp')[['app_name', 'updatetimestamp', 'lastupdatedate']])
zz = z.merge(dfs['app_libs'], on="app_id")
zzz = zz.merge(dfs['libs'], left_on="lib_id", right_on="id").drop(columns="id")
print("Oldest apps:", zzz.sort_values('updatetimestamp')[['app_name', 'updatetimestamp', 'lastupdatedate']])

print("Number of libs per app:", zzz.groupby("app_name").size())


zzzz = dfs['new_names'].query('"libpl_droidsonroids_gif.so" == name')[['lib_id']].merge(zzz, on='lib_id')
print("gif drawable cve vulnerables:", zzzz.query("updatetimestamp < 1570141815").sort_values('downloads')[['app_name', 'downloads', 'lastupdatedate']])


IPython.embed()
