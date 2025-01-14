import sqlite3
import datetime
import json
import random 
import datetime
from datetime import datetime, timedelta, tzinfo, timezone
import dateutil
import yfinance as yf
from enum import Enum
from dotenv import load_dotenv 
import uuid

#Enum to get the index of a value from the tag table assuming that you are getting the entire row
class label_index(Enum):
    label_name = 0
    label_text = 1
    label_image_path = 2
    user_id = 3

#Event data enum
class event_data_index(Enum):
    event_id = 0
    event_date = 1
    event_name = 2
    event_descrption = 3
    end_date = 4
    next_repeat = 5
    guild_id = 6
    channel_id = 7
    owner_id = 8
    participants = 9

#The two possible choices for a coin flip must match the button names
coin_flip_choices=["Heads","Tails"]

#Load envrioment variables (currently unsued)
load_dotenv() 

#Home directory is the directory to the DiscordBotV3 folder + /
home_directory = ""

#Load the config.json file
config = open(home_directory+"config.json")
file_data = json.load(config)


#Loads the database
database = sqlite3.connect(home_directory+"Persistant_Data/user.db")
cursor = database.cursor()
global_connection = sqlite3.connect(home_directory+"Persistant_Data/global.db")
global_cursor = global_connection.cursor()

#Amount of time for cooldown in days
cooldown = 1

#Wether or not to bypass cooldown
cooldown_bypass = False

#Formate for dates
format = "%Y-%m-%d"

#Default date to set as cooldown, ensure that the differnce between current date and defualt date is greater than cooldown
default_date = datetime(2024,1,1).strftime(format)

#Dictonary for quests matching quest number to the quest descripnt. "?" is the goal number, "*" is the current number of completetion
quests = {
    0:"Claim the daily reward ? time(s): */?",
    1:"Sell ? stock(s): */?",
    2:"Buy ? stock(s): */?",
    3:"Flip a coin ? time: */?",
    4:"Play blackjack ? time: */?"
}

#Dictionary for quests macthing the quest name to the quest number
quest_dict = {
    "Daily" : 0,
    "Sell Stock" : 1,
    "Buy Stock" : 2,
    "Flip Coin": 3,
    "Blackjack": 4
}



#Get last leaderboard upate
async def get_last_update():
    global_cursor.execute("SELECT lastUpdate FROM global_data")    
    return global_cursor.fetchone()[0]

#Calculate stock value
async def calc_stock_value(data):
    total = 0
    for key, value in data.items():
        info = yf.Ticker(key).info
        total += value*info["bid"]
    return total

#Update leadebord
async def update_leader_board():
    cursor.execute("SELECT stock_dicts, id FROM stocks")
    stock_data = cursor.fetchall()
    count = 0
    for row in stock_data:
        amount = round(await calc_stock_value(json.loads(row[0])), 2)
        await update_total_and_stock(row[1],amount)
    cursor.execute("SELECT username, total, points, stock_value, id FROM users ORDER BY total DESC")
    users = cursor.fetchall()
    user_names = ""
    totals = ""
    points_andS_socks = ""
    for row in users:
        count += 1
        user_names += str(count)+"."+row[0]+"\n"
        totals += str(row[1])+"\n"
        points_andS_socks += str(row[2])+"|"+str(row[3])+"\n"
        cursor.execute("UPDATE users SET placement=? WHERE id=?",(count,row[4]))
        database.commit()
    leaderBoard = json.dumps([user_names, totals, points_andS_socks])
    global_cursor.execute("UPDATE global_data SET leaderboard=?, lastUpdate=?",(leaderBoard,str(datetime.now())))
    global_connection.commit()

#Method to update toatla and stock value
async def update_total_and_stock(id:int, stockAmount:int):
    total = round(await get_points(id) + stockAmount,2)
    cursor.execute("UPDATE users SET stock_value=?, total=? WHERE id=?",(stockAmount, total, id))
    database.commit()


#Get the last saved leaderboard
async def get_leader_board():
    global_cursor.execute("SELECT leaderboard FROM global_data")
    return global_cursor.fetchone()[0]

#Get the row of user data from a user id
async def get_user_data(id:int):
    cursor.execute("SELECT placement, username, total, points, stock_value FROM users WHERE id=?",(id,))
    return cursor.fetchone()

#Quest and cooldown database functions

