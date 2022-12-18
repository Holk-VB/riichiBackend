from django.db import models
from django.contrib.auth.models import User
from tiles.models import TileStack, Tile, Meld
from tiles.utils import *
from games.utils import *
import numpy as np
from uuid import uuid4
from django.db.models import QuerySet
import random


class Player(models.Model):
    """
    Stores a single Player related to a registered User and a Game
    """
    user = models.ForeignKey(User, on_delete=models.PROTECT)  # FK to User
    game = models.ForeignKey('Game', on_delete=models.PROTECT)  # FK to Game
    username = models.CharField(max_length=255)  # in game username that could be used a customizable nickname
    score = models.IntegerField(default=DEFAULT_SCORE)
    wind = models.CharField(max_length=255, choices=WIND_NAMES)  # east, south, west or north
    is_dealer = models.BooleanField(default=False)
    can_play = models.BooleanField(default=False)  # indicates if the player can send moves to play or not
    possible_calls = models.JSONField(default=list)  # contains all the calls the player can send at any point
    call_sent = models.JSONField(default=dict)  # contains the possible_call the player sent
    in_tenpai = models.BooleanField(default=False)  # indicates whether a player is in tenpai

    @property
    def current_player_hand(self) -> 'PlayerHand':
        return self.playerhand_set.get(game_hand=self.game.current_round.current_hand)

    @property
    def current_player_discard(self) -> 'PlayerDiscard':
        return self.playerdiscard_set.get(game_hand=self.game.current_round.current_hand)

    @property
    def current_player_melds(self) -> QuerySet['PlayerMeld']:
        return self.playermeld_set.filter(game_hand=self.game.current_round.current_hand)

    def start_playing(self) -> None:
        self.can_play = True
        self.save()

    def stop_playing(self) -> None:
        self.can_play = False
        self.save()

    def clear_calls(self) -> None:
        self.possible_calls = list()
        self.call_sent = dict()
        self.save()

    def send_call(self, call: dict) -> None:
        self.call_sent = call
        self.save()

    def calculate_available_calls_in_turn_phase(self) -> None:
        """
        Calculates all the possible calls a player can make on its turn and stores it in its possible_calls attribute

        :return: None
        """

        hand = self.game.current_round.current_hand
        player_hand = self.playerhand_set.get(game_hand=hand).tile_stack
        available_calls = []

        # a player can only do 3 calls on its turn : closed kan, riichi and tsumo

        # for a closed kan what is needed is 4 tiles of any kind
        for suit, name in VALID_TILES:
            if player_hand.contain(suit, name, 4):
                call = {
                    "type": "closed kan",
                    "suit": suit,
                    "name": name + "-" + name + "-" + name + "-" + name
                }
                available_calls.append(call)

        # add tsumo TODO
        # add riichi TODO

        self.possible_calls = available_calls
        self.save()

    def calculate_available_calls_in_call_phase(self) -> None:
        """
        Calculates all the possible calls a player can make on the call phase
        and stores it in its possible_calls attribute

        :return: None
        """

        hand = self.game.current_round.current_hand
        player_hand = self.playerhand_set.get(game_hand=hand).tile_stack
        available_calls = []

        # a player can do 5 calls on its turn : opened and late kan, pon, chi and ron

        # the last player who played cannot make a call
        last_player = Player.objects.get(game=self.game, wind=get_previous_wind(hand.next_wind_to_play))
        if self == last_player:
            self.possible_calls = available_calls
            self.save()
            return

        # let's start be getting the last discarded tile
        suit = hand.last_discarded_tile.get("suit")
        name = str(hand.last_discarded_tile.get("name"))

        # add ron TODO

        # for an opened kan the player hand must contain 3 tiles same as the last discarded tile
        if player_hand.contain(suit, name, 3):
            call = {
                "type": "opened kan",
                "suit": suit,
                "name": name + "-" + name + "-" + name + "-" + name
            }
            available_calls.append(call)

        # for a late kan the player must have a pon meld with same tile as the last discarded tile
        player_meld_set = self.playermeld_set.filter(game_hand=hand).all()
        if player_meld_set.exists():
            for player_meld in player_meld_set:
                meld = player_meld.tile_stack.meld
                if meld.type == 'pon' and meld.suit == suit and meld.name == name+"-"+name+"-"+name:
                    call = {
                        "type": "late kan",
                        "suit": suit,
                        "name": name + "-" + name + "-" + name + "-" + name
                    }
                    available_calls.append(call)

        # for a pon the player hand must contain 2 tiles same as the last discarded tile
        if player_hand.contain(suit, name, 2):
            call = {
                "type": "pon",
                "suit": suit,
                "name": name + "-" + name + "-" + name
            }
            available_calls.append(call)

        # for a chi the player hand must contain 2 tiles forming a sequence with the last discarded tile,
        # and it only works with number suits
        if self.wind == hand.next_wind_to_play and suit in [SUIT[0] for SUIT in NUMBER_SUITS]:

            next_name = get_next_number(name)
            next_next_name = get_next_number(next_name)
            previous_name = get_next_number(name)
            previous_previous_name = get_next_number(previous_name)

            if int(name) in [3, 4, 5, 6, 7, 8, 9]:  # either the two previous tiles
                if player_hand.contain(suit, previous_previous_name) and player_hand.contain(suit, previous_name):
                    call = {
                        "type": "chi",
                        "suit": suit,
                        "name": previous_previous_name + "-" + previous_name + "-" + name
                    }
                    available_calls.append(call)

            if int(name) in [2, 3, 4, 5, 6, 7, 8]:  # either the previous tile and the next tile
                if player_hand.contain(suit, previous_name) and player_hand.contain(suit, next_name):
                    call = {
                        "type": "chi",
                        "suit": suit,
                        "name": previous_name + "-" + name + "-" + next_name
                    }
                    available_calls.append(call)

            if int(name) in [1, 2, 3, 4, 5, 6, 7]:   # either the two next tiles
                if player_hand.contain(suit, next_name) and player_hand.contain(suit, next_next_name):
                    call = {
                        "type": "chi",
                        "suit": suit,
                        "name": name + "-" + next_name + "-" + next_next_name
                    }
                    available_calls.append(call)

        self.possible_calls = available_calls
        self.save()


