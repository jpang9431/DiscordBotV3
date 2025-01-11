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
file_data = json.load(config)

#File paths for raw text files
full_text_output_file_path = home_directory+file_data["full_text_output_file_path"]
sepical_text_output_file_path = home_directory+file_data["sepical_text_output_file_path"]

#file paths for processed text files
word_count_file_path = home_directory+file_data["word_count_file"]
special_count_file_path = home_directory+file_data["special_count_file"]
char_count_file_path = home_directory+file_data["character_count_file"]
link_count_file_path = home_directory+file_data["links_file"]
ping_graph = home_directory+file_data["ping_graph"]
bad_words = home_directory+file_data["bad_word_file"]
James_words = home_directory+file_data["James_words"]
bad_words_file_path = home_directory+file_data["bad_word_output"]
James_words_file_path = home_directory+file_data["James_words_output"]

bad_words_list = []
James_words_list = []

with open(bad_words, newline='') as file:
    reader = csv.reader(file)
    for lines in reader:
        bad_words_list.append(lines[0])
    
with open(James_words, newline='') as file:
    reader = csv.reader(file)
    for lines in reader:
        James_words_list.append(lines[0])
        
#Transfer words from a soruce ditionary to a target dictionary with the words being in the words list
def transfer_words(source_dict, target_dict, words):
    for word in words:
        if (word in source_dict):
            target_dict[word] = source_dict[word]

#Adds a word to two dictionaries if not found otherwise increment by one, lowercase is wether the words should be made lowercase
def add_words_to_dictionary(dict, everyone_dict, words, lowercase=False):
    for word in words:
        if (lowercase):
            word = word.lower()
        if word:
            if (word in dict):
                dict[word] = dict[word]+1
            else:
                dict[word] = 1
            if (word in everyone_dict):
                everyone_dict[word] = everyone_dict[word]+1
            else:
                everyone_dict[word] = 1

#Write the data from a dictonary to a file
def write_to_file_from_dict(file_path, dictionary):
    with open (file_path, "w+", encoding="utf-8") as f:
        f.write("{")
        count = 0
        num_dicts = len(dictionary)
        for key in dictionary.keys():
            string = "\n"
            count+=1
            if (count<num_dicts):
                string = ","+string
            temp_dict = dictionary[key]
            f.write('"'+key+'":')
            f.write(json.dumps(dict(sorted(temp_dict.items(), key=lambda item: item[1], reverse=True)), ensure_ascii=False)+string)
        f.write("}")
        f.close()

