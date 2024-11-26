import discord
import json
import Database as db
from discord.ui import View
import random
import yfinance as yf
from Minigame import blackJack

#List of quests and the quest dictionary from databse
quests = db.quests
quest_dict = db.quest_dict

black_jack_payout = 1.5

#Function to handle a back button 
class back_button(discord.ui.Button):
    def __init__(self, interaction:discord.Interaction):
        super().__init__(label="Back", style=discord.ButtonStyle.blurple)
        self.interaction = interaction
    async def callback(self,interaction:discord.Interaction):
        await interaction_reply_menu(self.interaction, interaction)

#Handle the menu interaction
async def interaction_reply_menu(origninal_interaction, current_interaction):
    user = current_interaction.user
    embed = discord.Embed(title=user.display_name, color = user.color)
    view = View()
    await edit_menu(view, embed, user, origninal_interaction)
    await origninal_interaction.edit_original_response(view=view, embed=embed)
    await current_interaction.response.defer()

#Handle editning the menu with the correct information
async def edit_menu(view:discord.ui.View, embed:discord.Embed, user:discord.User, interaction:discord.Interaction):
    if (not user.avatar == None):
        embed.set_thumbnail(url=user.avatar.url)
    data = await db.get_user_data(user.id)
    embed.add_field(name="Menu", value="Click a button below to go to that section")
    embed.add_field(name="User Stats", value="Position: "+str(data[0])+"\nTotal: "+str(data[2])+"\nPoints: "+str(data[3])+"\nStocks: "+str(data[4]),inline=False)
    embed.set_footer(text="*Position and stock last updated: "+str(await db.get_last_update()))
    view.add_item(daily_button(interaction))
    view.add_item(refresh_leaderboard(interaction, "Leader Board"))
    view.add_item(claim_quests_button(interaction, "Quest")) 
    view.add_item(refresh_stocks(interaction, "Stocks"))
    view.add_item(play_blackjack_button(interaction,"Blackjack"))
    view.add_item(play_coin_flip_button(interaction,"Coin Flip"))
    
    
    
#Button to be able to claim quests
class claim_quests_button(discord.ui.Button):
    def __init__(self, interaction:discord.Interaction, label:str):
        super().__init__(label=label, style=discord.ButtonStyle.blurple)
        self.interaction = interaction
    async def callback(self,interaction:discord.Interaction):
        pointsGained = await db.claim_quests(interaction.user.id)
        await db.update_points(interaction.user.id, pointsGained)
        user = interaction.user
        embed = discord.Embed(title=user.display_name, color = user.color)
        view = View()
        await edit_quest(view, embed, user, self.interaction)
        embed.add_field(name="Reward", value="You gained "+str(pointsGained)+" points", inline=False)
        await self.interaction.edit_original_response(view=view, embed=embed)
        await interaction.response.defer()

#Button to get new quests
class get_new_quests_button(discord.ui.Button):
    def __init__(self, interaction:discord.Interaction):
        super().__init__(label="Replace Completed Quests", style=discord.ButtonStyle.blurple)
        self.interaction = interaction
    async def callback(self,interaction:discord.Interaction):
        user = interaction.user
        embed = discord.Embed(title=user.display_name, color = user.color)
        view = View()
        if (await db.check_quest_cooldown(interaction.user.id)):
            await db.set_new_quets(interaction.user.id)
            await db.reset_quest_cooldown(interaction.user.id)
            await edit_quest(view, embed, user, self.interaction)
        else:
            await edit_quest(view, embed, user, self.interaction)
            embed.add_field(name="Cooldown", value="Wait until twomorrow to replace completed quests", inline= False)
        await self.interaction.edit_original_response(view=view, embed=embed)
        await interaction.response.defer()
        