class Game(models.Model):
    """
    Stores a single Game related to players
    """
    users = models.ManyToManyField(User, through=Player)  # sets the N-N relation with User through the Player model
    seed = models.CharField(default='0', max_length=255)  # seed of all the random events of the game
    is_full = models.BooleanField(default=False)
    is_over = models.BooleanField(default=False)
    random_state = models.JSONField(default=dict)  # current python random state of the game

    @staticmethod
    def create(user: User,
               username: str) -> 'Game':

        game = Game()
        game.save()
        game.generate_seed()
        game.add_player(user, username)

        return game

    @property
    def current_round(self) -> 'Round':
        return self.round_set.latest('id')

    def add_player(self, user: User, username: str) -> None:
        self.users.add(user, through_defaults={'username': username})
        self.save()

    def assign_players_wind(self) -> None:
        players_winds = [wind for wind, name in WIND_NAMES]

        random.setstate(self.get_random_state())
        random.shuffle(players_winds)
        self.random_state = random.getstate()
        self.save()

        for player in self.player_set.all():
            player.wind = players_winds.pop()
            if player.wind == 'east':
                player.is_dealer = True
            player.save()

    def generate_seed(self) -> None:
        self.seed = str(int(uuid4()))  # large integer is easier to store as a str
        random.seed(int(self.seed))
        self.random_state = random.getstate()
        self.save()

    def get_random_state(self) -> tuple:
        random_state_list = self.random_state
        random_state = (random_state_list[0], tuple(random_state_list[1]), random_state_list[2])
        return random_state

    def fill_up(self) -> None:
        self.is_full = True
        self.save()

    def start(self) -> None:
        self.assign_players_wind()
        first_round = Round.create(self, 0, WIND_NAMES[0][0])
        first_hand = Hand.create(first_round, 0)
        first_hand.set_up()

        first_player = self.player_set.get(is_dealer=True)
        first_hand.player_pick(first_player)
        first_player.start_playing()

    def next_round(self) -> None:
        # add after having add ron, tsumo and yakus TODO
        pass


class Round(models.Model):
    """
    Stores a single Round related to a Game
    """
    game = models.ForeignKey(Game, on_delete=models.PROTECT)  # FK to Game
    position_in_game = models.IntegerField()  # 1 or 2 in a classic game
    prevailing_wind = models.CharField(max_length=255, choices=WIND_NAMES)  # dominant wind of the round

    @staticmethod
    def create(game: Game,
               position_in_game: int,
               prevailing_wind: str) -> 'Round':

        round = Round(game=game, position_in_game=position_in_game, prevailing_wind=prevailing_wind)
        round.save()

        return round

    @property
    def current_hand(self) -> 'Hand':
        return self.hand_set.latest('id')

    def next_hand(self) -> None:
        pass


