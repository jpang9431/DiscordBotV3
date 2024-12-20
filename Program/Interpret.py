import csv
import json
import re
import threading
import networkx as nx
import matplotlib.pyplot as plt

#Home directory is the directory to the DiscordBotV3 folder + /
home_directory = ""

#loads settings file
config = open(home_directory+"config.json")
fileData = json.load(config)

#File paths for raw text files
fullTextOutputFilePath = home_directory+fileData["fullTextOutputFilePath"]
sepicalTextOutputFilePath = home_directory+fileData["sepicalTextOutputFilePath"]

#file paths for processed text files
wordCountFilePath = home_directory+fileData["wordCountFile"]
specialCountFilePath = home_directory+fileData["specialCountFile"]
charCountFilePath = home_directory+fileData["characterCountFile"]
linkCountFilePath = home_directory+fileData["linksFile"]
pingGraph = home_directory+fileData["pingGraph"]
badWords = home_directory+fileData["badWordFile"]
JamesWords = home_directory+fileData["JamesWords"]
badWordsFilePath = home_directory+fileData["badWordOutput"]
JamesWordsFilePath = home_directory+fileData["JamesWordsOutput"]

badWordsList = []
JamesWordsList = []

with open(badWords, newline='') as file:
    reader = csv.reader(file)
    for lines in reader:
        badWordsList.append(lines[0])
    
with open(JamesWords, newline='') as file:
    reader = csv.reader(file)
    for lines in reader:
        JamesWordsList.append(lines[0])
#Transfer words from a soruce ditionary to a target dictionary with the words being in the words list
def transferWords(sourceDict, targetDict, words):
    for word in words:
        if (word in sourceDict):
            targetDict[word] = sourceDict[word]

#Adds a word to two dictionaries if not found otherwise increment by one, lowercase is wether the words should be made lowercase
def addWordsToDictionary(dict, everyoneDict, words, lowercase=False):
    for word in words:
        if (lowercase):
            word = word.lower()
        if word:
            if (word in dict):
                dict[word] = dict[word]+1
            else:
                dict[word] = 1
            if (word in everyoneDict):
                everyoneDict[word] = everyoneDict[word]+1
            else:
                everyoneDict[word] = 1

#Write the data from a dictonary to a file
def writeToFileFromDict(filePath, dictionary):
    with open (filePath, "w+", encoding="utf-8") as f:
        f.write("{")
        count = 0
        numDicts = len(dictionary)
        for key in dictionary.keys():
            string = "\n"
            count+=1
            if (count<numDicts):
                string = ","+string
            tempDict = dictionary[key]
            f.write('"'+key+'":')
            f.write(json.dumps(dict(sorted(tempDict.items(), key=lambda item: item[1], reverse=True)), ensure_ascii=False)+string)
        f.write("}")
        f.close()