#Button to reset current quests
class reset_quests_button(discord.ui.Button):
    def __init__(self, interaction:discord.Interaction):
        super().__init__(label="Replace All Quets", style=discord.ButtonStyle.blurple)
        self.interaction = interaction
    async def callback(self, interaction:discord.Interaction):
        user=  interaction.user
        embed = discord.Embed(title=user.display_name, color = user.color)
        view = View()
        if (await db.check_quest_cooldown(interaction.user.id)):
            await db.reset_quests(interaction.user.id)
            await db.reset_quest_cooldown(interaction.user.id)
            await edit_quest(view, embed, user, self.interaction)
        else:
            await edit_quest(view, embed, user, self.interaction)
            embed.add_field(name="Cooldown", value="Wait until twomorrow to replace all quests", inline = False)
        await self.interaction.edit_original_response(view=view, embed=embed)
        await interaction.response.defer()

#Method to interept quest into actual text from dictionary
async def interpret_quest(quest):
    msg = quests.get(quest["id"])
    msg = msg.replace("?",str(quest["goal"]))
    msg = msg.replace("*",str(quest["progress"]))
    if (quest["goal"]==1):
        msg = msg.replace("(s)","")
    else:
        msg = msg.replace("(s)", "s")
    msg += " - Reward: " + str(quest["points"])
    if (quest["progress"]>=quest["goal"]):
        msg = "~~"+msg+"~~"
    return msg +"\n"

#Edit the quest embed to have the correct information
async def edit_quest(view:discord.ui.View, embed:discord.Embed, user:discord.User, interaction):
    if (not user.avatar == None):
        embed.set_thumbnail(url=user.avatar.url)
    questList = await db.get_quests(user.id)
    textQuests = ""
    for quest in questList:
        textQuests+=await interpret_quest(quest)
    embed.add_field(name="Quests", value=textQuests)
    view.add_item(back_button(interaction))
    view.add_item(claim_quests_button(interaction, "Claim Quest"))
    view.add_item(get_new_quests_button(interaction))
    view.add_item(reset_quests_button(interaction))
    
#Button to claim daily reward
class daily_button(discord.ui.Button):
    def __init__(self, interaction:discord.Interaction):
        super().__init__(label="Daily", style=discord.ButtonStyle.blurple)
        self.interaction = interaction
    async def callback(self, interaction:discord.Interaction):
        user = interaction.user
        user = interaction.user
        view = View()
        embed = discord.Embed(title=user.display_name, color = user.color)
        await edit_daily(view, embed, user, self.interaction)
        await self.interaction.edit_original_response(view=view, embed=embed)
        await interaction.response.defer()

#Method to edit the daily embed with the correct information
async def edit_daily(view:discord.ui.View, embed:discord.Embed, user:discord.User, interaction:discord.Interaction):   
    if (not user.avatar == None):
        embed.set_thumbnail(url=user.avatar.url)
    embed.add_field(name="Daily", value="Click below to claim a daily reward")
    if (await db.check_daily_cooldown(user.id)):
        await db.reset_daily_cooldown(user.id)
        points = random.randint(10,20)
        await db.update_points(user.id, points)
        embed.add_field(name="Reward", value="You recived "+str(points)+" points", inline=False)
        await db.update_quests(user.id, quest_dict["Daily"])
    else:
        embed.add_field(name="Cooldown", value="Wait until twomorrow to claim your daily reward", inline=False)
    view.add_item(back_button(interaction))
    view.add_item(daily_button(interaction))

#Button to be able to buy shares
class buy_shares(discord.ui.Button):
    def __init__(self, interaction:discord.Interaction, amount:int, ticker:str):
        super().__init__(label="Buy "+str(amount), style=discord.ButtonStyle.blurple)
        self.interaction = interaction
        self.amount = amount
        self.ticker = ticker
    async def callback(self, interaction:discord.Interaction):
        user = interaction.user
        view = View()
        embed = discord.Embed(title=user.display_name, color=user.color)
        points = await db.get_points(user.id)
        stock_ticker = yf.Ticker(self.ticker)
        stock_ticker_info = stock_ticker.info
        canAfford = points>=stock_ticker_info["ask"]*self.amount
        if (canAfford):
            await db.update_stock(user.id, stock_ticker_info, "Buy", self.amount)
        await edit_stock_market_view_and_embed(view, embed, self.ticker, user, self.interaction, self.amount)
        if (canAfford):
            embed.add_field(name="Action Result", value="Sucessfully bought "+str(self.amount)+" of "+stock_ticker_info["shortName"], inline=False)
        else:
            embed.add_field(name="Action Result", value="Too poor to afford the stocks", inline=False)
        await self.interaction.edit_original_response(view=view, embed=embed)
        await interaction.response.defer()