#Creates repository if they do not exist
async def create_repository():
    cursor.execute("CREATE TABLE IF NOT EXISTS tags(label_name TEXT PRIMARY KEY, label_text TEXT, label_image_path TEXT, user_id INT )")
    cursor.execute("CREATE TABLE IF NOT EXISTS cooldown(id INT PRIMARY KEY, last_daily TEXT, last_quest TEXT )")
    cursor.execute("CREATE TABLE IF NOT EXISTS quests(id INT PRIMARY KEY,quest1 TEXT, quest2 TEXT, quest3 TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS users(id INT PRIMARY KEY, points REAL, stock_value REAL, total REAL, username TEXT, placement INT, time_offset TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS stocks(id INT PRIMARY KEY, stock_dicts TEXT, transactions TEXT)")
    global_cursor.execute("CREATE TABLE IF NOT EXISTS global_data(leaderboard TEXT, users INT, lastUpdate TEXT)")
    global_cursor.execute("CREATE TABLE IF NOT EXISTS events(event_id TEXT PRIMARY KEY, event_date TEXT, event_name TEXT, event_description TEXT, end_date TEXT, next_repeat TEXT, guild_id INT, channel_id INT, owner_id INT, participants TEXT)")
    global_cursor.execute("SELECT * FROM global_data")
    if(global_cursor.fetchone() is None):   
        global_cursor.execute("INSERT INTO global_data VALUES(?,?,?)",("",0,str(datetime.now())))
        global_connection.commit()

#Reset daily cooldown for speciifed user
async def reset_daily_cooldown(id:int):
    date = datetime.today().strftime(format)
    cursor.execute("UPDATE cooldown SET last_daily=? WHERE id=?",(date,id))
    database.commit()

#Check if the daily cooldown is less than or equal to the cooldown
async def check_daily_cooldown(id:int):
    cursor.execute("SELECT last_daily FROM cooldown WHERE id=?",(id,))
    timeDifference = (datetime.today() - datetime.strptime(cursor.fetchone()[0], format)).days
    return timeDifference>=cooldown or cooldown_bypass

#Check if the quest cooldown is less than or equal to the cooldown
async def check_quest_cooldown(id:int):
    cursor.execute("SELECT last_quest FROM cooldown WHERE id=?",(id,))
    timeDifference = (datetime.today() - datetime.strptime(cursor.fetchone()[0], format)).days
    return timeDifference>=cooldown or cooldown_bypass

#Resets the quest cooldown
async def reset_quest_cooldown(id:int):
    date = datetime.today().strftime(format)
    cursor.execute("UPDATE cooldown SET last_quest=? WHERE id=?",(date,id))
    database.commit()

#Updates the quests with new random quests
async def update_quests(id:int, quest_id:int, amount:int=1):
    cursor.execute("SELECT quest1, quest2, quest3 FROM quests WHERE id=?",(id,))
    quests = list(cursor.fetchone())
    for i in range(len(quests)):
        quest_dict = json.loads(quests[i])
        if (quest_dict["id"] == quest_id):
            quest_dict.update(progress=quest_dict["progress"]+amount)
            quests[i] = json.dumps(quest_dict)
    cursor.execute("UPDATE quests SET quest1 = ?, quest2 = ?, quest3 = ? WHERE id=?",(quests[0],quests[1],quests[2],id))
    database.commit()
    
#Genreate a random quest
def get_new_quest():
    goal = random.randint(1,5)
    quest = {
        "id" : random.randint(0,2),
        "progress" : 0,
        "goal" : goal,
        "points" : goal*random.randint(1,5),
        "claimed" : False
    }
    return json.dumps(quest)

#Get all the quests from a user
async def get_quests(id:int):
    cursor.execute("SELECT quest1, quest2, quest3 FROM quests WHERE id=?",(id,))
    quests = list(cursor.fetchone())
    for i in range(len(quests)):
        quest_dict = json.loads(quests[i])
        quests[i] = quest_dict
    return quests

#Reset the quests the user currently has
async def reset_quests(id:int):
    cursor.execute("UPDATE quests SET quest1 = ?, quest2 = ?, quest3 = ? WHERE id=?",(get_new_quest(),get_new_quest(),get_new_quest(),id))
    database.commit()