#Interepet all the text in raw files
def interpretMessage():
    userWordsDictionary = dict()
    userWordsDictionary["Everyone"] = dict()
    userSpeical = dict()
    userSpeical["Everyone"] = dict()
    userChar = dict()
    userChar["Everyone"] = dict()
    userLink = dict()
    userLink["Everyone"] = dict()
    speical = "("
    users = []
    with open(sepicalTextOutputFilePath, "r", encoding="utf8") as f:
        lines = f.readlines()
        for line in lines:
            list = line.split(",")
            speical+=list[1]
            speical+="|"
        speical = speical[:-1]
        speical += ")+"
        f.close()
    speicalRegEx = re.compile(speical)
    wordRegEx = re.compile(r'\w+|[^\s\w]')
    linkRegEx = re.compile(r'http://[^\s]+|https://[^\s]+')
    file = open(fullTextOutputFilePath, "r", encoding="utf8")
    lines = file.readlines()
    for line in lines:
        list = line.split(",",1)
        user = list[0]
        links = re.findall(linkRegEx, list[1])
        list[1] = re.sub(linkRegEx, '', list[1])
        speicalWords = re.findall(speicalRegEx, list[1])
        words = re.findall(wordRegEx, list[1])
        chars = re.findall(r".",list[1])
        if not user in userSpeical:
            userSpeical[user] = dict()
            userChar[user] = dict()
            userWordsDictionary[user] = dict()
            userLink[user] = dict()
            users.append(user)
        userSpeicalDict = userSpeical[user]
        userWordsDict = userWordsDictionary[user]
        userCharDict= userChar[user]
        userLinkDict = userLink[user]
        speicalThread = threading.Thread(target=addWordsToDictionary, args=(userSpeicalDict, userSpeical["Everyone"], speicalWords))
        wordThread = threading.Thread(target=addWordsToDictionary, args=(userWordsDict, userWordsDictionary["Everyone"], words, True))
        charThread = threading.Thread(target=addWordsToDictionary, args=(userCharDict, userChar["Everyone"], chars, True))
        linkThread = threading.Thread(target=addWordsToDictionary, args=(userLinkDict, userLink["Everyone"], links))
        speicalThread.start()
        wordThread.start()
        charThread.start()
        linkThread.start()
        speicalThread.join()
        wordThread.join()
        charThread.join()
        linkThread.join()
    badWordsDict = dict()
    JamesWordsDict = dict()
    for user in users:
        userWordDict = userWordsDictionary[user]
        userBadWordDict = dict()
        userJamesWordDict = dict()
        transferWords(userWordDict,userBadWordDict,badWordsList)
        transferWords(userWordDict, userJamesWordDict,JamesWordsList)
        badWordsDict[user] = userBadWordDict
        JamesWordsDict[user] = userJamesWordDict
    addBadWords = threading.Thread(target=writeToFileFromDict, args=(badWordsFilePath,badWordsDict))
    addJamesWords = threading.Thread(target=writeToFileFromDict,args=(JamesWordsFilePath,JamesWordsDict))    
    addWords = threading.Thread(target=writeToFileFromDict, args=(wordCountFilePath, userWordsDictionary))
    addSpecials = threading.Thread(target=writeToFileFromDict, args=(specialCountFilePath, userSpeical))
    addChars = threading.Thread(target=writeToFileFromDict, args=(charCountFilePath, userChar))
    addLinks = threading.Thread(target=writeToFileFromDict, args=(linkCountFilePath, userLink))
    addBadWords.start()
    addJamesWords.start()
    addWords.start()
    addSpecials.start()
    addChars.start()
    addLinks.start()
    addBadWords.join()
    addJamesWords.join()
    addWords.join()
    addSpecials.join()
    addChars.join()
    addLinks.join()
    print("Done")
    file.close()

#Print to utf8 for testing purchases
def printUTF8(text):
    print(text.encode("utf8"))

#Genetate a graph of pings
def graph():
    graphAsAdjacenyList = dict()
    validPings = []
    with open(sepicalTextOutputFilePath, "r", encoding="utf8") as f:
        lines = f.readlines()
        for line in lines:
            line = line[:-1]
            data = line.split(",")
            if (data[2]=="User Ping"):
                validPings.append(data[1])
        f.close()  
    with open(specialCountFilePath, "r", encoding="utf8") as f:
        specialDicts = json.load(f)
        for key in specialDicts:
            if key!="Everyone":
                adjancyDict= dict()
                userDictionary = specialDicts.get(key) 
                for ping in validPings:
                    if ping in userDictionary:
                        adjancyDict[ping] = userDictionary[ping]
                graphAsAdjacenyList[key] = adjancyDict         
        f.close()
    writeToFileFromDict(pingGraph, graphAsAdjacenyList)

#Gerenate a graph from strings
def generateGraph():
    file = open(pingGraph, "r", encoding="utf8")
    data = json.load(file)
    graph = nx.DiGraph()
    for key, value in data.items():
        for altKey in value.keys():
            graph.add_edge(key, altKey[1:], weight = value[altKey])
    pos = nx.spring_layout(graph)
    nx.draw(graph, pos, with_labels=True, node_size=9000, node_color="skyblue", edge_color="gray")
    plt.show()

#Testing method which runs interepetMessage if this the file ran to allow the file to be ran indpent of bot code
if __name__ == "__main__":
    interpretMessage()