#Button to be able to sell shares
class sell_shares(discord.ui.Button):
    def __init__(self, interaction:discord.Interaction, amount:int, ticker:str):
        super().__init__(label="Sell "+str(amount), style=discord.ButtonStyle.blurple)
        self.interaction = interaction
        self.amount = amount
        self.ticker = ticker
    async def callback(self, interaction:discord.Interaction):
        user = interaction.user
        view = View()
        embed = discord.Embed(title=user.display_name, color=user.color)
        stock_ticker = yf.Ticker(self.ticker)
        stock_ticker_info = stock_ticker.info
        stock_ticker_amount = await db.get_amount_of_stock(user.id, self.ticker)
        hasStocks = self.amount<=stock_ticker_amount
        if (hasStocks):
            await db.update_stock(user.id, stock_ticker_info, "Sell", self.amount)
        await edit_stock_market_view_and_embed(view, embed, self.ticker, user, self.interaction, self.amount)
        if (hasStocks):
            embed.add_field(name="Action Result", value="Sucessfully sold "+str(self.amount)+" of "+stock_ticker_info["shortName"], inline=False)
        else:
            embed.add_field(name="Action Result", value="Too few stocks own to sell", inline=False)
        await self.interaction.edit_original_response(view=view, embed=embed)
        await interaction.response.defer()

#Method to edit the view and embed for the stock information    
async def edit_stock_market_view_and_embed(view:discord.ui.View, embed:discord.Embed, ticker:str, user:discord.User, interaction:discord.Interaction, amount:int):
    embed.add_field(name="Stock Market", value="Stock data is displayed below, at the very bottom click buy or sell to buy or sell the stock")
    stock_ticker = yf.Ticker(ticker)
    info = stock_ticker.info
    msg = "Company Website: "+info["website"]+"\n"
    msg += "Industry: "+info["industry"]+"\n"
    msg += "Buy Price: "+str(info["ask"])+"\n"
    msg += "Sell Price: "+str(info["bid"])
    embed.add_field(name=info["shortName"]+" ("+ticker+")", value=msg, inline=False)
    numShares = await db.get_amount_of_stock(user.id, ticker)
    userDataMsg = "Points Balance: "+str(await db.get_points(user.id))+"\n"
    if (not numShares):
        userDataMsg += "Owned Shares: 0\n"
        userDataMsg += "Total Value: 0\n"
    else:
        userDataMsg += "Owned Shares: "+str(numShares)+"\n"
        userDataMsg += "Total Value: "+str(int(numShares)*info["bid"])+"\n"
    embed.add_field(name="User Data", value=userDataMsg)
    view.add_item(back_button(interaction))
    view.add_item(buy_shares(interaction, amount, ticker))
    view.add_item(sell_shares(interaction, amount, ticker))
    view.add_item(refresh_stocks(interaction, "Refresh Stocks"))
    
#Button to be able to refresh the information about a stock
class refresh_stocks(discord.ui.Button):
    def __init__(self, interaction:discord.Interaction, label:str):
        super().__init__(label=label, style=discord.ButtonStyle.blurple)
        self.interaction = interaction
    async def callback(self, interaction:discord.Interaction):   
        user = interaction.user
        view = View()
        embed = discord.Embed(title=user.display_name, color=user.color)
        await  edit_stock_view_and_embed(view, embed,user,self.interaction)  
        await self.interaction.edit_original_response(view=view, embed=embed)
        await interaction.response.defer()

