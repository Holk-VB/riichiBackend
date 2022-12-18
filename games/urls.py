from django.urls import path
from games.views import CreateGame, AddUserToGame, ViewGame, DiscardTile, CallInCallPhase, CallInTurnPhase

urlpatterns = [
    path('create', CreateGame.as_view(), name="create_game"),
    path('<int:game_id>/join', AddUserToGame.as_view(), name="add_user_to_game"),
    path('<int:game_id>', ViewGame.as_view(), name="view_game"),
    path('<int:game_id>/discard/<int:tile_id>', DiscardTile.as_view(), name="discard_tile"),
    path('<int:game_id>/call_in_call_phase', CallInCallPhase.as_view(), name="call_in_call_phase"),
    path('<int:game_id>/call_in_turn_phase', CallInTurnPhase.as_view(), name="call_in_turn_phase"),
]
