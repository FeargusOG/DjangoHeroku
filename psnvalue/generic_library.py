import json
import requests
import collections
import time
from django.db import transaction
from psycopg2 import IntegrityError
from django.utils import timezone
from datetime import datetime
from .models import Library, GameList, GamePrice, GameRatings, GameValue

#TODO tmp values for stdev and mean here
TMP_STDEV = 0.354
TMP_MEAN = 4.44

class GenericLibrary:
    m_stdev = TMP_STDEV
    m_mean = TMP_MEAN

    def game_exists_in_db(self, p_library_id, p_game_id):
        return (GameList.objects.filter(game_id=p_game_id, library_name=p_library_id).count() != 0)

    def add_game_list_entry_to_db(self, p_g_id, p_g_name, p_g_url, p_g_thumb, p_g_age, p_library_obj):
        g_list_entry = None
        try:
            g_list_entry = GameList.objects.create(game_id=p_g_id, game_name=p_g_name, json_url=p_g_url, image_url=p_g_thumb, age_rating=p_g_age, library_name=p_library_obj)
        except Exception as e:
            g_list_entry = GameList.objects.get(game_id=p_g_id)        
        return g_list_entry

    def get_game_price(self, p_game_entry):
        g_game_price_obj = GamePrice.objects.get(game_id=p_game_entry)
        g_game_price = g_game_price_obj.base_price

        if(g_game_price_obj.plus_discount > 0):
            g_game_price = self.apply_game_discount(g_game_price, g_game_price_obj.plus_discount)
        elif(g_game_price_obj.base_discount > 0):
            g_game_price = self.apply_game_discount(g_game_price, g_game_price_obj.base_discount)

        return g_game_price

    def calculate_game_value(self, p_game_rating, p_game_price):
        fixed_price = round(p_game_price)
        fixed_rating = p_game_rating * 100
        return round(1/(fixed_price/fixed_rating)*100) 

    def apply_weighted_game_rating(self, p_game_rating):
        return round((p_game_rating*10) + ((p_game_rating - self.m_mean)/self.m_stdev),2)

    def add_game_rating_entry(self, p_game_entry, p_rating_value, p_rating_count, p_weighted_rating):
        return GameRatings.objects.create(game_id=p_game_entry, last_updated=timezone.now(), rating=p_rating_value, rating_count=p_rating_count, weighted_rating=p_weighted_rating)

    def add_game_price_entry(self, p_game_entry, p_price, p_base_discount, p_plus_discount):
        return GamePrice.objects.create(game_id=p_game_entry, last_updated=timezone.now(), base_price=p_price, base_discount=p_base_discount, plus_discount=p_plus_discount)

    def apply_game_discount(self, p_base_price, p_discount_percentage):
        return ((p_base_price*(100-p_discount_percentage))/100)

    def get_game_rating(self, p_game_entry):
        return GameRatings.objects.get(game_id=p_game_entry).rating

    def get_game_weighted_rating(self, p_game_entry):
        return GameRatings.objects.get(game_id=p_game_entry).weighted_rating

    def add_game_value_entry(self, p_game_entry, p_game_value):
        return GameValue.objects.create(game_id=p_game_entry, value_score=p_game_value)

    def set_game_age_rating(self, p_game_entry, p_new_age_rating):
        p_game_entry.age_rating = p_new_age_rating
        p_game_entry.save()

    def get_lib_url_from_db(self, p_lib_name):
        return Library.objects.get(library_name=p_lib_name).library_url
