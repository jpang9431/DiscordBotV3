import os
import re
import time
import discord
from discord import app_commands
from discord.ext import commands
import json
import Interpret
import Database as db
from Database import event_data_index
from dotenv import load_dotenv 
import urllib.request
import uuid
import Bot_Ui as ui
from Bot_Ui import back_button, blackjack_hit_button, blackjack_stay_button, edit_menu, flip_coin_button, role_button
from Bot_Ui import edit_quest
from Bot_Ui import edit_daily
from Bot_Ui import edit_stock_market_view_and_embed
from Bot_Ui import edit_leaderboard
from discord.ext import commands
from discord.ui import View
from discord import app_commands
import yfinance as yf
import asyncio
from Minigame import blackJack
from datetime import datetime
import dateutil
import datetime
from datetime import datetime
import pytz
from datetime import timedelta
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler
import uuid
from asyncio import run
from apscheduler.triggers.date import DateTrigger

#All the event scheulding variables 
now = datetime.now(tz=pytz.timezone("UTC"))
current_date_processing:datetime = datetime(year=now.year, month=now.month, day=now.day, hour=23, tzinfo=pytz.timezone("UTC"))
next_date = timedelta(days=1)
scheduler = BackgroundScheduler({'apscheduler.timezone': 'UTC'})


#Home directory is the directory to the DiscordBotV3 folder + /
home_directory = ""

#Max number of characters in a embed field
max_characters = 1024

#Loads the envrioment varaibles
load_dotenv() 

#Global variables
token = os.getenv("token")
config = open(home_directory+"config.json")
file_data = json.load(config)


#File paths for the output to txt raw files
full_text_output_file_path = home_directory+file_data["full_text_output_file_path"]
sepical_text_output_file_path = home_directory+file_data["sepical_text_output_file_path"]

#File paths for the output to txt processed files
word_count_file = home_directory+file_data["word_count_file"]
special_count_file = home_directory+file_data["special_count_file"]
character_count_file = home_directory+file_data["character_count_file"]
links_file = home_directory+file_data["links_file"]
bad_word_output = home_directory+file_data["bad_word_output"]
James_words_output = home_directory+file_data["James_words_output"]

#List of all files
files = [full_text_output_file_path, sepical_text_output_file_path, word_count_file, special_count_file, 
         character_count_file, links_file, bad_word_output, James_words_output]

#Prevents race condition for writing to document
currentlyProcessing = False

#List of command interactions that are waiting for a presence update from a user
presenceUpate = {}


loop = None
class totally_not_a_gambling_bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_dynamic_items(role_button)

    #Event trigger as soon as the program is run
    async def on_ready(self):
        await db.create_repository()
        print("Online")
        synced = await self.tree.sync()
        print(len(synced))
        await db.update_leader_board()
        global loop
        loop = asyncio.get_running_loop()
        await add_events()
        scheduler.start()
        
        
client = totally_not_a_gambling_bot()
    
#Handle the bot being added to a new guild
async def add_guild(guild):
    for user in guild.members:
        if not user.bot:
            await db.insert_new_user_if_no_exists(user.id, user.global_name)
            
#Trigger adding all users in a guild
@client.event
async def on_guild_join(guild):
    await add_guild(guild)

#Trigger on a user chaning presence
@client.event
async def on_presence_update(before:discord.Member, after:discord.Member):
    if(str(before.status)=="offline" and str(after.status)!="offline"):
        target = await client.fetch_user(after.id)
        target_name = target.name
        users = presenceUpate.get(after.id,[])
        if (len(users)!=0):
            for interaction in users:
                await interaction.followup.send(interaction.user.mention+" "+target_name+" is online",ephemeral=True)
            del presenceUpate[after.id]
        #print(str(presenceUpate[after.id]))

#Command to be pinged when a user gets online
@client.tree.command(name="notify_when_user_online", description="Get notified when a user is online")
@app_commands.describe(target="The user you want to be notified about")
async def notify_when_user_online(interaction:discord.Interaction,target:discord.Member):
    listOfNotifs = presenceUpate.get(target.id,[])
    listOfNotifs.append(interaction)
    presenceUpate[target.id] = listOfNotifs
    await interaction.response.defer(ephemeral=True)
    

#Command to add new users to the db
@client.tree.command(name="add_new_users", description="Add users not in the database")
async def add_new_users(interaction:discord.Interaction):
    await add_guild(interaction.guild)
    await interaction.response.send_message(content="Process completed", ephemeral=True)
    
