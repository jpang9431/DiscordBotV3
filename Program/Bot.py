import os
import datetime
import time
import discord
from discord import app_commands
from discord.ext import commands
import json
import Interpret
import Database as db
from dotenv import load_dotenv, dotenv_values 
import urllib.request
import uuid

load_dotenv() 

#Global variables
token = os.getenv("token")
config = open("config.json")
fileData = json.load(config)

fullTextOutputFilePath = fileData["fullTextOutputFilePath"]
sepicalTextOutputFilePath = fileData["sepicalTextOutputFilePath"]

wordCountFilePath = fileData["wordCountFile"]
specialCountFilePath = fileData["specialCountFile"]
charCountFilePath = fileData["characterCountFile"]
linkCountFilePath = fileData["linksFile"]

files = [fullTextOutputFilePath, sepicalTextOutputFilePath, wordCountFilePath, specialCountFilePath, charCountFilePath, linkCountFilePath]

#Prevents race condition for writing to document
currentlyProcessing = False

#Necessary default bot stuff
client = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@client.event
async def on_ready():
    await db.createRepository()
    print("Online")
    synced = await client.tree.sync()
    print(len(synced))
    

#Save the image and return the path of the image
def saveImage(url):
    path="Images/"+str(uuid.uuid4())
    urllib.request.urlretrieve(url, path)
    return path

#Remove a tag, name is the name of the tag
@client.tree.command(name="remove_tag", description="Remove a tag from the database")
@app_commands.describe(name="The name of the tag you want to display")
async def tag_image(interaction:discord.Interaction, name:str):
    data = await db.getTag(name)
    if (data==None):
        await interaction.response.send_message("Error, tag was not found", ephemeral=True)
    elif (data[db.LabelIndex.user_id.value]!=interaction.user.id):
        await interaction.response.send_message("Error, you did not create the tag", ephemeral=True)
    else:
        await db.deleteTag(name)
        await interaction.response.send_message("Tag deleted", ephemeral=True)        

#Slash command to only output image from tag database, name is name of tag
@client.tree.command(name="tag_image", description="Display the image relating to a tag")
@app_commands.describe(name="The name of the tag you want to display")
async def tag_image(interaction:discord.Interaction, name:str):
    data = await db.getTag(name)
    if (data==None):
        await interaction.response.send_message("Error, tag was not found", ephemeral=True)
    else:
        image = data[db.LabelIndex.label_image_path.value]
        if (image==""):
            await interaction.response.send_message("Error, tag has no text", ephemeral=True)
        else:
            await interaction.response.send_message(image)


#Slash command to only output text from tag database, name is name of tag
@client.tree.command(name="tag_text", description="Display the text relating to a tag")
@app_commands.describe(name="The name of the tag you want to display")
async def tag_text(interaction:discord.Interaction, name:str):
    data = await db.getTag(name)
    if (data==None):
        await interaction.response.send_message("Error, tag was not found", ephemeral=True)
    else:
        text = data[db.LabelIndex.label_text.value]
        if (text==""):
            await interaction.response.send_message("Error, tag has no text", ephemeral=True)
        else:
            await interaction.response.send_message(text)
        
#Slash command to output text and image from tag database, name is name of tag
@client.tree.command(name="tag", description="Display the information relating to a tag")
@app_commands.describe(name="The name of the tag you want to display")
async def tag(interaction:discord.Interaction, name:str):
    data = await db.getTag(name)
    if (data==None):
        await interaction.response.send_message("Error, tag was not found", ephemeral=True)
    else:
        text = data[db.LabelIndex.label_text.value]
        image = data[db.LabelIndex.label_image_path.value]
        await interaction.response.send_message(text +" "+image)

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
            result = await db.updateTag(ctx.author.id, name, " ".join(str(word) for word in args), str(attachement))
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
async def getChannelIds(interaction: discord.Interaction):
    await interaction.response.send_message("Started Process")
    guild = interaction.guild
    channels = guild.text_channels
    for channel in channels:
        await interaction.channel.send("#"+str(channel.id) + ","+channel.name)
    await interaction.channel.send("Done")

async def getRoleIds(interaction: discord.Interaction):
    await interaction.response.send_message("Started Process")
    guild = interaction.guild
    roles = guild.roles
    for role in roles:
        if (role.name!="@everyone"):
         await interaction.channel.send("@&"+str(role.id)+">"+","+role.name)
    await interaction.channel.send("Done")

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

async def getspecialcombinations(interaction: discord.Interaction):
    speicalEscapes = []
    regularReplace = []
    typeOfEscape = []
    await getSpeicalCombinations(interaction, speicalEscapes, regularReplace, typeOfEscape)

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

client.run(token)