class Hand(models.Model):
    """
    Stores a single Hand related to a Round
    """
    round = models.ForeignKey(Round, on_delete=models.PROTECT)  # FK to Round
    position_in_round = models.IntegerField()  # 1, 2, 3 or 4 if the dealer does not win a hand
    kan_counter = models.IntegerField(default=0)  # indicates the number of doras to reveal to players
    in_call_phase = models.BooleanField(default=False)  # indicates if it is time for players to send calls
    last_discarded_tile = models.JSONField(default=dict)  # indicates the last discarded tile
    next_wind_to_play = models.CharField(default=get_next_wind('east'), choices=WIND_NAMES, max_length=255)

    @staticmethod
    def create(round: Round,
               position_in_round: int) -> 'Hand':

        hand = Hand(round=round, position_in_round=position_in_round)
        hand.save()

        return hand

    @property
    def doras(self):
        dora_indicators_holder = self.tilestackholder_set.get(name='dora_indicators')
        dora_indicators = dora_indicators_holder.tile_stack.tile_set.order_by('position_in_tile_stack')
        doras = []
        for i in range(1+self.kan_counter):
            suit = dora_indicators[i].suit
            name = dora_indicators[i].name
            doras.append({"suit": suit, "name": get_next_tile_name(suit, name)})
        return doras

    def set_up(self) -> None:
        """
        Sets up a game hand creating all necessary elements

        :return: None
        """

        # first creates a tile set for the game hand
        hand_tile_set = TileStackHolder.create_tile_stack('hand_tile_set', self)

        for i in range(TILES_PER_GAME):
            suit, name = VALID_TILES[i % UNIQUE_TILES]
            Tile.create(suit, name, hand_tile_set, i)

        hand_tile_set.length += TILES_PER_GAME
        hand_tile_set.save()

        hand_tile_set.shuffle()  # shuffle game's set
        players = self.round.game.player_set.all()  # get all players in a QuerySet

        for i, player in enumerate(players):  # create and fill players hand and discard
            PlayerDiscard.create_player_discard('discard '+str(i), self, player)
            player_hand = PlayerHand.create_player_hand('hand '+str(i), self, player)
            player_hand.pick_in(hand_tile_set, 13)
            player_hand.order_by_default()
            self.is_player_hand_in_tenpai(player)

        dora_indicators = TileStackHolder.create_tile_stack('dora_indicators', self)
        dora_indicators.pick_in(hand_tile_set, 5)
        dead_wall = TileStackHolder.create_tile_stack('dead_wall', self)
        dead_wall.pick_in(hand_tile_set, 9)
        wall = TileStackHolder.create_tile_stack('wall', self)
        wall.pick_in(hand_tile_set, 70)

    def player_pick(self, player) -> None:
        """
        Makes the player pick a tile in the wall

        :param player: player that should pick a tile
        :return: None
        """
        player_hand = player.playerhand_set.get(game_hand=self).tile_stack
        wall = self.tilestackholder_set.get(name='wall').tile_stack
        player_hand.pick_in(wall, 1)

    def player_discard(self, player: Player, tile: Tile) -> None:
        """
        Makes the player discard a tile in his discard

        :param player: player that should discard a tile
        :param tile: tile to be discarded
        :return: None
        """

        player_discard = player.playerdiscard_set.get(game_hand=self).tile_stack
        player_hand = player.playerhand_set.get(game_hand=self).tile_stack
        player_hand.transfer_to(player_discard, tile)
        self.last_discarded_tile = {"id": tile.id, "suit": tile.suit, "name": tile.name}
        self.save()
        player.stop_playing()
        self.is_player_hand_in_tenpai(player)

    def player_call(self, player) -> None:
        """
        Execute the call sent by a player

        :param player: player whose call was sent
        :return: None
        """

        call = player.call_sent
        player_hand = player.playerhand_set.get(game_hand=self).tile_stack
        discarded_tile = Tile.objects.get(id=self.last_discarded_tile.get("id"))
        player_discard = discarded_tile.tile_stack
        # add forbidden_discards after some calls TODO

        # if the call is an opened kan then the discarded tile and the 3 corresponding tiles in the player hand
        # get transfered to a new created meld related to the player
        if call.get("type") == 'opened kan':
            meld = PlayerMeld.create_meld(call.get("name"), call.get("type"), call.get("suit"), self, player)
            tile_names = call.get("name").split('-')
            player_discard.transfer_to(meld, discarded_tile)
            tile_names.pop()
            for name in tile_names:
                player_hand.transfer_to(meld, player_hand.tile_set.filter(name=name, suit=call.get("suit")).first())
            self.next_wind_to_play = player.wind
            self.kan_counter += 1
            self.save()

        # if the call is a late kan then the corresponding meld in the player meld set get upgraded a late kan
        # and the last discarded tile goes in it
        elif call.get("type") == 'late kan':
            pon_call_name = call.get("name")[0] + "-" + call.get("name")[0] + "-" + call.get("name")[0]
            meld = player.playermeld_set.get(game_hand=self, name=pon_call_name, type='pon', suit=call.get("suit"))
            player_discard.transfer_to(meld, discarded_tile)
            meld.type = call.get("type")
            meld.name = call.get("name")
            meld.save()
            self.next_wind_to_play = player.wind
            self.kan_counter += 1
            self.save()

        # if the call is an pon then the discarded tile and the 2 corresponding tiles in the player hand
        # get transfered to a new created meld related to the player
        elif call.get("type") == 'pon':
            meld = PlayerMeld.create_meld(call.get("name"), call.get("type"), call.get("suit"), self, player)
            tile_names = call.get("name").split('-')
            player_discard.transfer_to(meld, discarded_tile)
            tile_names.pop()
            for name in tile_names:
                player_hand.transfer_to(meld, player_hand.tile_set.filter(name=name, suit=call.get("suit")).first())
            self.next_wind_to_play = player.wind
            self.save()

        # if the call is an chi then the discarded tile and the 2 corresponding tiles in the player hand
        # get transfered to a new created meld related to the player
        elif call.get("type") == 'chi':
            meld = PlayerMeld.create_meld(call.get("name"), call.get("type"), call.get("suit"), self, player)
            tile_names = call.get("name").split('-')
            player_discard.transfer_to(meld, discarded_tile)
            tile_names.remove(discarded_tile.name)
            for name in tile_names:
                player_hand.transfer_to(meld, player_hand.tile_set.filter(name=name, suit=call.get("suit")).first())
            self.next_wind_to_play = player.wind
            self.save()

        # add ron TODO
        elif call.get("type") == 'ron':
            pass

        # if the call is an closed kan then the 4 concerned tiles in the player hand
        # get transfered to a new created meld related to the player
        elif call.get("type") == 'closed kan':
            meld = PlayerMeld.create_meld(call.get("name"), call.get("type"), call.get("suit"), self, player, False)
            tile_names = call.get("name").split('-')
            for name in tile_names:
                player_hand.transfer_to(meld, player_hand.tile_set.filter(name=name, suit=call.get("suit")).first())
            self.next_wind_to_play = player.wind
            self.kan_counter += 1
            self.save()

        # add riichi TODO
        elif call.get("type") == 'riichi':
            pass

        # add tsumo TODO
        elif call.get("type") == 'tsumo':
            pass

        else:
            pass

    def start_call_phase(self) -> None:
        players = self.round.game.player_set.all()

        for player in players:
            player.calculate_available_calls_in_call_phase()

        self.in_call_phase = True
        self.save()

    def end_call_phase(self) -> None:
        """
        Ends the call phase and chooses which player call is the priority

        :return: None
        """

        self.in_call_phase = False
        self.save()

        can_pick = True  # turn False if pon or chi is called

        players = self.round.game.player_set.all()
        calls = list(players.values_list('call_sent', flat=True))
        call_types = [call.get("type") for call in calls]

        if 'ron' in call_types:  # ron is the priority call
            player = players.get(call_sent__type='ron')
            self.player_call(player)

        elif 'opened kan' in call_types:  # then there is kan
            player = players.get(call_sent__type='opened kan')
            self.player_call(player)

        elif 'late kan' in call_types:
            player = players.get(call_sent__type='late kan')
            self.player_call(player)

        elif 'pon' in call_types:  # then there is pon
            player = players.get(call_sent__type='pon')
            self.player_call(player)

        elif 'chi' in call_types:  # then there is chi
            player = players.get(call_sent__type='chi')
            self.player_call(player)

        for player in players:  # clear player calls
            player.clear_calls()

        self.next_turn(can_pick)

    def next_turn(self, can_pick: bool):
        player = self.round.game.player_set.get(wind=self.next_wind_to_play)
        if can_pick:
            self.player_pick(player)
        self.next_wind_to_play = get_next_wind(player.wind)
        self.save()
        player.calculate_available_calls_in_turn_phase()
        player.playerhand_set.get(game_hand=self).tile_stack.order_by_default()
        player.start_playing()

    def is_player_hand_in_tenpai(self, player: Player) -> None:
        """
        Checks if the player hand is in tenpai and sets player.in_tenpai in accordance

        :param player: instance of Player on which the check is performed
        :return: None
        """

        # adapt method to return the tiles to complete the tenpai TODO

        #  ------------  functions needed to check tenpai  ------------

        def check_for_13_orphans(player_hand: np.ndarray) -> bool:
            """
            Checks if the player hand is in 13 orphans tenpai

            :param player_hand: instance of Player on which the check is performed
            :return: True if the player hand is in 13 orphans tenpai, False otherwise
            """

            missing_orphan = 0
            orphan_pair = 0

            # a complete 13 orphans hand needs a 1 and a 9 of each number suit
            for suit in ('bamboo', 'character', 'dot'):

                if player_hand[suit][0] == 0:
                    missing_orphan += 1
                elif player_hand[suit][0] == 2:
                    orphan_pair += 1
                elif player_hand[suit][0] != 1:  # anything more than 2 of a same tile cannot be 13 orphan tenpai
                    return False

                if player_hand[suit][8] == 0:
                    missing_orphan += 1
                elif player_hand[suit][8] == 2:
                    orphan_pair += 1
                elif player_hand[suit][8] != 1:  # anything more than 2 of a same tile cannot be 13 orphan tenpai
                    return False

            # a complete 13 orphans hand needs one of each honor tiles
            for i in range(7):
                if player_hand['honor'][i] == 0:
                    missing_orphan += 1
                elif player_hand['honor'][i] == 2:
                    orphan_pair += 1
                elif player_hand['honor'][i] != 1:  # anything more than 2 of a same tile cannot be 13 orphan tenpai
                    return False

            if missing_orphan == 0:  # 13 orphans tenpai is achieved with no missing orphans
                return True
            elif missing_orphan == 1 and orphan_pair == 1:  # or with one missing orphan and a spare orphan
                return True
            else:  # anything else is not 13 orphans tenpai
                return False

        def check_for_7_pairs(player_hand: np.ndarray) -> bool:
            """
            Checks if the player hand is in 7 pairs tenpai

            :param player_hand: instance of Player on which the check is performed
            :return: True if the player hand is in 7 pairs tenpai, False otherwise
            """

            pair = 0
            single = 0

            for suit in ('bamboo', 'character', 'dot', 'honor'):
                for i in range(player_hand[suit].size):
                    if player_hand[suit][i] == 2:
                        pair += 1
                    elif player_hand[suit][i] == 1:
                        single += 1
                    elif player_hand[suit][i] != 0:  # anything more than 2 of a same tile cannot be 7 pairs tenpai
                        return False

            if pair == 6 and single == 1:  # 7 pairs tenpai is achieved with 6 pairs and a single tile
                return True
            else:  # anything else is not 7 pairs tenpai
                return False

        def get_possible_melds(suit_vector: np.ndarray) -> list[np.ndarray]:
            """
            Gets all melds that could be formed in the suit_vector

            :param suit_vector: numpy array containing an integer representing all tiles of a suit,
                   example : [0 3 1 1 1 0 0 0 0] means the suit contains 3 tile 2, 1 tile 3, 4 and 5
            :return: list of numpy array representing all melds that can be formed in suit_vector
                     example : [0 3 1 1 1 0 0 0 0] -> [[0 3 0 0 0 0 0 0 0], [0 1 1 1 0 0 0 0 0], [0 0 1 1 1 0 0 0 0]]
            """

            possible_melds = []
            vector_size = suit_vector.size  # number suits and honor suit have different size and properties

            for i in range(vector_size):
                if suit_vector[i] >= 3:
                    new_possible_meld = np.zeros(vector_size, dtype=int)
                    new_possible_meld[i] = 3
                    possible_melds.append(new_possible_meld)

            if vector_size == 9:  # meaning it is not the honor vector
                for i in range(7):
                    if suit_vector[i] >= 1 and suit_vector[i + 1] >= 1 and suit_vector[i + 2] >= 1:
                        new_possible_meld = np.zeros(vector_size, dtype=int)
                        new_possible_meld[i] = 1
                        new_possible_meld[i + 1] = 1
                        new_possible_meld[i + 2] = 1
                        possible_melds.append(new_possible_meld)

            return possible_melds

        def get_meld_combinations(suit_vector: np.ndarray) -> list[dict]:
            """
            Tries all meld combinations that could be formed in the suit_vector and calculate all possible ones

            :param suit_vector: numpy array containing an integer representing all tiles of a suit,
                   example : [0 3 1 1 1 0 0 0 0] means the suit contains 3 tile 2, 1 tile 3, 4 and 5
            :return: list of numpy array representing all melds combinations that can be formed in suit_vector
                     example : [0 3 1 1 1 0 0 0 0] -> [{'meld_combination': [[0 3 0 0 0 0 0 0 0], [0 0 1 1 1 0 0 0 0]],
                      'leftover': [0 0 0 0 0 0 0 0 0]}, {'meld_combination': [[0 0 1 1 1 0 0 0 0], [0 3 0 0 0 0 0 0 0]],
                      'leftover': [0 0 0 0 0 0 0 0 0]}, {'meld_combination': [[0 1 1 1 0 0 0 0 0]],
                      'leftover': [0 2 0 0 1 0 0 0 0]}]
            """

            combinations = []

            possible_1_melds = get_possible_melds(suit_vector)  # gets a list of all possible melds in original vector
            if not possible_1_melds:  # if the list is empty
                combinations.append({'meld_combination': [], 'leftover': suit_vector})  # then everything is leftover

            else:
                for possible_1_meld in possible_1_melds:  # tries all meld possibilities
                    vector_1 = suit_vector.copy()  # makes a new vector for each possibility
                    vector_1 -= possible_1_meld  # removes the meld from the new vector

                    possible_2_melds = get_possible_melds(vector_1)  # gets a list of all possible melds in new vector
                    if not possible_2_melds:  # if the list is empty then this is the end of this combination
                        combinations.append({'meld_combination': [possible_1_meld], 'leftover': vector_1})

                    else:  # if the vector still contains melds then continue the same process
                        for possible_2_meld in possible_2_melds:
                            vector_2 = vector_1.copy()
                            vector_2 -= possible_2_meld

                            possible_3_melds = get_possible_melds(vector_2)
                            if not possible_3_melds:
                                combinations.append(
                                    {'meld_combination': [possible_1_meld, possible_2_meld], 'leftover': vector_2})

                            else:  # if the vector still contains melds then continue the process
                                for possible_3_meld in possible_3_melds:
                                    vector_3 = vector_2.copy()
                                    vector_3 -= possible_3_meld

                                    possible_4_melds = get_possible_melds(vector_3)
                                    if not possible_4_melds:
                                        combinations.append(
                                            {'meld_combination': [possible_1_meld, possible_2_meld, possible_3_meld],
                                             'leftover': vector_3})

                                    else:  # ... one last time since there cannot be more than 4 melds
                                        for possible_4_meld in possible_4_melds:
                                            vector_4 = vector_3.copy()
                                            vector_4 -= possible_4_meld

                                            combinations.append({'meld_combination': [possible_1_meld, possible_2_meld,
                                                                                      possible_3_meld, possible_4_meld],
                                                                 'leftover': vector_4})

            return combinations

        def delete_duplicate_leftovers(combinations: list[dict]) -> list[dict]:
            """
            Since combinations ordered by leftover contain duplicate (meld1 -> meld2 is the same as meld2 -> meld1),
            this function filters out duplicate combinations

            :param combinations: list of numpy array representing all melds combinations that can be formed
                     example : [{'meld_combination': [[0 3 0 0 0 0 0 0 0], [0 0 1 1 1 0 0 0 0]],
                      'leftover': [0 0 0 0 0 0 0 0 0]}, {'meld_combination': [[0 0 1 1 1 0 0 0 0], [0 3 0 0 0 0 0 0 0]],
                      'leftover': [0 0 0 0 0 0 0 0 0]}, {'meld_combination': [[0 1 1 1 0 0 0 0 0]],
                      'leftover': [0 2 0 0 1 0 0 0 0]}]
            :return: list of numpy array representing all melds unique combinations filtered by leftover
                     example : [{'meld_combination': [[0 3 0 0 0 0 0 0 0], [0 0 1 1 1 0 0 0 0]],
                      'leftover': [0 0 0 0 0 0 0 0 0]}, {'meld_combination': [[0 1 1 1 0 0 0 0 0]],
                      'leftover': [0 2 0 0 1 0 0 0 0]}]
            """

            leftovers = []
            leftovers_index = []

            for index, combination in enumerate(combinations):
                leftover = combination.get('leftover')
                leftover_is_duplicate = False
                for already_leftover in leftovers:
                    if np.array_equiv(leftover, already_leftover):
                        leftover_is_duplicate = True
                if not leftover_is_duplicate:
                    leftovers.append(leftover)
                    leftovers_index.append(index)

            combinations_without_duplicate = []
            for index in leftovers_index:
                combinations_without_duplicate.append(combinations[index])

            return combinations_without_duplicate

        def get_smallest_leftovers(combinations: list[dict]) -> list[dict]:
            """
            Gets the combinations with the smallest leftovers

            :param combinations: list of numpy array representing melds with big and small leftovers
                     example : [0 3 1 1 1 0 0 0 0] -> [{'meld_combination': [[0 3 0 0 0 0 0 0 0], [0 0 1 1 1 0 0 0 0]],
                      'leftover': [0 0 0 0 0 0 0 0 0]}, {'meld_combination': [[0 1 1 1 0 0 0 0 0]],
                      'leftover': [0 2 0 0 1 0 0 0 0]}]
            :return: list of numpy array representing all melds with the smallest leftovers
                     example : [0 3 1 1 1 0 0 0 0] -> [{'meld_combination': [[0 3 0 0 0 0 0 0 0], [0 0 1 1 1 0 0 0 0]],
                      'leftover': [0 0 0 0 0 0 0 0 0]}]
            """

            smallest_leftovers_size = 14
            smallest_leftovers_index = []

            for index, combination in enumerate(combinations):
                leftovers_size = sum(combination.get('leftover'))
                if leftovers_size == smallest_leftovers_size:
                    smallest_leftovers_index.append(index)
                elif leftovers_size < smallest_leftovers_size:
                    smallest_leftovers_size = leftovers_size
                    smallest_leftovers_index = [index]

            combinations_with_smallest_leftovers = []
            for index in smallest_leftovers_index:
                combinations_with_smallest_leftovers.append(combinations[index])

            return combinations_with_smallest_leftovers

        def get_possible_meld_parts(suit_vector: np.ndarray) -> list[np.ndarray]:
            """
            Gets all meld_parts that could be formed in the suit_vector

            :param suit_vector: numpy array containing an integer representing all tiles of a suit,
                   example : [0 2 0 1 1 0 0 0 0] means the suit contains 2 tile 2, 1 tile 4 and 5
            :return: list of numpy array representing all melds that can be formed in suit_vector
                     example : [0 2 0 1 1 0 0 0 0] -> [[0 2 0 0 0 0 0 0 0], [0 1 0 1 0 0 0 0 0], [0 0 0 1 1 0 0 0 0]]
            """

            possible_meld_parts = []
            vector_size = suit_vector.size

            for i in range(vector_size):  # number suits and honor suit have different size and properties
                if suit_vector[i] >= 2:
                    new_possible_meld_part = np.zeros(vector_size, dtype=int)
                    new_possible_meld_part[i] = 2
                    possible_meld_parts.append(new_possible_meld_part)

            if vector_size == 9:  # meaning it is not the honor vector
                for i in range(7):
                    if suit_vector[i] >= 1 and suit_vector[i + 1] >= 1:
                        new_possible_meld_part = np.zeros(vector_size, dtype=int)
                        new_possible_meld_part[i] = 1
                        new_possible_meld_part[i + 1] = 1
                        possible_meld_parts.append(new_possible_meld_part)
                    if suit_vector[i] >= 1 and suit_vector[i + 2] >= 1:
                        new_possible_meld_part = np.zeros(vector_size, dtype=int)
                        new_possible_meld_part[i] = 1
                        new_possible_meld_part[i + 2] = 1
                        possible_meld_parts.append(new_possible_meld_part)

            return possible_meld_parts

        def get_meld_part_combinations(suit_vector: np.ndarray) -> list[dict]:
            """
            Tries all meld part combinations that could be formed in the suit_vector and calculate all possible ones

            :param suit_vector: numpy array containing an integer representing all tiles of a suit,
                   example : [0 2 0 1 1 0 0 0 0] means the suit contains 2 tile 2, 1 tile 4 and 5
            :return: list of numpy array representing all meld parts combinations that can be formed in suit_vector
                     example : [0 2 0 1 1 0 0 0 0] -> [{'meld_part_combination': [[0 2 0 0 0 0 0 0 0],
                     [0 0 0 1 1 0 0 0 0]], 'leftover': [0 0 0 0 0 0 0 0 0]}, {'meld_part_combination':
                     [[0 0 0 1 1 0 0 0 0], [0 2 0 0 0 0 0 0 0]], 'leftover': [0 0 0 0 0 0 0 0 0]},
                     {'meld_part_combination': [[0 1 0 1 0 0 0 0 0]], 'leftover': [0 1 0 0 1 0 0 0 0]}]
            """

            combinations = []

            # gets a list of all possible meld parts in original vector
            possible_1_meld_parts = get_possible_meld_parts(suit_vector)
            # if the list is empty
            if not possible_1_meld_parts:
                # then everything is leftover
                combinations.append({'meld_part_combination': [], 'leftover': suit_vector})

            else:
                for possible_1_meld_part in possible_1_meld_parts:  # tries all meld part possibilities
                    vector_1 = suit_vector.copy()  # makes a new vector for each possibility
                    vector_1 -= possible_1_meld_part  # removes the meld part from the new vector

                    # gets a list of all possible meld parts in new vector
                    possible_2_meld_parts = get_possible_meld_parts(vector_1)
                    # if the list is empty then this is the end of this combination
                    if not possible_2_meld_parts:
                        combinations.append({'meld_part_combination': [possible_1_meld_part], 'leftover': vector_1})

                    else:  # if the vector still contains melds then continue the same process
                        for possible_2_meld_part in possible_2_meld_parts:
                            vector_2 = vector_1.copy()
                            vector_2 -= possible_2_meld_part

                            possible_3_meld_parts = get_possible_meld_parts(vector_2)
                            if not possible_3_meld_parts:
                                combinations.append(
                                    {'meld_part_combination': [possible_1_meld_part, possible_2_meld_part],
                                     'leftover': vector_2})

                            else:  # if the vector still contains melds then continue the process
                                for possible_3_meld_part in possible_3_meld_parts:
                                    vector_3 = vector_2.copy()
                                    vector_3 -= possible_3_meld_part

                                    possible_4_meld_parts = get_possible_meld_parts(vector_3)
                                    if not possible_4_meld_parts:
                                        combinations.append({'meld_part_combination': [possible_1_meld_part,
                                                                                       possible_2_meld_part,
                                                                                       possible_3_meld_part],
                                                             'leftover': vector_3})

                                    else:  # if the vector still contains melds then continue the process
                                        for possible_4_meld_part in possible_4_meld_parts:
                                            vector_4 = vector_3.copy()
                                            vector_4 -= possible_4_meld_part

                                            combinations.append({'meld_part_combination': [possible_1_meld_part,
                                                                                           possible_2_meld_part,
                                                                                           possible_3_meld_part,
                                                                                           possible_4_meld_part],
                                                                 'leftover': vector_4})

            return combinations

        def get_pair_number(meld_parts: list[np.ndarray]) -> int:
            """
            Meld parts are either pairs or part of a sequence, this function gets the number of pair meld parts

            :param meld_parts: list of numpy array representing meld parts
                   example: [[0 2 0 0 0 0 0 0 0], [0 1 0 1 0 0 0 0 0], [0 0 0 1 1 0 0 0 0]]
            :return: count of pair meld parts,
                     example: [[0 2 0 0 0 0 0 0 0], [0 1 0 1 0 0 0 0 0], [0 0 0 1 1 0 0 0 0]] -> 1
            """

            pair_counter = 0
            for meld_part in meld_parts:
                if 2 in meld_part:
                    pair_counter += 1
            return pair_counter

        #  ------------  start of tenpai algorithm  ------------

        # to facilitate calculation the player hand is turned into a numpy array
        player_hand_dict = player.playerhand_set.get(game_hand=self).to_dict()
        # the player can already have some melds locked
        number_of_locked_melds = player.playermeld_set.filter(game_hand=self).count()
        # therefore he only needs a required number of meld to win
        required_melds_to_win = 4 - number_of_locked_melds
        # and be in tenpai he needs one less than the maximum or the maximum with a pair and a meld part
        minimum_melds_to_tenpai = required_melds_to_win - 1

        # there is only two special cases with different tenpai conditions: 13 orphans and 7 pairs
        if check_for_13_orphans(player_hand_dict) or check_for_7_pairs(player_hand_dict):
            player.in_tenpai = True
            player.save()
            return

        # to know if the player hand is in tenpai or not let's find out all the combinations of melds and meld parts
        # that could lead to a tenpai
        viable_combinations = {'bamboo': [], 'character': [], 'dot': [], 'honor': [], }
        # since combinations cannot cross suits, let's find out those combinations suit by suit
        for suit in ('bamboo', 'character', 'dot', 'honor'):
            # first let's get all unique melds combinations
            possible_melds = get_meld_combinations(player_hand_dict[suit])
            possible_melds = delete_duplicate_leftovers(possible_melds)
            # then for each one of them
            for possible_meld in possible_melds:
                # if the leftover contains more than 4 tiles it cannot be a tenpai since 3 melds in hand is the minimum
                if sum(possible_meld.get('leftover')) <= 4:
                    # for the remaining meld combinations let's get all unique meld parts combinations
                    possible_meld_parts = get_meld_part_combinations(possible_meld.get('leftover'))
                    possible_meld_parts = delete_duplicate_leftovers(possible_meld_parts)
                    # then for each one of those meld parts combinations
                    for possible_meld_part in possible_meld_parts:
                        # if the leftover contains more than 1 isolated tile it cannot be a tenpai
                        # since in the case of 4 melds in hand there is 1 isolated tile and in the case of
                        # 3 melds, a pair and a meld_part in hand there is none
                        if sum(possible_meld_part.get('leftover')) <= 1:
                            # at this point any combinations has at least 3 melds and at maximum 1 isolated tile
                            # meaning that this is a viable combination of melds and meld parts for this suit
                            # so let's calculate how many pairs there are in the meld parts
                            pair_number = get_pair_number(possible_meld_part.get('meld_part_combination'))
                            #  and add it to the viable combinations of said suit
                            viable_combinations[suit].append({
                                'meld_number': len(possible_meld.get('meld_combination')),
                                'pair_number': pair_number,
                                'meld_part_number': len(possible_meld_part.get('meld_part_combination')) - pair_number,
                                # 'meld_combination': possible_meld.get('meld_combination'),
                                'meld_part_combination': possible_meld_part.get('meld_part_combination'),
                                'leftover': possible_meld_part.get('leftover')
                            })

            # if any of the suit does not have any viable combinations, meaning it has more than one isolated tile
            # or more than 4 tiles out of a meld then it cannot be a tenpai
            if not viable_combinations[suit]:
                player.in_tenpai = False
                player.save()
                return

        # waits = []  # should be added to return the number of tiles the player is waiting for

        # finally let's try all possible combinations of viable combinations of each suit
        for viable_bamboo in viable_combinations['bamboo']:
            for viable_character in viable_combinations['character']:
                for viable_dot in viable_combinations['dot']:
                    for viable_honor in viable_combinations['honor']:
                        # let's calculate how many melds, pairs and meld parts the combination has
                        total_meld_number = viable_bamboo['meld_number'] + viable_character['meld_number'] + \
                            viable_dot['meld_number'] + viable_honor['meld_number']
                        total_pair_number = viable_bamboo['pair_number'] + viable_character['pair_number'] + \
                            viable_dot['pair_number'] + viable_honor['pair_number']
                        total_meld_part_number = viable_bamboo['meld_part_number'] + viable_character[
                            'meld_part_number'] + viable_dot['meld_part_number'] + viable_honor['meld_part_number']
                        # if the combination has enough melds to win regardless of the last tile then it is a tenpai
                        if total_meld_number == required_melds_to_win:
                            player.in_tenpai = True
                            player.save()
                            return
                        # if the combination the minimum melds to tenpai, a pair and a meld part then it is a tenpai
                        elif total_meld_number == minimum_melds_to_tenpai \
                                and total_pair_number == 1 and total_meld_part_number == 1:
                            player.in_tenpai = True
                            player.save()
                            return

        # if this point is reached it means no tenpai has been found therefore the player hand is not in tenpai
        player.in_tenpai = False
        player.save()


