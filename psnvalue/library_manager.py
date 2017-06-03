import json
import requests
import collections
import time
from psycopg2 import IntegrityError
from django.utils import timezone
from datetime import datetime
from .models import Library, GameList, GamePrice, GameRatings, GameValue

#PSN Library Name
PSN_MODEL_LIBRARY_NAME = 'PS4'
#PSN Default Rating Value
PSN_MODEL_RATING_DEFAULT_VALUE = 1
#PSN Default Rating Count
PSN_MODEL_RATING_DEFAULT_COUNT = 0
#PSN Default Free Value - anything less than one causes division by zero errors
PSN_MODEL_PRICE_FREE = 1
#PSN Library Total Results
PSN_JSON_ELEM_TOTAL_RESULTS = 'total_results'
#PSN Each Game JSON element
PSN_JSON_ELEM_EACH_GAME = 'links'
#PSN Sub-Base Game JSON element i.e. bundles etc.
PSN_JSON_ELEM_SUB_GAME = 'parent_name'
#PSN TODO Maybe use this for identifying full games
PSN_JSON_ELEM_FULL_GAME = 'Full Game'
#PSN Game release date
PSN_JSON_ELEM_RELEASE_DATE = 'release_date'
#PSN Game ID JSON element
PSN_JSON_ELEM_GAME_ID = 'id'
#PSN Game Name JSON element
PSN_JSON_ELEM_GAME_NAME = 'name'
#PSN Game Full Detials URL JSON element
PSN_JSON_ELEM_GAME_URL = 'url'
#PSN Game Platform List JSON element
PSN_JSON_ELEM_GAME_PFORMS = 'playable_platform'
#PSN Game PS4 Platform Title
PSN_JSON_ELEM_GAME_PS4_PFORM = 'PS4™'
#PSN Game Image list JSON element
PSN_JSON_ELEM_GAME_IMAGES = 'images'
#PSN Game Image type JSON element
PSN_JSON_ELEM_GAME_IMGTYPE = 'type'
#PSN Game Image thumb type
PSN_JSON_ELEM_GAME_IMGTYPE_THUMB = 1
#PSN Game Age Rating JSON element - part of the full game details json!
PSN_JSON_ELEM_GAME_AGERATING = 'age_limit'
#PSN Default Age Rating
PSN_DEFAULT_AGE_RATING = 0
#PSN Main Game details block
PSN_JSON_ELEM_GAME_PRICE_BLOCK = 'default_sku'
#PSN Base Price JSON element - part of the full game details json!
PSN_JSON_ELEM_GAME_BASE_PRICE = 'price'
#PSN Base Discount JSON element - part of the full game details json!
PSN_JSON_ELEM_GAME_REWARDS = 'rewards'
#PSN Base Discount JSON element - part of the full game details json!
PSN_JSON_ELEM_GAME_BASE_DISCOUNT = 'discount'
#PSN PS Plus Discount JSON element - part of the full game details json!
PSN_JSON_ELEM_GAME_BONUS_DISCOUNT = 'bonus_discount'
#PSN Game Rating Parent Block - part of the full game details json!
PSN_JSON_ELEM_GAME_RATING_BLOCK = 'star_rating'
#PSN Game Rating Parent Block - part of the full game details json!
PSN_JSON_ELEM_GAME_RATING_VALUE = 'score'
#PSN Game Rating Parent Block - part of the full game details json!
PSN_JSON_ELEM_GAME_RATING_COUNT = 'total'


def update_library(p_library_id):
    print("Gonna update the lib: ", p_library_id)
    #For the moment, only psn is supported.
    update_psn_lib(p_library_id)

def update_psn_lib(p_library_id):
    count_of_base_games = 0
    psn_lib_json = get_psn_lib_json()
    count = 0
    for eachGame in psn_lib_json[PSN_JSON_ELEM_EACH_GAME]:
        # We're just looking for base games i.e. ignore bundles etc.
        # If a game is on sale, the bundle is (always?) on sale too.
        # Maybe we shouldn't be.... Do some tests on this.
        if PSN_JSON_ELEM_SUB_GAME in eachGame:
            #print("Game is not full game! - ", eachGame[PSN_JSON_ELEM_GAME_NAME])
            continue

        # Check to make sure the game is released - otherwise we
        # can get games without prices etc.
        if(game_is_released(eachGame) == False):
            #print("Game is not released! - ", eachGame[PSN_JSON_ELEM_GAME_NAME])
            continue

        # We found a base game, so parse the details
        count_of_base_games += 1
        if(game_exists_in_db(p_library_id, eachGame[PSN_JSON_ELEM_GAME_ID])):
            print("Game exists: ", eachGame[PSN_JSON_ELEM_GAME_NAME])
        else:
            print("Game doesn't exist: ", eachGame[PSN_JSON_ELEM_GAME_NAME])
            add_psn_game(p_library_id, eachGame)
            time.sleep(1)

        count += 1
        if count == 30:
            break

