import json
import requests
import collections
import time
from statistics import pstdev, mean
from django.db import transaction
from psycopg2 import IntegrityError
from django.utils import timezone
from datetime import datetime
from .models import Library, GameList

# These were place-in-time values that were determined.
DEFAULT_STDEV = 0.71
DEFAULT_MEAN = 4.11
# DEFAULT_GAME_PRICE - anything less than one causes division by zero errors
DEFAULT_GAME_PRICE = 1

class GenericLibrary:

    def get_library_obj(self, p_library_id):
        return Library.objects.get(pk=p_library_id)

    def update_library_statistics(self, p_library_obj):
        list_of_game_ratings = self.get_list_of_all_game_ratings_in_lib(p_library_obj)
        p_library_obj.library_rating_stdev = self.calculate_standard_deviation(list_of_game_ratings)
        p_library_obj.library_rating_mean = self.calculate_mean(list_of_game_ratings)
        p_library_obj.last_updated = timezone.now()
        p_library_obj.save()

    def get_list_of_all_game_ratings_in_lib(self, p_library_obj):
        return GameList.objects.filter(library_fk=p_library_obj).values_list('rating', flat=True)

    def calculate_standard_deviation(self, p_list_of_ratings):
        if p_list_of_ratings: 
            return pstdev(p_list_of_ratings)
        else:
            return DEFAULT_STDEV

    def calculate_mean(self, p_list_of_ratings):
        if p_list_of_ratings:
            return mean(p_list_of_ratings)
        else:
            return DEFAULT_MEAN

    def game_exists_in_db(self, p_library_obj, p_game_id):
        return (GameList.objects.filter(game_id=p_game_id, library_fk=p_library_obj).count() != 0)

    def get_game_obj(self, p_library_obj, p_game_id):
        game_obj = None
        try:
            game_obj = GameList.objects.get(game_id=p_game_id, library_fk=p_library_obj)
        except GameList.DoesNotExist:
            pass
        return game_obj

    def add_skeleton_game_list_entry_to_db(self, p_g_id, p_g_name, p_g_url, p_g_thumb, p_g_age, p_library_obj):
        return GameList.objects.create(game_id=p_g_id, game_name=p_g_name, json_url=p_g_url, image_url=p_g_thumb, age_rating=p_g_age, library_fk=p_library_obj)

    def get_net_game_price(self, p_game_obj):
        game_price = p_game_obj.base_price
        game_discount = max(p_game_obj.base_discount, p_game_obj.plus_discount)

        if(game_discount > 0):
            game_price = self.apply_game_discount(game_price, game_discount)

        return game_price

    def apply_game_discount(self, p_base_price, p_discount_percentage):
        return ((p_base_price*(100-p_discount_percentage))/100)

    def calculate_game_value(self, p_game_rating, p_game_price):
        # Account for free games
        game_price = p_game_price if p_game_price > 0.0 else DEFAULT_GAME_PRICE
        fixed_price = round(game_price)
        fixed_rating = p_game_rating * 100
        return round(1/(fixed_price/fixed_rating)*100) 

    def apply_weighted_game_rating(self, p_library_obj, p_game_rating):
        return round((p_game_rating*10) + ((p_game_rating - p_library_obj.library_rating_mean)/p_library_obj.library_rating_stdev),2)

    def update_game_obj(self, p_game_obj):
        p_game_obj.last_updated = timezone.now()
        p_game_obj.save()