class TileStackHolder(models.Model):
    """
    Stores a single holder of a tile stack related to a game hand
    """
    name = models.CharField(max_length=255)
    game_hand = models.ForeignKey(Hand, on_delete=models.PROTECT)  # FK to GameHand

    @staticmethod
    def create_tile_stack(name: str,
                          game_hand: Hand) -> TileStack:
        """
        Simplifies the use of the default django TileStackHolder constructor and create a default linked tile stack

        :param name: name given to the tile stack holder
        :param game_hand: instance of GameHand related to the holder
        :return: created instance of TileStack
        """

        tile_stack_holder = TileStackHolder(name=name, game_hand=game_hand)
        tile_stack_holder.save()

        return TileStack.create(name, tile_stack_holder)


class PlayerHand(TileStackHolder):
    """
    Stores a special holder of tile stack which is related to a player, and can be opened by calls.
    This is a model inherited from TileStackHolder.
    """
    player = models.ForeignKey(Player, on_delete=models.PROTECT)
    is_opened = models.BooleanField(default=False)

    @staticmethod
    def create_player_hand(name: str,
                           game_hand: Hand,
                           player: Player) -> TileStack:
        """
        Simplifies the use of the default django PlayerHand constructor and create a default linked tile stack

        :param name: name given to the tile stack holder
        :param game_hand: instance of GameHand related to the holder
        :param player: instance of Player related to the holder
        :return: created instance of TileStack
        """

        player_hand = PlayerHand(name=name, game_hand=game_hand, player=player)
        player_hand.save()

        return TileStack.create(name, player_hand)

    def to_dict(self) -> dict:

        player_hand_dict = {
            'bamboo': np.zeros(9, dtype=int),
            'character': np.zeros(9, dtype=int),
            'dot': np.zeros(9, dtype=int),
            'honor': np.zeros(7, dtype=int),
        }

        for tile in self.tile_stack.tile_set.all():
            if tile.suit in ('bamboo', 'character', 'dot'):
                player_hand_dict[tile.suit][int(tile.name)-1] += 1
            else:
                if tile.name == 'east':
                    player_hand_dict['honor'][0] += 1
                elif tile.name == 'south':
                    player_hand_dict['honor'][1] += 1
                elif tile.name == 'west':
                    player_hand_dict['honor'][2] += 1
                elif tile.name == 'north':
                    player_hand_dict['honor'][3] += 1
                elif tile.name == 'green':
                    player_hand_dict['honor'][4] += 1
                elif tile.name == 'red':
                    player_hand_dict['honor'][5] += 1
                elif tile.name == 'white':
                    player_hand_dict['honor'][6] += 1

        return player_hand_dict