#Reaplces all quests that are completed
async def set_new_quets(id:int):
    cursor.execute("SELECT quest1, quest2, quest3 FROM quests WHERE id=?",(id,))
    quests = list(cursor.fetchone())
    for i in range(len(quests)):
        quest = json.loads(quests[i])
        if quest["progress"]>=quest["goal"]:
            quests[i] = get_new_quest()
    cursor.execute("UPDATE quests SET quest1 = ?, quest2 = ?, quest3 = ? WHERE id=?",(quests[0],quests[1],quests[2],id))

#Claims quest if the quest has not been claimed
async def claim_quests(id:int):
    cursor.execute("SELECT quest1, quest2, quest3 FROM quests WHERE id=?",(id,))
    quests = cursor.fetchone()
    total_points = 0
    for i in range(len(quests)):
        quest_dict = json.loads(quests[i])
        if (quest_dict["progress"]>=quest_dict["goal"] and not quest_dict["claimed"]):
            total_points+=quest_dict["points"]
            quest_dict["claimed"] = True
    cursor.execute("UPDATE quests SET quest1 = ?, quest2 = ?, quest3 = ? WHERE id=?",(quests[0],quests[1],quests[2],id))
    database.commit()
    return total_points
    
#Insets new user into the database if they do not exist
async def insert_new_user_if_no_exists(id:int,name:str):
    cursor.execute("SELECT * FROM users WHERE id=?",(id,))
    if(cursor.fetchone() is None):
        global_cursor.execute("SELECT users FROM global_data")
        num_users = global_cursor.fetchone()[0]
        num_users+=1        
        global_cursor.execute("UPDATE global_data SET users = ? ",(num_users,))
        global_connection.commit()
        cursor.execute("INSERT INTO users VALUES(?,?,?,?,?,?,?)",(id,0,0,0,name,num_users,"undefined"))
        cursor.execute("INSERT INTO cooldown VALUES(?,?,?)",(id,default_date,default_date))
        cursor.execute("INSERT INTO quests VALUES(?,?,?,?)",(id,get_new_quest(),get_new_quest(),get_new_quest()))
        cursor.execute("INSERT INTO stocks VALUES(?,?,?)",(id, "{}", "[]"))
        database.commit()

#Get the amount of a stock a user has
async def get_amount_of_stock(id:int, ticker:str):
    dictionary = await get_stocks(id)
    if (ticker in dictionary):
        return dictionary[ticker]
    else:
        return 0

#Gets all the sotcks a user has
async def get_stocks(id:int):
    cursor.execute("SELECT stock_dicts FROM stocks WHERE id=?",(id,))
    data = cursor.fetchone()
    dictionary = json.loads(data[0])
    return dictionary

#Update the value of stocks a user has
async def update_stock_value(id:int, value:float):
    cursor.execute("SELECT stock_value FROM users WHERE id=?",(id,))
    data = cursor.fetchone()[0]
    data += value
    data = round(data, 2)
    cursor.execute("UPDATE users SET stock_value = ? WHERE id = ?",(data, id))
    database.commit()

#Set the value of stock a user has
async def set_stock_value(id:int, value:float):
    cursor.execute("UPDATE users SET stock_value=? WHERE id=?",(value, id))
    database.commit()

#Get the value of stock stored in the database
async def get_stored_stock_value(id:int):
    cursor.execute("SELECT stock_value FROM users WHERE id=?",(id,))
    return round(cursor.fetchone()[0],2)

#Get eevent data
async def get_event_data_dict(event_id:str):
    global_cursor.execute("SELECT * FROM event_data WHERE event_id=?",(event_id,))
    data = global_cursor.fetchone()
    if (data == None):
        return "Event not found"
    else:
        event_data = {
                "event_id":data[event_data_index.event_id],
                "guild_id":data[event_data_index.guild_id],
                "channel_id":data[event_data_index.channel_id],
                "owner_id":data[event_data_index.owner_id],
                "participants":''.join(json.loads(data[event_data_index.participants])),
                "event_end":data[event_data_index.event_name],
                "current_event_date":data[event_data_index.event_date],
                "description":data[event_data_index.event_descrption]
            }
        event_end = datetime.fromisoformat(event_data["event_end"])
        next_date:datetime = calc_next_time(datetime.fromisoformat())
        if (next_date<event_end):
            event_data["next_date"] = next_date.isoformat("YYYY-MM-DD HH:MM", "T")
        else:
            event_data["next_date"] = "None"
        return event_data