def add_psn_game(p_library_id, p_base_game_json):
    g_id = p_base_game_json[PSN_JSON_ELEM_GAME_ID]
    g_name = p_base_game_json[PSN_JSON_ELEM_GAME_NAME]
    g_url = p_base_game_json[PSN_JSON_ELEM_GAME_URL]
    g_thumb = get_psn_thumbnail(p_base_game_json[PSN_JSON_ELEM_GAME_IMAGES])
    g_age = PSN_DEFAULT_AGE_RATING
    print("Adding game: ", g_name, " - ", g_url)
    game_entry = add_game_list_entry_to_db(g_id, g_name, g_url, g_thumb, g_age, Library.objects.get(pk=p_library_id))
    add_psn_full_game_details(game_entry)

def add_psn_full_game_details(p_game_entry):
    full_details_json = get_psn_game_json(p_game_entry.json_url)
    print("Game: ",full_details_json[PSN_JSON_ELEM_GAME_NAME],"- Age: ",full_details_json[PSN_JSON_ELEM_GAME_AGERATING])
    #Update the age rating
    g_age = full_details_json[PSN_JSON_ELEM_GAME_AGERATING]
    set_game_age_rating(p_game_entry, g_age)
    #Add a GamePrice entry
    g_price = full_details_json[PSN_JSON_ELEM_GAME_PRICE_BLOCK][PSN_JSON_ELEM_GAME_BASE_PRICE]
    g_discount_tuple = get_psn_game_discounts(full_details_json[PSN_JSON_ELEM_GAME_PRICE_BLOCK])
    add_game_price_entry(p_game_entry, g_price, g_discount_tuple.base, g_discount_tuple.plus)
    #Add a GameRatings entry
    add_psn_game_ratings(p_game_entry, full_details_json[PSN_JSON_ELEM_GAME_RATING_BLOCK])
    #Add a GameValue entry
    add_psn_game_value(p_game_entry)

def get_psn_game_discounts(p_game_price_block_json):
    psn_discounts = collections.namedtuple('psn_discounts', ['base', 'plus'])
    base_discount = 0
    plus_discount = 0
    if (PSN_JSON_ELEM_GAME_REWARDS in p_game_price_block_json) and (p_game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS]):
        print(type(p_game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS]))
        if PSN_JSON_ELEM_GAME_BASE_DISCOUNT in p_game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0]:
            base_discount = p_game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0][PSN_JSON_ELEM_GAME_BASE_DISCOUNT]
        if PSN_JSON_ELEM_GAME_BONUS_DISCOUNT in p_game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0]:
            plus_discount = p_game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0][PSN_JSON_ELEM_GAME_BONUS_DISCOUNT]

    return psn_discounts(base=base_discount,plus=plus_discount)

def add_psn_game_ratings(p_game_entry, p_game_rating_block_json):
    g_rating_value = p_game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_VALUE] if p_game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_VALUE] else PSN_MODEL_RATING_DEFAULT_VALUE
    g_rating_count = p_game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_COUNT] if p_game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_COUNT] else PSN_MODEL_RATING_DEFAULT_COUNT
    add_game_rating_entry(p_game_entry, g_rating_value, g_rating_count)

def add_game_rating_entry(p_game_entry, p_rating_value, p_rating_count):
    return GameRatings.objects.create(game_id=p_game_entry, last_updated=timezone.now(), rating=p_rating_value, rating_count=p_rating_count)

def add_game_price_entry(p_game_entry, p_price, p_base_discount, p_plus_discount):
    return GamePrice.objects.create(game_id=p_game_entry, last_updated=timezone.now(), base_price=p_price, base_discount=p_base_discount, plus_discount=p_plus_discount)

def add_psn_game_value(p_game_entry):
    g_rating = get_game_rating(p_game_entry)
    g_price = get_game_price(p_game_entry)
    g_price = g_price if g_price > 0.0 else PSN_MODEL_PRICE_FREE
    print("Rating: ", g_rating)
    print("Price: ", g_price)
    #Calculate the value for this game
    g_val = calculate_game_value(g_rating, g_price)
    print("Value: ", g_val)
    #Add entry to DB for this game value
    add_game_value_entry(p_game_entry, g_val)