class PlayerMeld(TileStackHolder):
    """
    Stores a special holder of meld which is related to a player.
    This is a model inherited from TileStackHolder.
    """
    player = models.ForeignKey(Player, on_delete=models.PROTECT)

    @staticmethod
    def create_meld(name: str,
                    type: str,
                    suit: str,
                    game_hand: Hand,
                    player: Player,
                    is_opened: bool = True,
                    length: int = 0) -> Meld:
        """
        Simplifies the use of the default django PlayerMeld constructor and create a default linked meld

        :param name: name given to the tile stack holder
        :param type: type of the meld to create
        :param suit: suit of the meld to create
        :param game_hand: instance of GameHand related to the holder
        :param player: instance of Player related to the holder
        :param is_opened: is_opened attribute of the meld to create
        :param length: length of the meld to create
        :return: created instance of Meld
        """

        player_meld = PlayerMeld(name=name, game_hand=game_hand, player=player)
        player_meld.save()

        return Meld.create_meld(name, type, suit, player_meld, is_opened, length)


class PlayerDiscard(TileStackHolder):
    """
    Stores a special holder of tile stack which is related to a player.
    This is a model inherited from TileStackHolder.
    """
    player = models.ForeignKey(Player, on_delete=models.PROTECT)

    @staticmethod
    def create_player_discard(name: str,
                              game_hand: Hand,
                              player: Player) -> None:
        """
        Simplifies the use of the default django PlayerDiscard constructor and create a default linked tile stack

        :param name: name given to the tile stack holder
        :param game_hand: instance of GameHand related to the holder
        :param player: instance of Player related to the holder
        :return: created instance of TileStack
        """

        player_discard = PlayerDiscard(name=name, game_hand=game_hand, player=player)
        player_discard.save()
        TileStack.create(name, player_discard)