#Calculate the time/date depending on the users time offest returns a string
async def calc_time_day_str(date_time:str,user_id:int):
    date_time_datetime = datetime.fromisoformat(datetime)
    time_offset = await get_time_offset(user_id)
    if (time_offset is None):
        return None
    else:
        return (date_time_datetime + time_offset).isoformat("YYYY-MM-DD HH:MM","T")


#Get the processed data of an event
async def process_event(event_id:str):
    global_cursor.execute("SELECT * FROM event_data WHERE event_id=?",(event_id,))
    data = global_cursor.fetchone()
    if (data == None):
        return "Event not found"
    else:
        event_data = {
            "event_id":data[event_data_index.event_id],
            "guild_id":data[event_data_index.guild_id],
            "channel_id":data[event_data_index.channel_id],
            "owner_id":data[event_data_index.owner_id],
            "participants":''.join(json.loads(data[event_data_index.participants])),
            "title":data[event_data_index.event_name],
            "event_end":data[event_data_index.event_name],
            "current_event_date":data[event_data_index.event_date],
            "description":data[event_data_index.event_descrption]
        }
        event_end = datetime.fromisoformat(event_data["event_end"])
        next_date:datetime = calc_next_time(datetime.fromisoformat())
        if (next_date<event_end):
            event_data["next_date"] = next_date.isoformat("YYYY-MM-DD HH:MM", "T")
            global_cursor.execute("UPDATE event_data SET event_date = ? WHERE event_id = ?", (event_data["next_date"], event_data["event_id"]))
            global_connection.commit()
        else:
            event_data["next_date"] = "None"
            global_cursor.execute("DELETE FROM event_data WHERE event_id = ?", (event_data["event_id"],))
        return event_data

async def calc_next_time(date:str, time_diff:str):
    date_datetime = datetime.fromisoformat(date)
    time_diff_datetime = datetime.fromisoformat(time_diff)
    time_zero = datetime.strptime('00:00:00', '%H:%M:%S')
    next_date = (date_datetime - time_zero + time_diff_datetime)
    return next_date

#Set the user time offest sign is --1 or 1 where it is utc to local time such that EST would be -5:0
async def update_user_time_offest(id:int, hours:int, minutes:int):
    cursor.execute("UPDATE users SET time_offset = ? WHERE id = ?",(f'{hours}:{minutes}',id))
    database.commit()

#Get the time offset of a user, returns the delta time which is the different between UTC and local time
async def get_time_offset(id:int):
    cursor.execute("SELECT time_offset WHERE id=?",(id,))
    deltatime = cursor.fetchone()
    if (deltatime is None):
        return None
    else:
        str_deltatime = deltatime[0].split(":")
        time_diff = timedelta(hours=int(str_deltatime[0]),minutes=int(str_deltatime[1]))
        return time_diff

#Calculate the time/date depending on the users time offest
async def calc_time_day(date_time:datetime,user_id:int):
    time_offset = await get_time_offset(user_id)
    if (time_offset is None):
        return None
    else:
        return date_time + time_offset

#Check if the date is past the current date
async def check_future(date_time:datetime):
    today = datetime.now(tz=timezone.utc)
    return date_time>today

#Add an event to the event database
#Date is the date/time of the first instance of the event in ISO 8601 format
#Title is the title of the event, and descpriton is the descpriton of the event
#Repeats is the number of itmes is repeats, 
async def add_event(date:str, title:str, description:str, end_date:str, next_repeat:str, guild:int, channel:int, owner:str):
    participants = [f"<@{owner}>"]
    global_cursor.execute("INSERT INTO event_data VALUES(?,?,?,?,?,?,?,?,?)",(uuid.uuid4(),date,title,description,end_date,next_repeat,guild,channel,owner,json.dumps(participants)))
    global_connection.commit()
    return "done"

#Get event data from event event id
async def get_event(event_id:str):
    global_cursor.execute("SELECT * FROM event_data WHERE event_id=?",(event_id,))
    return global_cursor.fetchone()

