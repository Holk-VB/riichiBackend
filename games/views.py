from rest_framework import generics, status
from games.models import Game, Player
from games.serializers import GameSerializer, PlayerSerializer, GameLightSerializer, PlayerLightSerializer
from games.utils import *
from django.core.exceptions import ObjectDoesNotExist
from tiles.utils import get_previous_wind
from rest_framework.response import Response
from django.contrib.auth.models import User


class CreateGame(generics.CreateAPIView):

    def post(self, request, *args, **kwargs):
        user = User.objects.get(id=request.user.id)
        game = Game.create(user, user.username)

        serialized_player = PlayerLightSerializer(game.player_set.get(user=user)).data
        serialized_game = GameLightSerializer(game).data
        return Response({'player': serialized_player, 'game': serialized_game}, status.HTTP_200_OK)


class AddUserToGame(generics.CreateAPIView):

    def post(self, request, *args, **kwargs):
        user = User.objects.get(id=request.user.id)
        game = Game.objects.get(id=kwargs['game_id'])

        if game.is_full:
            return Response('game is already full', status.HTTP_401_UNAUTHORIZED)

        try:
            player = Player.objects.get(game=game, user_id=request.user.id)
            if player:
                return Response('you are already in game', status.HTTP_401_UNAUTHORIZED)
        except ObjectDoesNotExist:
            pass

        game.add_player(user, user.username)

        if game.player_set.all().count() == MAX_PLAYERS_PER_GAME:
            game.fill_up()
            game.start()

        serialized_player = PlayerLightSerializer(game.player_set.get(user=user)).data
        serialized_game = GameLightSerializer(game).data
        return Response({'player': serialized_player, 'game': serialized_game}, status.HTTP_200_OK)


class ViewGame(generics.RetrieveAPIView):

    def get(self, request, *args, **kwargs):
        game = Game.objects.get(id=kwargs['game_id'])

        try:
            player = Player.objects.get(game=game, user_id=request.user.id)
        except ObjectDoesNotExist:
            if game.is_full:
                serialized_game = GameSerializer(game).data
            else:
                serialized_game = GameLightSerializer(game).data
            return Response({'game': serialized_game}, status.HTTP_200_OK)

        if game.is_full:
            serialized_player = PlayerSerializer(player).data
            serialized_game = GameSerializer(game).data
        else:
            serialized_player = PlayerLightSerializer(player).data
            serialized_game = GameLightSerializer(game).data

        return Response({'player': serialized_player, 'game': serialized_game}, status.HTTP_200_OK)


class DiscardTile(generics.CreateAPIView):

    def post(self, request, *args, **kwargs):
        game = Game.objects.get(id=kwargs['game_id'])
        current_hand = game.current_round.current_hand

        try:
            player = Player.objects.get(game=game, user_id=request.user.id, can_play=True)
        except ObjectDoesNotExist:
            return Response('wait for your time to play', status.HTTP_401_UNAUTHORIZED)

        try:
            player_hand = player.playerhand_set.get(game_hand=current_hand)
            tile = player_hand.tile_stack.tile_set.get(id=kwargs['tile_id'])
        except ObjectDoesNotExist:
            return Response('you do not have this tile in your hand', status.HTTP_401_UNAUTHORIZED)

        current_hand.player_discard(player, tile)
        current_hand.start_call_phase()

        return Response('ok', status.HTTP_200_OK)


class CallInCallPhase(generics.CreateAPIView):

    def post(self, request, *args, **kwargs):

        call = request.data['call']
        game = Game.objects.get(id=kwargs['game_id'])
        current_hand = game.current_round.current_hand

        try:
            player = Player.objects.get(game=game, user_id=request.user.id)
        except ObjectDoesNotExist:
            return Response('you are not a player of this game', status.HTTP_404_NOT_FOUND)

        # twisted
        last_player = Player.objects.get(game=game, wind=get_previous_wind(current_hand.next_wind_to_play))
        if player == last_player:
            return Response('you cannot call your own discarded tile', status.HTTP_401_UNAUTHORIZED)

        if not current_hand.in_call_phase:
            return Response('this is not the call phase', status.HTTP_401_UNAUTHORIZED)

        if call not in player.possible_calls:
            return Response('this is not a possible call', status.HTTP_401_UNAUTHORIZED)

        player.send_call(call)

        return Response('ok', status.HTTP_200_OK)


class CallInTurnPhase(generics.CreateAPIView):

    def post(self, request, *args, **kwargs):

        call = request.data['call']
        game = Game.objects.get(id=kwargs['game_id'])
        current_hand = game.current_round.current_hand

        try:
            player = Player.objects.get(game=game, user_id=request.user.id, can_play=True)
        except ObjectDoesNotExist:
            return Response('this is not your turn', status.HTTP_401_UNAUTHORIZED)

        if call not in player.possible_calls:
            return Response('this is not a possible call', status.HTTP_401_UNAUTHORIZED)

        player.send_call(call)
        current_hand.player_call(player)

        return Response('ok', status.HTTP_200_OK)
