import os
import time
import discord
from discord import app_commands
from discord.ext import commands
import json
import Interpret
import Database as db
from dotenv import load_dotenv 
import urllib.request
import uuid
from Bot_Ui import back_button, blackjack_hit_button, blackjack_stay_button, edit_menu, flip_coin_button
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

#Loads the envrioment varaibles
load_dotenv() 

#Global variables
token = os.getenv("token")
config = open("config.json")
fileData = json.load(config)

#File paths for the output to txt raw files
fullTextOutputFilePath = fileData["fullTextOutputFilePath"]
sepicalTextOutputFilePath = fileData["sepicalTextOutputFilePath"]

#File paths for the output to txt processed files
wordCountFilePath = fileData["wordCountFile"]
specialCountFilePath = fileData["specialCountFile"]
charCountFilePath = fileData["characterCountFile"]
linkCountFilePath = fileData["linksFile"]
badWordsFilePath = fileData["badWordOutput"]
JamesWordsFilePath = fileData["JamesWordsOutput"]

#List of all files
files = [fullTextOutputFilePath, sepicalTextOutputFilePath, wordCountFilePath, specialCountFilePath, charCountFilePath, linkCountFilePath, badWordsFilePath, JamesWordsFilePath]

#Prevents race condition for writing to document
currentlyProcessing = False

#Necessary default bot stuff
client = commands.Bot(command_prefix='!', intents=discord.Intents.all())

#Set up the leaderboard to update at ceratin periods of time
async def updateLeaderBoardInterval():
    while True:
        await db.update_leader_board()
        await asyncio.sleep(3600)
        
#Event trigger as soon as the program is run
@client.event
async def on_ready():
    await db.create_repository()
    print("Online")
    synced = await client.tree.sync()
    print(len(synced))
    await db.update_leader_board()
    await updateLeaderBoardInterval()
    
#Handle the bot being added to a new guild
async def add_guild(guild):
    for user in guild.members:
        if not user.bot:
            await db.insert_new_user_if_no_exists(user.id, user.global_name)
            
#Trigger adding all users in a guild
@client.event
async def on_guild_join(guild):
    await add_guild(guild)

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
    filePath = sepicalTextOutputFilePath
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
    filepath = fullTextOutputFilePath
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

#Runs the bot token
client.run(token)