#Interepet all the text in raw files
def interpret_message():
    user_words_dictionary = dict()
    user_words_dictionary["Everyone"] = dict()
    user_speical = dict()
    user_speical["Everyone"] = dict()
    user_char = dict()
    user_char["Everyone"] = dict()
    user_link = dict()
    user_link["Everyone"] = dict()
    speical = "("
    users = []
    with open(sepical_text_output_file_path, "r", encoding="utf8") as f:
        lines = f.readlines()
        for line in lines:
            list = line.split(",")
            speical+=list[1]
            speical+="|"
        speical = speical[:-1]
        speical += ")+"
        f.close()
    speical_reg_ex = re.compile(speical)
    word_reg_ex = re.compile(r'\w+|[^\s\w]')
    link_reg_ex = re.compile(r'http://[^\s]+|https://[^\s]+')
    file = open(full_text_output_file_path, "r", encoding="utf8")
    lines = file.readlines()
    for line in lines:
        list = line.split(",",1)
        user = list[0]
        links = re.findall(link_reg_ex, list[1])
        list[1] = re.sub(link_reg_ex, '', list[1])
        speical_words = re.findall(speical_reg_ex, list[1])
        words = re.findall(word_reg_ex, list[1])
        chars = re.findall(r".",list[1])
        if not user in user_speical:
            user_speical[user] = dict()
            user_char[user] = dict()
            user_words_dictionary[user] = dict()
            user_link[user] = dict()
            users.append(user)
        user_speicalDict = user_speical[user]
        userWordsDict = user_words_dictionary[user]
        user_charDict= user_char[user]
        user_linkDict = user_link[user]
        speical_thread = threading.Thread(target=add_words_to_dictionary, args=(user_speicalDict, user_speical["Everyone"], speical_words))
        word_thread = threading.Thread(target=add_words_to_dictionary, args=(userWordsDict, user_words_dictionary["Everyone"], words, True))
        char_thread = threading.Thread(target=add_words_to_dictionary, args=(user_charDict, user_char["Everyone"], chars, True))
        link_thread = threading.Thread(target=add_words_to_dictionary, args=(user_linkDict, user_link["Everyone"], links))
        speical_thread.start()
        word_thread.start()
        char_thread.start()
        link_thread.start()
        speical_thread.join()
        word_thread.join()
        char_thread.join()
        link_thread.join()
    bad_words_dict = dict()
    James_words_dict = dict()
    for user in users:
        user_word_dict = user_words_dictionary[user]
        user_bad_word_dict = dict()
        user_James_word_dict = dict()
        transfer_words(user_word_dict,user_bad_word_dict,bad_words_list)
        transfer_words(user_word_dict, user_James_word_dict,James_words_list)
        bad_words_dict[user] = user_bad_word_dict
        James_words_dict[user] = user_James_word_dict
    add_bad_words = threading.Thread(target=write_to_file_from_dict, args=(bad_words_file_path,bad_words_dict))
    add_James_words = threading.Thread(target=write_to_file_from_dict,args=(James_words_file_path,James_words_dict))    
    add_words = threading.Thread(target=write_to_file_from_dict, args=(word_count_file_path, user_words_dictionary))
    add_specials = threading.Thread(target=write_to_file_from_dict, args=(special_count_file_path, user_speical))
    add_chars = threading.Thread(target=write_to_file_from_dict, args=(char_count_file_path, user_char))
    add_links = threading.Thread(target=write_to_file_from_dict, args=(link_count_file_path, user_link))
    add_bad_words.start()
    add_James_words.start()
    add_words.start()
    add_specials.start()
    add_chars.start()
    add_links.start()
    add_bad_words.join()
    add_James_words.join()
    add_words.join()
    add_specials.join()
    add_chars.join()
    add_links.join()
    print("Done")
    file.close()

#Print to utf8 for testing purchases
def printUTF8(text):
    print(text.encode("utf8"))

#Genetate a graph of pings
def graph():
    graph_as_adjaceny_list = dict()
    valid_pings = []
    with open(sepical_text_output_file_path, "r", encoding="utf8") as f:
        lines = f.readlines()
        for line in lines:
            line = line[:-1]
            data = line.split(",")
            if (data[2]=="User Ping"):
                valid_pings.append(data[1])
        f.close()  
    with open(special_count_file_path, "r", encoding="utf8") as f:
        special_dicts = json.load(f)
        for key in special_dicts:
            if key!="Everyone":
                adjancy_dict= dict()
                user_dictionary = special_dicts.get(key) 
                for ping in valid_pings:
                    if ping in user_dictionary:
                        adjancy_dict[ping] = user_dictionary[ping]
                graph_as_adjaceny_list[key] = adjancy_dict         
        f.close()
    write_to_file_from_dict(ping_graph, graph_as_adjaceny_list)

#Gerenate a graph from strings
def generate_graph():
    file = open(ping_graph, "r", encoding="utf8")
    data = json.load(file)
    graph = nx.DiGraph()
    for key, value in data.items():
        for alt_key in value.keys():
            graph.add_edge(key, alt_key[1:], weight = value[alt_key])
    pos = nx.spring_layout(graph)
    nx.draw(graph, pos, with_labels=True, node_size=9000, node_color="skyblue", edge_color="gray")
    plt.show()

#Testing method which runs interepetMessage if this the file ran to allow the file to be ran indpent of bot code
if __name__ == "__main__":
    interpret_message()