from datetime import date
import asyncio
import pandas as pd
from mongoengine import connect

from src.resubmission.config_handler import config
from src.resubmission.models import Policy
from src.resubmission.extraction import ExtractAgent
from src.resubmission.utils import insert,delete,insert_ncci
from src.resubmission.prompt import bupa_prompt

# -----------------------
# MongoDB connection
# -----------------------
params = config(section="mongodb")

connect(
    db=params["db"],
    host=params.get("host"),
    port=int(params.get("port")),
    username=params.get("username"),
    password=params.get("password"),
    authentication_source=params.get("authentication_source"),
)

import json
from pathlib import Path

def insert_jsons_from_folder(folder_path="jsons/New"):
    folder = Path(folder_path)

    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Folder not found: {folder_path}")

    for json_file in folder.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)   # ✅ load JSON content as dict

            insert(data)              # ✅ insert into MongoDB

        except Exception as e:
            print(f"Error inserting {json_file.name}: {e}")

""" def delete_for_update():
    updated_policies = ["508238003",
                        "509813003",
                        "513508002",
                        "514363002",
                        "519802001",
                        "520137001",
                        "521269001",
                        "514891001",
                        "467296001",
                        "508521028",
                        "501533015",
                        "515124001",
                        "476608003",
                        "356232006",
                        "501551003",
                        "514312002",
                        "501471001",
                        "363102001",
                        "357880307",
                        "562957002",
                        "508167008",
                        "501709048",
                        "514312001",
                        "514758001",
                        "514222001",
                        "440526003",
                        "501516018",
                        "501471003",
                        "501462011",
                        "508499003",
                        "488797001",
                        "514279001",
                        "508351001",
                        "514293001",
                        "476260005",
                        "165782084",
                        "563249007",
                        "475232002"
    ]
    for i in updated_policies:
        delete(i) """

if __name__=="__main__":
    #delete_for_update()
    #insert_jsons_from_folder("/home/ai/Workspace/Rafik/Resubmission-Copilot/jsons/NCCI/New")
    file = "/home/ai/Workspace/Rafik/Resubmission-Copilot/jsons/NCCI/New/llama-extract-01a54f13-5267-4f24-9509-824f6e3e4baf-48594944- Hala Payments Company-15-9-2026.json"
    
    with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)   # ✅ load JSON content as dict

    insert_ncci(data)