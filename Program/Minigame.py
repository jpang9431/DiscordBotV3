import random
import itertools

#Turns the value of the card to the name of the card
def interpret_card(card):
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
def calc_hand_value(hand):
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
        self.card_pointer = 0
        self.dealer_hand = []
        self.player_hand = []
        self.string_dealer_hand = ""
        self.string_player_hand = ""
        for i in range(2):
            self.dealer_hand.append(self.deck[self.card_pointer])
            self.card_pointer+=1
            self.string_dealer_hand+=interpret_card(self.dealer_hand[i])
            self.player_hand.append(self.deck[self.card_pointer])
            self.string_player_hand+=interpret_card(self.player_hand[i])
            self.card_pointer+=1
    def hit(self):
        self.player_hand.append(self.deck[self.card_pointer])
        self.string_player_hand+=interpret_card(self.player_hand[len(self.player_hand)-1])
        self.card_pointer+=1
        return calc_hand_value(self.player_hand)
    def stay(self):
        dealer_handValue = calc_hand_value(self.dealer_hand)
        player_handValue = calc_hand_value(self.player_hand)
        while(dealer_handValue<=player_handValue and dealer_handValue<21):
            self.dealer_hand.append(self.deck[self.card_pointer])
            self.string_dealer_hand+=interpret_card(self.dealer_hand[len(self.dealer_hand)-1])
            self.card_pointer+=1
            dealer_handValue = calc_hand_value(self.dealer_hand)
        return [player_handValue, dealer_handValue]
    def get_player_hand_value(self):
        return calc_hand_value(self.player_hand)
    def get_dealer_hand_value(self):
        return calc_hand_value(self.dealer_hand)
    
    
def flip_coin(value:int, bet=0):
    head_tail = random.randint(0,1)
    if (value==head_tail):
        return bet*2
    else:
        return 0