def calculate_game_value(p_game_rating, p_game_price):
    fixed_price = round(p_game_price)
    fixed_rating = p_game_rating * 100
    return round(1/(fixed_price/fixed_rating)*1000)
    #return round((fixed_price/fixed_rating)*100)

def get_game_price(p_game_entry):
    g_game_price_obj = GamePrice.objects.get(game_id=p_game_entry)
    g_game_price = g_game_price_obj.base_price

    if(g_game_price_obj.plus_discount > 0):
        g_game_price = apply_game_discount(g_game_price, g_game_price_obj.plus_discount)
    elif(g_game_price_obj.base_discount > 0):
        g_game_price = apply_game_discount(g_game_price, g_game_price_obj.base_discount)

    return g_game_price

def apply_game_discount(p_base_price, p_discount_percentage):
    return ((p_base_price*(100-p_discount_percentage))/100)

def get_game_rating(p_game_entry):
    return GameRatings.objects.get(game_id=p_game_entry).rating

def add_game_value_entry(p_game_entry, p_game_value):
    return GameValue.objects.create(game_id=p_game_entry, value_score=p_game_value)

def set_game_age_rating(p_game_entry, p_new_age_rating):
    p_game_entry.age_rating = p_new_age_rating
    p_game_entry.save()

def add_game_list_entry_to_db(p_g_id, p_g_name, p_g_url, p_g_thumb, p_g_age, p_library_obj):
    g_list_entry = None
    try:
        g_list_entry = GameList.objects.create(game_id=p_g_id, game_name=p_g_name, json_url=p_g_url, image_url=p_g_thumb, age_rating=p_g_age, library_name=p_library_obj)
    except Exception as e:
        g_list_entry = GameList.objects.get(game_id=p_g_id)        
    return g_list_entry

def get_psn_thumbnail(p_image_list):
    game_thumb = None
    for eachGameImg in p_image_list:
        if eachGameImg[PSN_JSON_ELEM_GAME_IMGTYPE] == PSN_JSON_ELEM_GAME_IMGTYPE_THUMB:
            game_thumb = eachGameImg[PSN_JSON_ELEM_GAME_URL]
            break
    return game_thumb

def update_psn_game(p_base_game_json):
    print("Updating game: ", p_base_game_json[PSN_JSON_ELEM_GAME_NAME])

def game_exists_in_db(p_library_id, p_game_id):
    return (GameList.objects.filter(game_id=p_game_id, library_name=p_library_id).count() != 0)

def game_is_on_PS4(p_platform_list):
    return PSN_JSON_ELEM_GAME_PS4_PFORM in p_platform_list

def game_is_released(p_lib_game_entry):
    g_is_released = False
    g_release_date = datetime.strptime(p_lib_game_entry[PSN_JSON_ELEM_RELEASE_DATE], '%Y-%m-%dT%H:%M:%SZ')
    if(g_release_date < datetime.now()):
        g_is_released = True
    return g_is_released

def get_psn_lib_total_results(p_psn_lib_url):
    response_json = requests.get(p_psn_lib_url+'0')
    psn_lib_json = response_json.json()
    return psn_lib_json[PSN_JSON_ELEM_TOTAL_RESULTS]

def get_lib_url_from_db(p_lib_name):
    return Library.objects.get(library_name=p_lib_name).library_url

def get_psn_lib_json():
    psn_lib_json = None
    psn_lib_url = get_lib_url_from_db(PSN_MODEL_LIBRARY_NAME)
    response_json = requests.get(psn_lib_url+str(get_psn_lib_total_results(psn_lib_url)))
    psn_lib_json = response_json.json()
    #File for testing only - live version will pull json from psn api
    #with open('staticfiles/psnvalue/TotalPS4GameLibrary.json') as data_file:    
    #    psn_lib_json = json.load(data_file)

    return psn_lib_json

def get_psn_game_json(p_game_url):
    psn_game_json = None
    response_json = requests.get(p_game_url)
    psn_game_json = response_json.json()
    #File for testing only - live version will pull json from psn api
    #with open('staticfiles/psnvalue/DragonAgeInquisition_FullGame.json') as data_file:
    #with open('staticfiles/psnvalue/DarkSoulsIII_FullGame.json') as data_file:
    #    psn_game_json = json.load(data_file)

    return psn_game_json
