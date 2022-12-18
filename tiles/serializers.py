from rest_framework import serializers
from tiles.models import TileStack, Tile, Meld


class TileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tile
        depth = 1
        fields = [
            'id',
            'suit',
            'name',
            'is_horizontal',
        ]


class TileStackSerializer(serializers.ModelSerializer):
    tiles = serializers.SerializerMethodField()

    def get_tiles(self, instance):
        tiles = instance.tile_set.all().order_by('position_in_tile_stack')
        return TileSerializer(tiles, many=True).data

    class Meta:
        model = TileStack
        depth = 1
        fields = [
            'id',
            'tiles',
        ]


class MeldSerializer(serializers.ModelSerializer):
    tiles = serializers.SerializerMethodField()

    def get_tiles(self, instance):
        tiles = instance.tile_set.all().order_by('position_in_tile_stack')
        return TileSerializer(tiles, many=True).data

    class Meta:
        model = Meld
        depth = 1
        fields = [
            'id',
            'type',
            'suit',
            'name',
            'tiles',
        ]