#command to check quest infromation
@client.tree.command(name="quest", description="Check/Claim quest progress and get new quests")
async def quest(interaction:discord.Interaction):
    userId = interaction.user.id
    await db.insert_new_user_if_no_exists(userId, interaction.user.global_name)
    user = interaction.user
    embed = discord.Embed(title=user.display_name, color = user.color)
    view = View()
    await edit_quest(view, embed, user,interaction)
    await interaction.response.send_message(embed=embed, view=view)

#Get the menu of options from discord slash command
@client.tree.command(name="menu", description="View the menu of options")
async def menu(interaction:discord.Interaction):
    userId = interaction.user.id
    await db.insert_new_user_if_no_exists(userId, interaction.user.global_name)
    user = interaction.user
    embed = discord.Embed(title=user.display_name, color = user.color)
    view = View()
    await edit_menu(view, embed, user, interaction)
    await interaction.response.send_message(embed=embed, view=view)

#Claim daily reward
@client.tree.command(name="daily", description="Claim daily reward")
async def daily(interaction:discord.Interaction):
    user = interaction.user
    await db.insert_new_user_if_no_exists(user.id, interaction.user.global_name)
    embed = discord.Embed(title=user.display_name, color = user.color)
    view = View()
    await edit_daily(view, embed, user, interaction)
    await interaction.response.send_message(embed=embed, view=view)

#Display the stock marknet menu
@client.tree.command(name="stock_market", description="Display the menu for the stock market")
@app_commands.describe(ticker="The stock ticker symbol that you want to look up")
@app_commands.describe(amount="Amount of stocks to buy/sell")
async def stock_market(interaction:discord.Interaction, ticker: str, amount: app_commands.Range[int,0]):
    tickerObj = yf.Ticker(ticker)
    if(tickerObj.cashflow.empty):
        await interaction.response.send_message(content="Error, the stock is not found", ephemeral=True)
        return
    user = interaction.user
    view = View()
    embed = discord.Embed(title=user.display_name, color = user.color)
    await edit_stock_market_view_and_embed(view, embed, ticker, user, interaction, amount)
    await interaction.response.send_message(embed=embed, view=view)

#Buy stocks
@client.tree.command(name="buy_stocks", description="Buy stocks")
@app_commands.describe(ticker="The stock ticker symbol that you want to look up")
@app_commands.describe(amount="Amount of stocks to buy/sell")
async def buy_stocks(interaction:discord.Interaction, ticker: str, amount: app_commands.Range[int,0]):
    stock_ticker = yf.Ticker(ticker)
    if(stock_ticker.cashflow.empty):
        await interaction.response.send_message(content="Error, the stock is not found", ephemeral=True)
        return
    user = interaction.user
    view = View()
    embed = discord.Embed(title=user.display_name, color = user.color)
    points = await db.get_points(user.id)
    stock_ticker_info = stock_ticker.info
    canAfford = points>=stock_ticker_info["ask"]*amount
    if (canAfford):
        await db.update_stock(user.id, stock_ticker_info, "Buy", amount)
    await edit_stock_market_view_and_embed(view=view, embed=embed, ticker=ticker, user=user, interaction=interaction, amount=amount)
    if (canAfford):
            embed.add_field(name="Action Result", value="Sucessfully bought "+str(amount)+" of "+stock_ticker_info["shortName"], inline=False)
    else:
        embed.add_field(name="Action Result", value="Too poor to afford the stocks", inline=False)
    await interaction.response.send_message(view=view, embed=embed)

#Sell stocks
@client.tree.command(name="sell_stocks", description="Sell stocks")
@app_commands.describe(ticker="The stock ticker symbol that you want to look up")
@app_commands.describe(amount="Amount of stocks to buy/sell")
async def sell_stocks(interaction:discord.Interaction, ticker: str, amount: app_commands.Range[int,0]):
    stock_ticker = yf.Ticker(ticker)
    if(stock_ticker.cashflow.empty):
        await interaction.response.send_message(content="Error, the stock is not found", ephemeral=True)
        return
    user = interaction.user
    view = View()
    embed = discord.Embed(title=user.display_name, color = user.color)
    stock_ticker_info = stock_ticker.info
    stock_ticker_amount = await db.get_amount_of_stock(user.id, ticker)
    hasStocks = amount<=stock_ticker_amount
    if (hasStocks):
        await db.update_stock(user.id, stock_ticker_info, "Sell", amount)
    await edit_stock_market_view_and_embed(view, embed, ticker, user, interaction, amount)
    if (hasStocks):
        embed.add_field(name="Action Result", value="Sucessfully sold "+str(amount)+" of "+stock_ticker_info["shortName"], inline=False)
    else:
        embed.add_field(name="Action Result", value="Too few stocks own to sell", inline=False)
    await interaction.response.send_message(view=view, embed=embed)