#Get and display the stocks a user has
async def edit_stock_view_and_embed(view:discord.ui.View, embed:discord.Embed, user:discord.User, interaction:discord.Interaction):
    data = await db.get_stocks(user.id)
    msg = ""
    totalStockValue = 0
    for key, value in data.items():
        info = yf.Ticker(key).info
        msg += info["shortName"]+" ("+key+") | Amount: "+str(value)+" | Value: "+str(value*info["bid"])+"\n"
        totalStockValue += value*info["bid"]
    await db.setStockValue(user.id, totalStockValue)
    embed.add_field(name="Owned Stocks", value=msg)
    if (not user.avatar == None):
        embed.set_thumbnail(url=user.avatar.url)
    view.add_item(back_button(interaction))
    view.add_item(refresh_stocks(interaction, "Refresh Stocks"))

#Refresh the current leaderboard for new information button
class refresh_leaderboard(discord.ui.Button):
    def __init__(self, interaction:discord.Interaction, label:str):
        super().__init__(label=label, style=discord.ButtonStyle.blurple)
        self.interaction = interaction
    async def callback(self, interaction:discord.Interaction):   
        user = interaction.user
        view = View()
        embed = discord.Embed(title=user.display_name, color=user.color)
        await edit_leaderboard(view,embed,user,interaction)
        await self.interaction.edit_original_response(view=view, embed=embed)
        await interaction.response.defer()
    
#Edit leaderboard with new information   
async def edit_leaderboard(view:discord.ui.View, embed:discord.Embed, user:discord.User, interaction:discord.Interaction):
    leaderboard = json.loads(await db.get_leader_board())
    userData = await db.get_user_data(user.id)
    lastUpdate = await db.get_last_update()
    if (not user.avatar == None):
        embed.set_thumbnail(url=user.avatar.url)
    embed.add_field(name="Username and Total", value=leaderboard[0]+"\n"+str(userData[0])+"."+userData[1])
    embed.add_field(name="Total", value=leaderboard[1]+"\n"+str(userData[2]))
    embed.add_field(name="Points|Stocks", value=leaderboard[2]+"\n"+str(userData[3])+"|"+str(userData[4]))
    embed.set_footer(text="Last Updated: "+lastUpdate)
    view.add_item(back_button(interaction))
    view.add_item(refresh_leaderboard(interaction,"Refresh Leaderboard"))
    
#Function to edit the view and embed depdent on how the game ends
async def end_blackjack(orgInteraction:discord.Interaction, interaction:discord.Interaction, bet:int, blackjack:blackJack, text:str):
    emded = discord.Embed(color=interaction.user.color, title="Blackjack but worse")
    emded.add_field(name="", value=text, inline=False)
    emded.add_field(name="**Player Hand: "+str(blackjack.getPlayerHandValue())+"**", value=blackjack.stringPlayerHand, inline=False)
    emded.add_field(name="**Dealer Hand: "+str(blackjack.getDealerHandValue())+"**", value=blackjack.stringDealerHand, inline=False)
    view = View()
    view.add_item(back_button(orgInteraction))
    view.add_item(play_blackjack_button(orgInteraction, "Play again bet "+str(bet), bet))
    view.add_item(play_blackjack_button(orgInteraction, "Play again bet 0", 0))
    await db.update_quests(interaction.user.id,quest_dict["Blackjack"])
    await orgInteraction.edit_original_response(view=view,embed=emded)
    
# Menu button to play a game of blackjack 
class play_blackjack_button(discord.ui.Button):
    def __init__(self, interaction:discord.Interaction, label:str, bet=0):
        super().__init__(label=label, style=discord.ButtonStyle.blurple)
        self.interaction = interaction
        self.bet = bet
    async def callback(self,interaction):
        points = await db.get_points(interaction.user.id)
        if (self.bet>points):
            self.bet = 0
        await db.update_points(interaction.user.id,self.bet*-1)
        blackjack = blackJack()
        await edt_blackjack_view_and_embed(self.interaction, blackjack, self.bet)
        await interaction.response.defer()
    
