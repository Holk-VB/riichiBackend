from django.db import models
from tiles.utils import *
import random
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from games.models import TileStackHolder


class TileStack(models.Model):
    """
    Stores a stack of tile held by a TileStakHolder
    """
    name = models.CharField(max_length=255)
    length = models.IntegerField(default=0)
    holder = models.OneToOneField('games.TileStackHolder',  # FK to TileStackHolder
                                  on_delete=models.PROTECT,
                                  primary_key=False,
                                  related_name='tile_stack')

    @staticmethod
    def create(name: str,
               holder: 'TileStackHolder',
               length: int = 0) -> 'TileStack':
        """
        Simplifies the use of the default django TileStack constructor

        :param name: name given to the tile stack
        :param holder: instance of TileStackHolder holding the tile stack
        :param length: number of tiles in the tile stack
        :return: created instance of TileStack
        """

        tile_stack = TileStack(name=name, holder=holder, length=length)
        tile_stack.save()

        return tile_stack

    def transfer_to(self, receiving_tile_stack: 'TileStack', tile: 'Tile') -> None:
        """
        Transfers the tile from self tile stack to receiving tile stack

        :param receiving_tile_stack: instance of TileStack that should receive the tile
        :param tile: instance of Tile that should be transferred
        :return: None
        """
        tile_old_position_in_tile_stack = tile.position_in_tile_stack
        tile.tile_stack = receiving_tile_stack  # transfer the tile to the receiving_tile_stack
        tile.position_in_tile_stack = receiving_tile_stack.length
        tile.save()
        receiving_tile_stack.length += 1  # add 1 to receiving tile_stack length
        receiving_tile_stack.save()

        moving_tiles = self.tile_set.filter(position_in_tile_stack__gt=tile_old_position_in_tile_stack)
        for tile in moving_tiles:  # move the position of other tiles of sending tile_stack
            tile.position_in_tile_stack -= 1
            tile.save()
        self.length -= 1  # remove 1 to sending tile_stack length
        self.save()

    def pick_in(self, target: 'TileStack', number_of_tiles: int = 1) -> None:
        """
        Picks the number_of_tiles last tiles of the target tile stack and add them to self tile stack

        :param target: instance of TileStack in which tiles should be picked
        :param number_of_tiles: number of tiles that should be picked in target
        :return: None
        """
        for _ in range(number_of_tiles):
            tile = target.tile_set.get(position_in_tile_stack=target.length-1)  # get last tile of the target
            tile.tile_stack = self  # transfer tile to self tile_stack
            tile.position_in_tile_stack = self.length
            tile.save()
            self.length += 1  # add 1 to self tile_stack length
            self.save()
            target.length -= 1  # remove 1 to the target tile_stack length
            target.save()

    def shuffle(self) -> None:
        """
        Shuffles self tile stack by setting tiles position with the random seed of the game

        :return: None
        """
        tiles = self.tile_set.all()  # get all tiles of this tile_stack
        tiles_position = list(tiles.values_list('position_in_tile_stack', flat=True))  # get list of tiles position

        random.setstate(self.holder.game_hand.round.game.get_random_state())  # get random state of the game
        random.shuffle(tiles_position)  # shuffle tiles position
        self.holder.game_hand.round.game.random_state = random.getstate()  # store random state of the game

        for tile in tiles:  # set new tiles position in set
            tile.position_in_tile_stack = tiles_position.pop()
            tile.save()

    def order_by_default(self):
        """
        Orders self tile stack by suit bamboo -> character -> dot -> dragon -> wind and by name

        :return: None
        """
        tiles = self.tile_set.order_by('suit', 'name').all()  # gets all tiles of this tile_stack in logic order
        count = 0

        for tile in tiles:  # sets new tiles position
            tile.position_in_tile_stack = count
            tile.save()  # saves updated tiles to database
            count += 1

    def contain(self, tile_suit: str, tile_name: str, number: int = 1) -> bool:
        """
        Check if the self tile stack contains set number of tile the set tile_suit and tile_name

        :param tile_suit: suit of the tile that should be searched for
        :param tile_name: name of the tile that should be searched for
        :param number: number of tiles that should be searched for
        :return: True if number of tile with tile_suit / tile_name were found, else otherwise
        """
        return self.tile_set.filter(suit=tile_suit, name=tile_name).count() >= number


class Tile(models.Model):
    """
    Stores a single tile contained in a TileStack
    """
    suit = models.CharField(max_length=255, choices=VALID_SUITS)  # bamboo, character, dot, dragon or wind
    name = models.CharField(max_length=255, choices=VALID_NAMES)  # 1 -> 9, east -> north, green -> white
    tile_stack = models.ForeignKey(TileStack, on_delete=models.PROTECT)  # FK to TileStack
    position_in_tile_stack = models.IntegerField()  # position in TileStack
    is_horizontal = models.BooleanField(default=False)  # needed when a tile is stolen

    @staticmethod
    def create(suit: str,
               name: str,
               tile_stack: TileStack,
               position_in_tile_stack: int) -> 'Tile':
        """
        Simplifies the use of the default django Tile constructor

        :param suit: bamboo, character, dot, dragon or wind
        :param name: '1' to '9' if bamboo/character/dot, east/south/west/north if wind, green/red/white if dragon
        :param tile_stack: instance of TileStack
        :param position_in_tile_stack: integer to order the instance of TileStack
        :return: created instance of Tile
        """

        tile = Tile(suit=suit,
                    name=name,
                    tile_stack=tile_stack,
                    position_in_tile_stack=position_in_tile_stack)  # creates Tile instance with set parameters

        tile.save()  # saves Tile instance to database
        return tile


class Meld(TileStack):
    """
    Stores a special stack of tile which has a type, a suit and can be opened in calls.
    This is a model inherited from TileStack.
    """
    type = models.CharField(max_length=255, choices=MELD_NAMES)  # chi, pon, or opened / closed / late kan
    suit = models.CharField(max_length=255, choices=VALID_SUITS)
    is_opened = models.BooleanField()  # represent if the meld opens the hand or not for yakus

    @staticmethod
    def create_meld(name: str,
                    type: str,
                    suit: str,
                    holder: 'TileStackHolder',
                    is_opened: bool = True,
                    length: int = 0):
        """
        Simplifies the use of the default django Meld constructor.

        :param name: name that should be given to the meld
        :param type: chi, pon, or opened / closed / late kan
        :param suit: bamboo, character, dot, dragon or wind
        :param holder: instance of TileStackHolder holding the meld
        :param is_opened: True if the meld opens the player hand, False otherwise
        :param length: number of tiles in the meld
        :return: created instance of Meld
        """

        meld = Meld(name=name, suit=suit, type=type, holder=holder, is_opened=is_opened, length=length)
        meld.save()

        return meld