#Check owned stocks
@client.tree.command(name="owned_stocks", description="View stocks owned")
async def owned_stocks(interaction:discord.Interaction):
    user = interaction.user
    view = View()
    embed = discord.Embed(title=user.display_name, color = user.color)
    await edit_stock_market_view_and_embed(view, embed, interaction.user, interaction)
    await interaction.response.send_message(embed=embed, view=view)

#Update leaderboard
@client.tree.command(name="update_leaderboard", description="Refresh leaderboard")
@app_commands.checks.has_permissions(administrator=True)
async def update_leaderboard(interaction:discord.Interaction):
    await db.update_leader_board()
    user = interaction.user
    view = View()
    embed = discord.Embed(title=user.display_name, color = user.color)
    await edit_leaderboard(view, embed, interaction.user, interaction)
    await interaction.response.send_message(view=view, embed=embed)

#Error when a non-admin tries to update leaderboard 
@update_leaderboard.error
async def update_leaderboard_error(interaction, error):
    await interaction.response.send_message(content="You do not have the permission to update the leaderboard", ephemeral=True)

#Save the image and return the path of the image
def saveImage(url):
    path="Images/"+str(uuid.uuid4())
    urllib.request.urlretrieve(url, path)
    return path

#Remove a tag, name is the name of the tag
@client.tree.command(name="remove_tag", description="Remove a tag from the database")
@app_commands.describe(name="The name of the tag you want to display")
async def tag_image(interaction:discord.Interaction, name:str):
    data = await db.get_tag(name)
    if (data==None):
        await interaction.response.send_message("Error, tag was not found", ephemeral=True)
    elif (data[db.label_index.user_id.value]!=interaction.user.id):
        await interaction.response.send_message("Error, you did not create the tag", ephemeral=True)
    else:
        await db.delete_tag(name)
        await interaction.response.send_message("Tag deleted", ephemeral=True)        

#Slash command to only output image from tag database, name is name of tag
@client.tree.command(name="tag_image", description="Display the image relating to a tag")
@app_commands.describe(name="The name of the tag you want to display")
async def tag_image(interaction:discord.Interaction, name:str):
    data = await db.get_tag(name)
    if (data==None):
        await interaction.response.send_message("Error, tag was not found", ephemeral=True)
    else:
        image = data[db.label_index.label_image_path.value]
        if (image==""):
            await interaction.response.send_message("Error, tag has no text", ephemeral=True)
        else:
            await interaction.response.send_message(image)


#Slash command to only output text from tag database, name is name of tag
@client.tree.command(name="tag_text", description="Display the text relating to a tag")
@app_commands.describe(name="The name of the tag you want to display")
async def tag_text(interaction:discord.Interaction, name:str):
    data = await db.get_tag(name)
    if (data==None):
        await interaction.response.send_message("Error, tag was not found", ephemeral=True)
    else:
        text = data[db.label_index.label_text.value]
        if (text==""):
            await interaction.response.send_message("Error, tag has no text", ephemeral=True)
        else:
            await interaction.response.send_message(text)
        
#Slash command to output text and image from tag database, name is name of tag
@client.tree.command(name="tag", description="Display the information relating to a tag")
@app_commands.describe(name="The name of the tag you want to display")
async def tag(interaction:discord.Interaction, name:str):
    data = await db.get_tag(name)
    if (data==None):
        await interaction.response.send_message("Error, tag was not found", ephemeral=True)
    else:
        text = data[db.label_index.label_text.value]
        image = data[db.label_index.label_image_path.value]
        await interaction.response.send_message(text +" "+image)

#Lists all possible commands (is out of date TODO complete it)
@client.tree.command(name="help", description="Get some help")
async def help(interaction:discord.Interaction):
    await interaction.response.send_message("/help, !updateTag, !createTag, /tag, /tag_text, /tag_image, /remove_tag, /ping, /outputtotxt")
    