#Add participants to an event
async def add_Participant(event_id:str, new_participant:int):
    new_participant = f"<@{new_participant}>"
    global_cursor.execute("SELECT * FROM event_data WHERE event_id=?", (event_id,))
    event = global_cursor.fetchone()
    if (event == None):
        return "Event not found"
    else:
        participants = json.loads(event[event_data_index.participants])
        if (new_participant in participants):
            return "You are already a participant of this event"
        else:
            participants.append(new_participant)
            if (len(participants)>48):
                return "Too many participant the max number of users is 48"
            else:
                global_cursor.execute("UPDATE events SET participants = ? WHERE event_id = ?", (json.dump(participants),event_id))
                global_connection.commit()
                
#Update the stocks a user has
async def update_stock(id:int, stock_dict, action:str, amount:int):
    cursor.execute("SELECT * FROM stocks WHERE id=? ",(id,))
    userDataJSON = cursor.fetchone()
    userData = []
    price = 0
    ticker = stock_dict["underlyingSymbol"]
    for i in range(2):
        userData.append(json.loads(userDataJSON[i+1]))
    if (userData[0].get(ticker)==None):
        userData[0][ticker] = 0
    if (action=="Buy"):
        await update_points(id, stock_dict["ask"]*-1*amount)
        userData[0][ticker] = userData[0][ticker]+amount
        price = stock_dict["ask"]
        await update_stock_value(id, stock_dict["bid"]*amount)
        await update_quests(id, quest_dict["Buy Stock"], amount)
    elif (action=="Sell"):
        await update_points(id, stock_dict["bid"]*amount)
        newAmountOfStock = userData[0][ticker]-amount
        if (newAmountOfStock>0):
            userData[0][ticker] = newAmountOfStock 
        else:
            del userData[0][ticker]
        price = stock_dict["bid"]
        await update_stock_value(id, stock_dict["bid"]*amount*-1)
        await update_quests(id, quest_dict["Sell Stock"], amount)
    transaction = {
        "stock":stock_dict["underlyingSymbol"],
        "action": action,
        "price":price
    }
    userData[1].append(transaction)
    cursor.execute("UPDATE stocks SET stock_dicts =?, transactions=? WHERE id=?",(json.dumps(userData[0]), json.dumps(userData[1]),id))
    database.commit()

#Get the number of points a user has
async def get_points(id:int):
    cursor.execute("SELECT points FROM users WHERE id=?",(id,))
    points = cursor.fetchone()
    return points[0]

#Update the amount of points a user has
async def update_points(id:int, change:float):
    cursor.execute("SELECT points FROM users WHERE id=?",(id,))
    points = cursor.fetchone()[0]
    points += change
    points = round(points, 2)
    cursor.execute("UPDATE users SET points = ? WHERE id=?",(points, id))
    database.commit()
    return points

#Remove tag if it exists
async def delete_tag(name:str):
    cursor.execute("DELETE FROM tags WHERE label_name=?",(name,))
    database.commit()

#Gets the data relating to a tag based on name
async def get_tag(name:str):
    cursor.execute("SELECT * FROM tags WHERE label_name=?",(name,))
    result = cursor.fetchone()
    return result

#Update a tag with new values assuming that empty arguments mean not change if the tag exists
async def update_tag(user:int, name:str, text:str, image=""):
    result = await get_tag(name)
    if (result==None):
        return "Error, tag not found"
    elif(user!=result[label_index.user_id.value]):
        return "Error, you did not create the tag and do not have permission"
    else:
        if (text==""):
            text=result[label_index.label_text.value]
        if (image==""):
            image=result[label_index.label_image_path.value]
        cursor.execute("UPDATE tags SET label_text=?, label_image_path=? WHERE label_name=?",(text, image, name))
        database.commit()
        return "Tag updated sucessfully"

#Adds a tag if it does not exist and returns any messages relating to the process
async def add_tag(user:int, name:str, text:str, image=""):
    if (name==""):
        return "Please input the tag with the format of: name(space)text"
    if (text=="" and image==""):
        return "Either text or image must have an input, both cannot be empty at once"
    result = await get_tag(name)
    if (result == None):
        cursor.execute("INSERT INTO tags VALUES(?,?,?,?)",(name, text, image, user))
        database.commit()
        return "Tag added sucessfully"
    else:
        return "Error, tag already exists"
    
    
#Determine and process a coin flip bet
async def coin_flip(user:int, bet:int, choice:str):
    await update_quests(user,3)
    win_choice=random.choice(coin_flip_choices)
    if (choice==win_choice):
        await update_points(user,bet)
    else:
        await update_points(user,bet*-1)
    return choice==win_choice
        

