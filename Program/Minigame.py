import random
import itertools

#Turns the value of the card to the name of the card
def interpretCard(card):
    msg = " of "+card[1]
    faceCard = ["J","Q","K"]
    if (card[0]>10):
        msg = str(faceCard[card[0]-11]) + msg
    elif(card[0]==1):
        msg = "A"+msg
    else:
        msg = str(card[0]) + msg
    return msg + "\n"

#calcaluates the hand value
def calcHandValue(hand):
    value = 0
    numAces = 0
    for card in hand:
        if card[0] == 1:
            numAces+=1
        elif card[0] > 10:
            value+=10
        else:
            value+=card[0]
    if numAces==1 and value<=10:
        value+=11
    else:
        value+=numAces
    return value

#Blackjack class to play a game of blackjack
class blackJack():
    def __init__(self):
        self.deck = list(itertools.product(range(1,14),['Spade','Heart','Diamond','Club']))
        random.shuffle(self.deck)
        self.cardPointer = 0
        self.dealerHand = []
        self.playerHand = []
        self.stringDealerHand = ""
        self.stringPlayerHand = ""
        for i in range(2):
            self.dealerHand.append(self.deck[self.cardPointer])
            self.cardPointer+=1
            self.stringDealerHand+=interpretCard(self.dealerHand[i])
            self.playerHand.append(self.deck[self.cardPointer])
            self.stringPlayerHand+=interpretCard(self.playerHand[i])
            self.cardPointer+=1
    def hit(self):
        self.playerHand.append(self.deck[self.cardPointer])
        self.stringPlayerHand+=interpretCard(self.playerHand[len(self.playerHand)-1])
        self.cardPointer+=1
        return calcHandValue(self.playerHand)
    def stay(self):
        dealerHandValue = calcHandValue(self.dealerHand)
        playerHandValue = calcHandValue(self.playerHand)
        while(dealerHandValue<=playerHandValue and dealerHandValue<21):
            self.dealerHand.append(self.deck[self.cardPointer])
            self.stringDealerHand+=interpretCard(self.dealerHand[len(self.dealerHand)-1])
            self.cardPointer+=1
            dealerHandValue = calcHandValue(self.dealerHand)
        return [playerHandValue, dealerHandValue]
    def getPlayerHandValue(self):
        return calcHandValue(self.playerHand)
    def getDealerHandValue(self):
        return calcHandValue(self.dealerHand)