#Update a tag, assume any missing arugments are to be ignored
@client.command()
async def updateTag(ctx, *args):
    if (not ctx.message.author.bot):       
        attachement = ctx.message.attachments
        
        if (len(args)==0):
            await ctx.send("Arguments missing please use the following format of \'!update name text\' and then attach and image. Text and attachment are optional")
            return
        data = await db.getTag(args[0])
        if (data[db.LabelIndex.user_id.value]!=ctx.author.id):
            await ctx.send("Error, you did not create the tag")
        else:
            name = args[0]
            args = args[1:]
            if (len(attachement)>0):
                attachement = attachement[0]
            else:
                attachement = ""
            result = await db.update_tag(ctx.author.id, name, " ".join(str(word) for word in args), str(attachement))
            await ctx.send(result)
    
#Create a tag, excepts discord.py context and list of string arugments
@client.command()
async def createTag(ctx, *args):
     if (not ctx.message.author.bot):       
        attachement = ctx.message.attachments
        if (len(args)==0):
            await ctx.send("Arguments missing please use the following format of \'!createTag name text\' and then attach and image. Text and attachment are optional")
        else:
            name = args[0]
            args = args[1:]
            if (len(attachement)>0):
                attachement = attachement[0]
            else:
                attachement = ""
            result = await db.addTag(ctx.author.id, name, " ".join(str(word) for word in args), str(attachement))
            await ctx.send(result)
        


