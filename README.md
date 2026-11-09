# acid
Repository for the "Android Code Idendification &amp; Detection" project.

*Link to the anonymized database:* [link](https://drive.google.com/file/d/18dfeTwvcMaoqqehv02xspWW5rWwbjkeG/view?usp=drive_link)

## How to

1. setup: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
2. `python3 new_dload_apks.py` this script will:
    - Download androzoo apk list
    - Download native libs from androzoo by using the zipfile trick
    - Download play store metadata for each app
    - Store everything in the db `the_base_of_datas.sqlite`
3. Run the analysis `python3 database_statistics.py`, which will:
    - Print statistics about collected libraries
    - Analyze which apps are vulnerable
    - Create plots and figures in the plots/ folder
