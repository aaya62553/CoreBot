import dropbox
import dropbox.files
from dotenv import load_dotenv 
import os
load_dotenv()

dbx=dropbox.Dropbox(os.getenv('dropbox_TOKEN'))

def savedropboxconfig():
    with open('config.json','rb') as f:
        dbx.files_upload(f.read(),'/config.json',mode=dropbox.files.WriteMode.overwrite)
    print('config.json uploaded to Dropbox')