#Standard useful commands
@client.tree.command(name="ping", description="Check latency in nanoseconds to the bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message('Pong! '+str(round(client.latency*1000000000))+'ns', ephemeral=True)


#Based on my output to txt bot: https://github.com/jpang9431/DiscordBotToOuputTextToDocuments/blob/main/Bot.py
#Get all channel Ids
async def getChannelIds(interaction: discord.Interaction):
    await interaction.response.send_message("Started Process")
    guild = interaction.guild
    channels = guild.text_channels
    for channel in channels:
        await interaction.channel.send("#"+str(channel.id) + ","+channel.name)
    await interaction.channel.send("Done")

#Get all roles
async def getRoleIds(interaction: discord.Interaction):
    await interaction.response.send_message("Started Process")
    guild = interaction.guild
    roles = guild.roles
    for role in roles:
        if (role.name!="@everyone"):
         await interaction.channel.send("@&"+str(role.id)+">"+","+role.name)
    await interaction.channel.send("Done")

#Get all sepcial discord escape seuqences
async def getSpeicalCombinations(interaction: discord.Interaction, speicalEscapes, regularReplace,typeOfEscape):
    guild = interaction.guild
    filePath = sepical_text_output_file_path
    await interaction.response.send_message("Started")
    file = open(filePath, "w", encoding="utf-8")
    total = 0
    for role in guild.roles:
        speicalEscapes.append("<@&"+str(role.id)+">")
        regularReplace.append("@"+role.name)
        typeOfEscape.append("Role Ping")
        total+=1
    await interaction.channel.send(str(total)+" roles found excluding everyone")
    lastTotal = total
    for channel in guild.channels:
        speicalEscapes.append("<#"+str(channel.id)+">")
        regularReplace.append("#"+channel.name)
        typeOfEscape.append("Channel Mention")
        total+=1
    await interaction.channel.send(str(total-lastTotal)+" channels found")
    lastTotal = total
    for user in guild.members:
        speicalEscapes.append("<@"+str(user.id)+">")
        regularReplace.append("@"+user.display_name)
        typeOfEscape.append("User Ping")
        total+=1
    await interaction.channel.send(str(total-lastTotal)+" members found")
    lastTotal = total
    for emoji in guild.emojis:
        speicalEscapes.append("<:"+str(emoji.name)+":"+str(emoji.id)+">")
        regularReplace.append(":"+emoji.name+":")
        typeOfEscape.append("Emjoi Use")
        total+=1
    await interaction.channel.send(str(total-lastTotal)+" custom emjois found")
    for i in range(len(speicalEscapes)):
        file.write(speicalEscapes[i]+","+regularReplace[i]+","+typeOfEscape[i]+"\n")
    file.close()    



#Output all the information into a local txt
@client.tree.command(name="outputtotxt", description="Output and parse data from a discord group")
async def outputtotxt(interaction: discord.Interaction):
    global currentlyProcessing
    if (currentlyProcessing):
        await interaction.channel.send("Please wait for the current processing to be completed")
        return
    else:
        currentlyProcessing = True
    guild = interaction.guild
    speicalEscapes = []
    regularReplace = []
    typeOfEscape = []
    await getSpeicalCombinations(interaction, speicalEscapes, regularReplace, typeOfEscape)
    channels = guild.text_channels
    count = 0
    filepath = full_text_output_file_path
    file = open(filepath, "w+", encoding="utf-8")
    totalTime = time.time()
    #print(channels)
    for channel in channels:
        messagesInChannel = 0
        now = time.time()
        async for msg in channel.history(limit=2000000, oldest_first=True):
            if (msg.author.global_name!=None and msg.content!=""):
                strContent = msg.content.replace("\n"," ")
                for i in range(len(speicalEscapes)):
                    strContent = strContent.replace(speicalEscapes[i],regularReplace[i])
                item = str(msg.author.global_name) + "," + str(strContent)+"\n"
                file.write(item)
                count+=1
                messagesInChannel+=1
        now = time.time()-now
        await interaction.channel.send(str(messagesInChannel) + " messages by users outputted in "+channel.name+" | "+str(now))
    totalTime = time.time()-totalTime
    await interaction.channel.send(str(count) + " messages by users outputted | "+str(totalTime))
    file.close()
    Interpret.interpretMessage()
    Interpret.graph()
    for filePath in files:
        await interaction.channel.send(file=discord.File(filePath))
    currentlyProcessing = False

#Play blackjack what else would this command do
@client.tree.command(name="blackjack", description="Play a game of blackjack")
@app_commands.describe(bet="The amount you want to be must be >=0 and <= the number of points you have, if the bet is out of range it goes to the default of 0")
async def blackjack(interaction:discord.Interaction,bet:int=0):
    points = await db.get_points(interaction.user.id)
    if (bet<0 or bet>points):
        bet = 0
    emded = discord.Embed(color=interaction.user.color, title="Blackjack but worse")
    await db.update_points(interaction.user.id,bet*-1)
    blackjack = blackJack()
    emded.add_field(name="**Player Hand: "+str(blackjack.getPlayerHandValue())+"**", value=blackjack.stringPlayerHand, inline=False)
    emded.add_field(name="**Dealer Hand: "+str(blackjack.getDealerHandValue())+"**", value=blackjack.stringDealerHand, inline=False)
    view = View()
    view.add_item(back_button(interaction))
    view.add_item(blackjack_hit_button(interaction, blackjack, bet))
    view.add_item(blackjack_stay_button(interaction, blackjack, bet))
    await interaction.response.send_message(view=view, embed=emded)

#Flip coin command
@client.tree.command(name="coinflip", description="Flip a coin")
@app_commands.describe(bet="The amount you want to be must be >=0 and <= the number of points you have, if the bet is out of range it goes to the default of 0")
async def coinflip(interaction:discord.Interaction, bet:int=0):
    emded = discord.Embed(color=interaction.user.color, title="Flip coin for "+str(bet))
    view = View()
    view.add_item(back_button(interaction))
    view.add_item(flip_coin_button(interaction,bet,"Heads"))
    view.add_item(flip_coin_button(interaction,bet,"Tails"))
    await interaction.response.send_message(view=view,embed=emded)

#Create a button to allow for adding and removing role
@client.tree.command(name="role_button",description="Create a button to add/remove a role")
@app_commands.describe(text="The message you want sent with the button")
@app_commands.describe(role="The role you want to be attacted to the button")
async def roleButton(interaction:discord.Interaction, text:str, role:discord.Role):
    view = View(timeout=None)
    view.add_item(role_button(role.id,role.name))
    await interaction.response.send_message(text,view=view)
    
#Create multiple buttons for adding and remvoning roles
@client.tree.command(name="role_buttons",description="Create buttons to add/remove roles")
@app_commands.describe(text="The message you want sent with the button")
@app_commands.describe(roles="List of role ids seperated anything other than a number")
async def roleButton(interaction:discord.Interaction, text:str, roles:str):
    role_ids = re.findall(r'\d+',roles)
    view = View(timeout=None)
    guild = interaction.guild
    for role in role_ids:
        role_obj = guild.get_role(int(role))
        if (role_obj==None):
            await interaction.response.send_message(f"Role of id '{role}' could not be found", ephemeral=True)
            return
        else:
            view.add_item(role_button(role_obj.id,role_obj.name))
    await interaction.response.send_message(text,view=view)
    
    
@client.tree.command(name="clear",description="Clear a number of messages")
@app_commands.describe(count="The number of messages you want to delete")
@app_commands.checks.has_permissions(administrator=True)
async def clear(interaction:discord.Interaction,count:int):
    channel = interaction.channel
    await channel.purge(limit=count)
    await interaction.response.send_message("Done",ephemeral=True)

#Ouput all custuom emjois in a guild
@client.tree.command(name="output_emoji",description="output all emjois")
async def output_emoji(interaction:discord.Interaction):
    guild = interaction.guild
    for emoji in guild.emojis:
        await interaction.channel.send(emoji.name+":")
        await interaction.channel.send("<:"+emoji.name+":"+str(emoji.id)+">")

#Set time zone difference
@client.tree.command(name="set_timediff",description="output all emjois")
@app_commands.describe(hours="Difference between local and utc for the hours, aka Local-UTC bewteen [-12,14]")
@app_commands.describe(minutes="Difference between local and utc for the minutes place for the few places that have a minute offest, including {0,30,45}")
async def set_timediff(interaction:discord.Interaction, hours:int, minutes:int):
    if (hours<-12 or hours>14):
        await interaction.response.send_message("Error, enter in a hours amount that is greater than negative 12 and less than 14", ephemeral=True)
    elif (not (minutes==0 or minutes==30 or minutes == 45)):
        await interaction.response.send_message("Error, minute time difference must be 0 or 30 or 45", ephemeral=True)
    else:
        await db.update_user_time_offest(interaction.user.id, hours, minutes)
        await interaction.response.send_message("Done", ephemeral=True)

def run_process_event(event_id):
    asyncio.run_coroutine_threadsafe(process_event(event_id), loop)  

#Create an event
@client.tree.command(name="create_event",description="Create an event that will occur in the future")
@app_commands.describe(channel_id="The channel you want the event notification to")
@app_commands.describe(title="The title of the event")
@app_commands.describe(description="The description of the event")
@app_commands.describe(year="The year number of the event that is >= current year")
@app_commands.describe(month="The month number of the event where it is in the range of [1,12]")
@app_commands.describe(day="The day number of the event where it is in the range of [1,31]")
@app_commands.describe(minute="The number of minutes where it is in the range of [0,59]")
@app_commands.describe(next_repeat="The next time you want this to repeat, foramt it as yyyy-mm-dd, leave it blank if you do not want it to repeat and skip the next paramter")
@app_commands.describe(end_date="The date you want the repeats to end, leave blank if you want it to repeat forever")
async def create_event(interaction:discord.Interaction,channel_id:str,title:str,description:str,year:int,month:int,day:int,hour:int,minute:int,next_repeat:str="",end_date:str=""):
    try:
        channel_id = int(channel_id)
    except:
        await interaction.response.send_message("Error, you have to input a valid number")
        return
    if (len(description)>max_characters):
        await interaction.response.send_message("The description must be less than 1024 charactesr", ephemeral=True)
        return
    try:
        await interaction.guild.fetch_channel(channel_id)
    except:
        await interaction.response.send_message("Enter in a valid channel that is a channel in the guild you are currently running the command in", ephemeral=True)
        return
    time_diff = await db.get_time_offset(interaction.user.id)
    if (time_diff == None):
        await interaction.response.send_message("Please set your time zone difference using /set_time_diff") 
        return
    date = None
    try:
        date = datetime(year=year, month=month, day=day, hour=hour, minute=minute) - time_diff
    except:
        await interaction.response.send_message("The date entered is invalid",ephemeral=True)
        return
    future = await db.check_future(date)
    if (not future):
        await interaction.response.send_message("Enter a date/time that is in the future", ephemeral=True)
    else:
        if (not next_repeat == ""):
            try:
                datetime.fromisoformat(next_repeat)
            except:
                await interaction.response.send_message("Enter a valid next repeat date", ephemeral=True)
                return
            if (not end_date == ""):
                try:
                    repeat_end_date = datetime.fromisoformat(end_date) + time_diff
                    end_date = repeat_end_date.isoformat(sep="T", timespec="auto")
                    if (end_date<date):
                        await interaction.response.send_message("Enter an end date that is in the future when compared to the start event date", ephemeral=True)
                        return
                except:
                    await interaction.response.send_message("Enter a valid end date", ephemeral=True)
                    return     
        await interaction.response.send_message("The event was added sucessfully", ephemeral=True)
        event_id = str(uuid.uuid4())
        await db.add_event(date=date.isoformat(sep="T", timespec="auto"), title=title, description=description, end_date=end_date, next_repeat=next_repeat, guild=interaction.guild.id, channel=channel_id, event_id=event_id, owner=interaction.user.id)
        if (str(date.date())==str(current_date_processing.date()) or str(date.date())==str((current_date_processing-next_date).date())):
            if (scheduler.get_job(str(event_id))==None):
                global loop
                scheduler.add_job(func=lambda: run_process_event(event_id=event_id), trigger=DateTrigger(run_date=date, timezone=pytz.timezone("UTC")), misfire_grace_time=None)

async def add_events():
    all_events = await db.get_all_events()
    twomorrow = current_date_processing + next_date
    twomorrow_timestamp = twomorrow.timestamp()
    current_time = datetime.now(tz=pytz.timezone("UTC")).timestamp()
    for event in all_events:
        event_date = datetime.fromisoformat(event[1])
        date_timestamp = event_date.timestamp()
        if (date_timestamp<=current_time):
            process_event(event[1])
        elif (date_timestamp<=twomorrow_timestamp and scheduler.get_job(event[0]) == None):
            scheduler.add_job(func=lambda: run_process_event(event_id=event[0]), trigger=DateTrigger(run_date=event_date, timezone=pytz.timezone("UTC")), misfire_grace_time=None)
            print(event[0])
        

async def process_event(event_id:str):
    event = await db.process_event(event_id=event_id)
    channel = await client.fetch_channel(event["channel_id"])
    if (event["next_date"] == str(current_date_processing.date())):
        scheduler.add_job(func=lambda: run_process_event(event_id=event_id), trigger=DateTrigger(run_date=datetime.fromisoformat(event[db.event_data_index.event_date.value]), timezone=pytz.timezone("UTC")), misfire_grace_time=None)
    embed = discord.Embed()
    view = View()
    await ui.event_embed_and_view(embed=embed, view=view, event=event)
    await channel.send(content=event["participants"], embed=embed, view=view)

async def event_info_embed(event_id:str, process_event:bool):
    event = None
    if (process_event):
        event = await db.process_event(event_id=event_id)
    else:
        event = await db.get_event_data_dict(event_id=event_id)
    owner:discord.User = await client.fetch_user(event["owner_id"])
    embed = discord.Embed(color=owner.color, title=event["title"], description=event["description"])
    embed.add_field(name="Date Information", value=f"Current date:{db.calc_time_day_str(event["current_event_date"],owner.id)}, Next date:{db.calc_time_day_str(event["next_date"],owner.id)}, End date:{db.calc_time_day_str(event["event_end"],owner.id)}")
    embed.add_field(name="Participants", value=event["participants"])
    embed.set_thumbnail(owner.display_avatar)
    view = View()
    view.add_item(ui.event_button(event_id=event_id))
    
@client.tree.command(name="get_events", description="Get all events that are scheduled from this guild")
async def get_events(interaction:discord.Interaction):
    guild_id = interaction.guild_id
    events = await db.get_events_by_guild(guild_id=guild_id)
    text = ""
    for event in events:
        text += "Event name: " + str(event[db.event_data_index.event_name.value]) + "\n  Date: "+str(event[db.event_data_index.event_date.value]) + "\n  Event id: " + str(event[db.event_data_index.event_id.value]) + "\n"
        text += "\n"
    embed = discord.Embed()
    embed.title = interaction.guild.name
    embed.description = "List of events in UTC time"
    embed.add_field(name="Events", value=text)
    await interaction.response.send_message(embed=embed)
    
@client.tree.command(name="get_event", description="Get full details about an event")
@app_commands.describe(event_id="The id of the event")
async def get_event(interaction:discord.Interaction, event_id:str):
    event = await db.get_event_data_dict(event_id) 
    embed = discord.Embed()
    view = View()
    await ui.event_embed_and_view(embed=embed, view=view, event=event)
    await interaction.response.send_message(embed=embed, view=view)

#Runs the bot token
client.run(token)

