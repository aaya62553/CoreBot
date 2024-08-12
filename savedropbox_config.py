import dropbox
import dropbox.files
from dotenv import load_dotenv 
import os
import json
load_dotenv()

import requests


def refresh_access_token(refresh_token, client_id, client_secret):
    url = "https://api.dropboxapi.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    response = requests.post(url, data=data)
    if response.status_code == 200:
        tokens = response.json()
        new_access_token = tokens['access_token']
        # Met à jour ton fichier config.json avec le nouveau access_token ici
        return new_access_token
    else:
        print(f"Erreur: {response.status_code}")
        return None
    



def savedropboxconfig():
    with open('config.json','r') as f:
        config=json.load(f)
    dbx=dropbox.Dropbox(config["dropbox_token"])

    with open('config.json','rb') as f:
        dbx.files_upload(f.read(),'/config.json',mode=dropbox.files.WriteMode.overwrite)
    print('config.json uploaded to Dropbox')

def loadconfig_dropbox():
    with open('config.json','r') as f:
        config=json.load(f)
    new_token=refresh_access_token(os.getenv("refresh_TOKEN"), os.getenv("APP_KEY"), os.getenv("APP_SECRET"))
    dbx=dropbox.Dropbox(new_token)
    dbx.files_download_to_file('config.json','/config.json')

    return config