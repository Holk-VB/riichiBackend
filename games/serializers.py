from rest_framework import serializers
from django.contrib.auth.models import User
from games.models import Game, Player, Round, Hand
from tiles.serializers import TileStackSerializer, MeldSerializer


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = [
            'id',
            'username',
        ]


class HandSerializer(serializers.ModelSerializer):

    class Meta:
        model = Hand
        depth = 1
        fields = [
            'id',
            'in_call_phase',
            'last_discarded_tile',
            'position_in_round',
            'doras',
        ]


class RoundSerializer(serializers.ModelSerializer):
    current_hand = HandSerializer()

    class Meta:
        model = Round
        depth = 1
        fields = [
            'id',
            'position_in_game',
            'prevailing_wind',
            'current_hand',
        ]


class PlayerGameSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    discard = TileStackSerializer(source='current_player_discard.tile_stack')
    # melds = MeldSerializer(source='current_player_melds', many=True)
    melds = serializers.SerializerMethodField()

    def get_melds(self, instance):
        melds_data = []
        for player_meld in instance.current_player_melds.all():
            melds_data.append(MeldSerializer(player_meld.tile_stack.meld).data)
        return melds_data

    class Meta:
        model = Player
        depth = 1
        fields = [
            'id',
            'user',
            'score',
            'wind',
            'is_dealer',
            'can_play',
            'call_sent',
            'discard',
            'melds',
        ]


class PlayerLightSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Player
        depth = 1
        fields = [
            'id',
            'user',
        ]


class GameSerializer(serializers.ModelSerializer):
    current_round = RoundSerializer()
    players = PlayerGameSerializer(source='player_set', many=True)

    class Meta:
        model = Game
        depth = 1
        fields = [
            'id',
            'is_full',
            'is_over',
            'players',
            'current_round',
        ]


class GameLightSerializer(serializers.ModelSerializer):
    players = PlayerLightSerializer(source='player_set', many=True)

    class Meta:
        model = Game
        depth = 1
        fields = [
            'id',
            'is_full',
            'players',
        ]


class PlayerSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    hand = TileStackSerializer(source='current_player_hand.tile_stack')

    class Meta:
        model = Player
        depth = 1
        fields = [
            'id',
            'user',
            'hand',
            'score',
            'wind',
            'is_dealer',
            'can_play',
            'possible_calls',
            'call_sent',
            'in_tenpai',
        ]
