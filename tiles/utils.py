VALID_TILES = (
    ('dot', '1'), ('dot', '2'), ('dot', '3'), ('dot', '4'), ('dot', '5'),
    ('dot', '6'), ('dot', '7'), ('dot', '8'), ('dot', '9'),
    ('bamboo', '1'), ('bamboo', '2'), ('bamboo', '3'), ('bamboo', '4'), ('bamboo', '5'),
    ('bamboo', '6'), ('bamboo', '7'), ('bamboo', '8'), ('bamboo', '9'),
    ('character', '1'), ('character', '2'), ('character', '3'), ('character', '4'), ('character', '5'),
    ('character', '6'), ('character', '7'), ('character', '8'), ('character', '9'),
    ('wind', 'east'), ('wind', 'south'), ('wind', 'west'), ('wind', 'north'),
    ('dragon', 'green'), ('dragon', 'red'), ('dragon', 'white'),
)

VALID_SUITS = (
    ('dot', 'dot'), ('bamboo', 'bamboo'), ('character', 'character'), ('wind', 'wind'), ('dragon', 'dragon')
)
NUMBER_SUITS = (
    ('dot', 'dot'), ('bamboo', 'bamboo'), ('character', 'character')
)
HONOR_SUITS = (
    ('wind', 'wind'), ('dragon', 'dragon')
)
WIND_NAMES = (
    ('east', 'east'), ('south', 'south'), ('west', 'west'), ('north', 'north')
)
VALID_NAMES = (
    ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'),
    ('east', 'east'), ('south', 'south'), ('west', 'west'), ('north', 'north'),
    ('green', 'green'), ('red', 'red'), ('white', 'white')
)
MELD_NAMES = (('kan', 'kan'), ('pon', 'pon'), ('chi', 'chi'))


def get_next_wind(current_wind_name: str):
    if current_wind_name == 'east':
        return 'south'
    elif current_wind_name == 'south':
        return 'west'
    elif current_wind_name == 'west':
        return 'north'
    else:
        return 'east'


def get_next_dragon(current_dragon_name: str):
    if current_dragon_name == 'green':
        return 'red'
    elif current_dragon_name == 'red':
        return 'white'
    else:
        return 'green'


def get_next_number(current_number_name: str):
    return str(int(current_number_name) % 9 + 1)


def get_next_tile_name(current_tile_suit: str, current_tile_name: str):
    if current_tile_suit == 'wind':
        return get_next_wind(current_tile_name)
    elif current_tile_suit == 'dragon':
        return get_next_dragon(current_tile_name)
    else:
        return get_next_number(current_tile_name)


def get_previous_wind(current_wind_name: str):
    if current_wind_name == 'east':
        return 'north'
    elif current_wind_name == 'south':
        return 'east'
    elif current_wind_name == 'west':
        return 'south'
    else:
        return 'west'


def get_previous_dragon(current_dragon_name: str):
    if current_dragon_name == 'green':
        return 'white'
    elif current_dragon_name == 'red':
        return 'green'
    else:
        return 'red'


def get_previous_number(current_number_name: str):
    if current_number_name == '1':
        return '9'
    else:
        return str(int(current_number_name) - 1)


def get_previous_tile_name(current_tile_suit: str, current_tile_name: str):
    if current_tile_suit == 'wind':
        return get_previous_wind(current_tile_name)
    elif current_tile_name == 'dragon':
        return get_previous_dragon(current_tile_name)
    else:
        return get_previous_number(current_tile_name)