# Button to stay current hand in blackjack
class blackjack_stay_button(discord.ui.Button):
    def __init__(self, interaction:discord.Interaction, blackjack:blackJack, bet:int):    
        super().__init__(label="Stay", style=discord.ButtonStyle.blurple)
        self.bet = bet
        self.blackjack = blackjack
        self.interaction = interaction
    async def callback(self,interaction):
        if (self.interaction.user.id!=interaction.user.id):
            await interaction.response.defer()
            return
        handValues = self.blackjack.stay()
        if (handValues[1]>21):
            await end_blackjack(self.interaction, interaction, self.bet, self.blackjack, "Dealer busted (went over 21). You win "+str(self.bet*1.5)+".")
            await db.update_points(interaction.user.id, self.bet*black_jack_payout)
        elif (handValues[1]<=handValues[0]):
            await end_blackjack(self.interaction, interaction, self.bet, self.blackjack, "Dealer has a smaller hand value. You win "+str(self.bet*1.5)+".")
            await db.update_points(interaction.user.id, self.bet*black_jack_payout)
        else:
            await end_blackjack(self.interaction, interaction, self.bet, self.blackjack, "You have a smaller hand value. You lose "+str(self.bet*1.5)+".")
        await interaction.response.defer()
        
class blackjack_hit_button(discord.ui.Button):
    def __init__(self, interaction:discord.Interaction, blackjack:blackJack, bet:int):
        super().__init__(label="Hit", style=discord.ButtonStyle.blurple)
        self.bet = bet
        self.blackjack = blackjack
        self.interaction = interaction
    async def callback(self,interaction):
        if (self.interaction.user.id!=interaction.user.id):
            await interaction.response.defer()
            return
        playerHandValue = self.blackjack.hit()
        if (playerHandValue>21):
            await end_blackjack(self.interaction, interaction, self.bet, self.blackjack, "You busted (went over 21). You lose "+str(self.bet)+".")
        else:
            await edt_blackjack_view_and_embed(self.interaction, self.blackjack, self.bet)
        await interaction.response.defer()
        
# Edit the view and embed to display blackjack
async def edt_blackjack_view_and_embed(interaction:discord.Interaction, blackjack:blackJack, bet:int):
    emded = discord.Embed(color=interaction.user.color, title="Blackjack but worse")
    emded.add_field(name="**Player Hand:"+str(blackjack.getPlayerHandValue())+"**", value=blackjack.stringPlayerHand, inline=False)
    emded.add_field(name="**Dealer Hand:"+str(blackjack.getDealerHandValue())+"**", value=blackjack.stringDealerHand, inline=False)
    view = View()
    view.add_item(back_button(interaction))
    view.add_item(blackjack_stay_button(interaction, blackjack, bet))
    view.add_item(blackjack_hit_button(interaction, blackjack, bet))
    await interaction.edit_original_response(view=view,embed=emded)
    
# Coin flip menu button
class play_coin_flip_button(discord.ui.Button):
    def __init__(self, intearction, label:str):
        super().__init__(label=label, style=discord.ButtonStyle.blurple)
        self.intearction = intearction
    async def callback(self,intearction):
        print("?")
        await edit_coinflip_view_and_embed(self.intearction,0,"")   
        intearction.response.defer()

#Coin flip button to play acutal game (expects Heads or Tails as label input)
class flip_coin_button(discord.ui.Button):
    def __init__(self, intearction, bet: int, label:str):
        super().__init__(label=label, style=discord.ButtonStyle.blurple)
        self.intearction = intearction
        self.bet = bet
        self.label = label
    async def callback(self,interaction):
        result= await db.coinFlip(interaction.user.id, self.bet, self.label)
        if (result):
            await edit_coinflip_view_and_embed(self.intearction, self.bet, "You chose "+self.label+" and won "+str(self.bet))
        else:
            await edit_coinflip_view_and_embed(self.intearction, self.bet, "You chose "+self.label+" and lost "+str(self.bet))
        await interaction.response.defer()
    
# Edit the view and embed of conflip to 
async def edit_coinflip_view_and_embed(interaction:discord.Interaction, bet:int, text:str):
    emded = discord.Embed(color=interaction.user.color, title="Flip coin for "+str(bet))
    emded.add_field(name="", value=text, inline=False)
    view = View()
    view.add_item(back_button(interaction))
    view.add_item(flip_coin_button(interaction,bet,"Heads"))
    view.add_item(flip_coin_button(interaction,bet,"Tails"))
    await interaction.edit_original_response(view=view,embed=emded)
