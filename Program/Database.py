import sqlite3
import datetime
import json
import random 
import datetime
import yfinance as yf
import os
from enum import Enum

#Enum to get the index of a value from the tag table assuming that you are getting the entire row
class LabelIndex(Enum):
    label_name = 0
    label_text = 1
    label_image_path = 2
    user_id = 3


config = open("config.json")
fileData = json.load(config)

database = sqlite3.connect(fileData["database"])
cursor = database.cursor()


#Creates repository if they do not exist
async def createRepository():
    cursor.execute("CREATE TABLE IF NOT EXISTS tags(label_name TEXT PRIMARY KEY, label_text TEXT, label_image_path TEXT, user_id INT )")

#Gets the data relating to a tag based on name
async def getTag(name:str):
    cursor.execute("SELECT * FROM tags WHERE label_name=?",(name,))
    result = cursor.fetchone()
    return result

#Adds a tag if it does not exist and returns any messages relating to the process
async def addTag(user:int, name:str, text:str, image=""):
    if (name==""):
        return "Please input the tag with the format of: name(space)text"
    if (text=="" and image==""):
        return "Either text or image must have an input, both cannot be empty at once"
    cursor.execute("SELECT * FROM tags WHERE label_name=?",(name,))
    result = cursor.fetchone()
    if (result == None):
        cursor.execute("INSERT INTO tags VALUES(?,?,?,?)",(name, text, image, user))
        database.commit()
        return "Tag added sucessfully"
    else:
        return "Error, tag already exists"
    
    
    
createRepository()