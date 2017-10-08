import json
import requests
import collections
import time
import traceback
import base64
import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from .generic_library import GenericLibrary
from urllib.request import urlopen

#PSN Library Name
PSN_MODEL_LIBRARY_NAME = 'PS4'
#PSN Default Rating Value
PSN_MODEL_RATING_DEFAULT_VALUE = 1
#PSN Default Rating Count
PSN_MODEL_RATING_DEFAULT_COUNT = 0
#PSN Default Age Rating
PSN_DEFAULT_AGE_RATING = 0

###############################################################
#   These elements below are part of the PSN library's JSON   #
###############################################################
#PSN Library Total Results
PSN_JSON_ELEM_TOTAL_RESULTS = 'total_results'
#PSN Each Game JSON element
PSN_JSON_ELEM_EACH_GAME = 'links'
#PSN Sub-Base Game JSON element i.e. bundles etc.
PSN_JSON_ELEM_SUB_GAME = 'parent_name'
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
#PSN Game Image large thumb
PSN_JSON_ELEM_GAME_IMGTYPE_THUMB_LRG = 1
#PSN Game Image small thumb
PSN_JSON_ELEM_GAME_IMGTYPE_THUMB_SML = 2
#PSN Main Game details block - This element is part of both the library and game JSON!
PSN_JSON_ELEM_GAME_PRICE_BLOCK = 'default_sku'

####################################################################
#   These elements below are part of each individual game's JSON   #
####################################################################
# Element - The price of the game before discounts are applied
PSN_JSON_ELEM_GAME_PRICE = 'price'
# Parent Element - Block that contains the details of any discounts
PSN_JSON_ELEM_GAME_REWARDS = 'rewards'
# Element - The discount on the game for non-PSPlus members
PSN_JSON_ELEM_GAME_BASE_DISCOUNT = 'discount'
# Element - The price of the game after applying discount for non-PSPlus members
PSN_JSON_ELEM_GAME_BASE_PRICE = 'price'
# Element - The discount on the game for PSPlus members
PSN_JSON_ELEM_GAME_BONUS_DISCOUNT = 'bonus_discount'
# Element - The price of the game after applying discount for PSPlus members
PSN_JSON_ELEM_GAME_BONUS_PRICE = 'bonus_price'

# Parent Element - Block that contains all rating info
PSN_JSON_ELEM_GAME_RATING_BLOCK = 'star_rating'
# Element - The rating for this game
PSN_JSON_ELEM_GAME_RATING_VALUE = 'score'
# Element - The number of rating votes this game has recieved
PSN_JSON_ELEM_GAME_RATING_COUNT = 'total'

# Element - The age limit of this game
PSN_JSON_ELEM_GAME_AGERATING = 'age_limit'

# Parent Element - Block that contains list of content descriptors
PSN_JSON_ELEM_EACH_GAME_CONTENT = 'content_descriptors'
# Element - Name of content e.g. Language
PSN_JSON_ELEM_GAME_CONTENT_NAME = 'name'
# Element - Description of content e.g. Language
PSN_JSON_ELEM_GAME_CONTENT_DESCR = 'description'


class PSNLibrary(GenericLibrary):

    def upload_thumbnails_to_cloudinary(self, p_library_id):
        count = 0

        # Get the Library Object from the DB
        library_obj = super().get_library_obj(p_library_id)

        # Get all games from the DB
        all_games_objs = super().get_all_game_objs(library_obj)

        for each_game_obj in all_games_objs:
            print("Game: ", each_game_obj.game_name)
            upload_result = cloudinary.uploader.upload(each_game_obj.image_url)
            print(upload_result)
            each_game_obj.image_datastore_url = upload_result['url']
            image_file = urlopen(each_game_obj.image_url)
            super().update_game_obj(each_game_obj)

            count = count + 1
            if(count == 1):
                break

    # This is temporary migration function for migrating thumbnail data into the db
    def update_psn_game_thumbnails(self, p_library_id):
        count = 0

        # Get the Library Object from the DB
        library_obj = super().get_library_obj(p_library_id)

        # Get the Library JSON
        try:
            psn_lib_json = self.request_psn_lib_json(library_obj)
        except Exception as e:
            traceback.print_exc()
            return

        for eachGame in psn_lib_json[PSN_JSON_ELEM_EACH_GAME]:
            try:
                if(self.game_is_valid(eachGame)):
                    print(eachGame[PSN_JSON_ELEM_GAME_NAME])
                    game_obj = super().get_game_obj(library_obj, eachGame[PSN_JSON_ELEM_GAME_ID])

                    #count = count + 1
                    #if(count == 6):
                    #    break

                    if(game_obj == None):
                        continue
                    else:
                        print("Found ", game_obj.game_name)
                        game_obj.image_url = self.get_psn_thumbnail(eachGame[PSN_JSON_ELEM_GAME_IMAGES])
                        game_obj.image_data = self.get_psn_thumbnail_as_base64_str(game_obj.image_url)
                        super().update_game_obj(game_obj)

                    # Sleep for short time to space our requests to the PSN API.
                    #time.sleep(2)
            except Exception as e:
                # The PSN store has some inconsistencies. When I've seen KeyErrors for the PSN_JSON_ELEM_GAME_PRICE_BLOCK element
                # its been because a game was still listed in the store for pre-order after it already came out. So ignore these.
                if(PSN_JSON_ELEM_GAME_PRICE_BLOCK not in str(e)):
                    print("Exception processing game: ", eachGame[PSN_JSON_ELEM_GAME_NAME])
                    traceback.print_exc()

    # This is used for applying updates to the rating weighting algorithm
    def update_psn_weighted_ratings(self, p_library_id):
        # Get the Library Object from the DB
        library_obj = super().get_library_obj(p_library_id)

        # Get all games from the DB
        all_games_objs = super().get_all_game_objs(library_obj)

        for each_game_obj in all_games_objs:
            print("Game: ", each_game_obj.game_name)
            each_game_obj.weighted_rating = super().apply_weighted_game_rating(library_obj, each_game_obj)
            self.set_psn_game_value(each_game_obj)
            super().update_game_obj(each_game_obj)

    def update_psn_lib(self, p_library_id):
        count = 0
        # Get the Library Object from the DB
        library_obj = super().get_library_obj(p_library_id)

        # Get the Library JSON
        try:
            psn_lib_json = self.request_psn_lib_json(library_obj)
        except Exception as e:
            traceback.print_exc()
            return

        for eachGame in psn_lib_json[PSN_JSON_ELEM_EACH_GAME]:
            try:
                if(self.game_is_valid(eachGame)):
                    print(eachGame[PSN_JSON_ELEM_GAME_NAME])
                    game_obj = super().get_game_obj(library_obj, eachGame[PSN_JSON_ELEM_GAME_ID])

                    #count = count + 1
                    #if(count == 6):
                    #    break
                    #

                    # If this game doesn't exist in the DB yet, add a skeleton record and update below.
                    if(game_obj == None):
                        self.add_psn_game(library_obj, eachGame)
                    else:
                        self.update_psn_game(library_obj, game_obj)

                    # Sleep for short time to space our requests to the PSN API.
                    time.sleep(2)

            except Exception as e:
                # The PSN store has some inconsistencies. When I've seen KeyErrors for the PSN_JSON_ELEM_GAME_PRICE_BLOCK element
                # its been because a game was still listed in the store for pre-order after it already came out. So ignore these.
                if(PSN_JSON_ELEM_GAME_PRICE_BLOCK not in str(e)):
                    print("Exception processing game: ", eachGame[PSN_JSON_ELEM_GAME_NAME])
                    traceback.print_exc()

        # Update Library statistics, such as std dev, for rating weighting
        super().update_library_statistics(library_obj)

    @transaction.atomic
    def add_psn_game(self, p_library_obj, p_base_game_json):
        game_obj = self.add_skeleton_psn_game_record(p_library_obj, p_base_game_json)
        self.update_psn_game(p_library_obj, game_obj)

    def add_skeleton_psn_game_record(self, p_library_obj, p_base_game_json):
        g_id = p_base_game_json[PSN_JSON_ELEM_GAME_ID]
        g_name = p_base_game_json[PSN_JSON_ELEM_GAME_NAME]
        g_url = p_base_game_json[PSN_JSON_ELEM_GAME_URL]
        g_thumb = self.get_psn_thumbnail(p_base_game_json[PSN_JSON_ELEM_GAME_IMAGES])
        g_thumb_b64 = self.get_psn_thumbnail_as_base64_str(g_thumb)
        g_age = PSN_DEFAULT_AGE_RATING #TODO, set this correctly...
        return super().add_skeleton_game_list_entry_to_db(g_id, g_name, g_url, g_thumb, g_thumb_b64, g_age, p_library_obj)

    @transaction.atomic
    def update_psn_game(self, p_library_obj, p_game_obj):
        full_details_json = self.request_psn_game_json(p_game_obj)
        # Set the game content
        self.set_psn_game_content(p_game_obj, full_details_json)
        # Set the price
        self.set_psn_game_price(p_game_obj, full_details_json)
        # Set the ratings (both new ratings in psn and updated weighting)
        self.set_psn_game_ratings(p_library_obj, p_game_obj, full_details_json[PSN_JSON_ELEM_GAME_RATING_BLOCK])
        # Set the game value
        self.set_psn_game_value(p_game_obj)
        # Update the game object in the DB
        super().update_game_obj(p_game_obj)

    def set_psn_game_content(self, p_game_obj, p_game_full_details_json):
        # Check if there is a content descriptors json block
        if (PSN_JSON_ELEM_EACH_GAME_CONTENT in p_game_full_details_json) and (p_game_full_details_json[PSN_JSON_ELEM_EACH_GAME_CONTENT]):
            for eachContentDescr in p_game_full_details_json[PSN_JSON_ELEM_EACH_GAME_CONTENT]:
                #print(eachContentDescr[PSN_JSON_ELEM_GAME_CONTENT_NAME])
                content_descriptor = super().get_or_create_content_descriptor(eachContentDescr[PSN_JSON_ELEM_GAME_CONTENT_NAME], eachContentDescr[PSN_JSON_ELEM_GAME_CONTENT_DESCR])
                super().get_or_create_game_content(p_game_obj, content_descriptor)

    def set_psn_game_price(self, p_game_obj, p_game_full_details_json):
        # Set the standard price of the game
        p_game_obj.price = p_game_full_details_json[PSN_JSON_ELEM_GAME_PRICE_BLOCK][PSN_JSON_ELEM_GAME_PRICE]
        # Now set any discount rates and prices
        g_discount_dtls_tuple = self.get_psn_game_discounts(p_game_full_details_json[PSN_JSON_ELEM_GAME_PRICE_BLOCK])
        p_game_obj.base_discount = g_discount_dtls_tuple.rates.base
        p_game_obj.plus_discount = g_discount_dtls_tuple.rates.plus
        p_game_obj.base_price = g_discount_dtls_tuple.prices.base
        p_game_obj.plus_price = g_discount_dtls_tuple.prices.plus

    def set_psn_game_ratings(self, p_library_obj, p_game_obj, p_game_rating_block_json):
        p_game_obj.rating = p_game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_VALUE] if p_game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_VALUE] else PSN_MODEL_RATING_DEFAULT_VALUE
        p_game_obj.rating_count = p_game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_COUNT] if p_game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_COUNT] else PSN_MODEL_RATING_DEFAULT_COUNT
        p_game_obj.weighted_rating = super().apply_weighted_game_rating(p_library_obj, p_game_obj)

    def set_psn_game_value(self, p_game_obj):
        p_game_obj.base_value_score = super().calculate_game_value(p_game_obj, False)
        p_game_obj.plus_value_score = super().calculate_game_value(p_game_obj, True)

    def get_psn_game_discounts(self, p_game_price_block_json):
        psn_discount_dtls = collections.namedtuple('psn_discount_dtls', ['rates', 'prices'])
        psn_discount_rates = collections.namedtuple('psn_discount_rates', ['base', 'plus'])
        psn_discount_prices = collections.namedtuple('psn_discount_prices', ['base', 'plus'])
        base_discount = 0
        plus_discount = 0

        # Use the standard price as default, and only overwrite if there are discounts.
        base_price = p_game_price_block_json[PSN_JSON_ELEM_GAME_PRICE]
        plus_price = p_game_price_block_json[PSN_JSON_ELEM_GAME_PRICE]

        # Check if there is a discount json block
        if (PSN_JSON_ELEM_GAME_REWARDS in p_game_price_block_json) and (p_game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS]):
            # Check for discounts that apply to PS and non-PS Plus members
            if PSN_JSON_ELEM_GAME_BASE_DISCOUNT in p_game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0]:
                base_discount = p_game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0][PSN_JSON_ELEM_GAME_BASE_DISCOUNT]
                base_price = p_game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0][PSN_JSON_ELEM_GAME_BASE_PRICE]
                plus_discount = base_discount
                plus_price = base_price
            # Now check for discounts that apply only to PS Plus members
            if PSN_JSON_ELEM_GAME_BONUS_DISCOUNT in p_game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0]:
                plus_discount = p_game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0][PSN_JSON_ELEM_GAME_BONUS_DISCOUNT]
                plus_price = p_game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0][PSN_JSON_ELEM_GAME_BONUS_PRICE]

        discount_rates_tuple = psn_discount_rates(base=base_discount,plus=plus_discount)
        discount_prices_tuple = psn_discount_prices(base=base_price,plus=plus_price)
        discount_dtls_tuple = psn_discount_dtls(rates=discount_rates_tuple,prices=discount_prices_tuple)
        return discount_dtls_tuple

    def get_psn_thumbnail(self, p_image_list):
        game_thumb = None
        for eachGameImg in p_image_list:
            if eachGameImg[PSN_JSON_ELEM_GAME_IMGTYPE] == PSN_JSON_ELEM_GAME_IMGTYPE_THUMB_SML:
                game_thumb = eachGameImg[PSN_JSON_ELEM_GAME_URL]
                break
        return game_thumb

    def get_psn_thumbnail_as_base64_str(self, p_thumbnail_url):
        image_file = urlopen(p_thumbnail_url)
        return base64.b64encode(image_file.read())

    def game_is_valid(self, p_game_json):
        game_valid = True
        # We're just looking for base games i.e. ignore bundles etc.
        # If a game is on sale, the bundle is (always?) on sale too.
        # Maybe we shouldn't be.... Do some tests on this.
        if PSN_JSON_ELEM_SUB_GAME in p_game_json:
            game_valid = False
        # Check to make sure the game is released - otherwise we can get games without prices etc.
        elif(self.game_is_released(p_game_json) == False):
            game_valid = False

        return game_valid

    def game_is_on_PS4(self, p_platform_list):
        return PSN_JSON_ELEM_GAME_PS4_PFORM in p_platform_list

    def game_is_released(self, p_lib_game_entry):
        g_is_released = False
        g_release_date = datetime.strptime(p_lib_game_entry[PSN_JSON_ELEM_RELEASE_DATE], '%Y-%m-%dT%H:%M:%SZ')
        if(g_release_date < datetime.now()):
            g_is_released = True
        return g_is_released

    def request_psn_lib_json(self, p_library_obj):
        lib_total_results = self.get_psn_lib_total_results(p_library_obj.library_url)
        return self.make_psn_lib_json_api_request(p_library_obj.library_url, lib_total_results)

    def get_psn_lib_total_results(self, p_psn_lib_url):
        response_json = requests.get(p_psn_lib_url+'0')
        print("URL: ", p_psn_lib_url+'1')
        print("Status Code for Game Count request: ", print(response_json.status_code))
        # Sleep for short time to space our requests to the PSN API.
        time.sleep(5)
        psn_lib_json = response_json.json()
        return psn_lib_json[PSN_JSON_ELEM_TOTAL_RESULTS]

    def make_psn_lib_json_api_request(self, p_psn_lib_url, p_count_to_fetch):
        #File for testing only - live version will pull json from psn api
        #with open('staticfiles/psnvalue/TotalPS4GameLibrary.json') as data_file:
        #    psn_lib_json = json.load(data_file)
        response_json = requests.get(p_psn_lib_url+str(p_count_to_fetch))
        print("Status Code for Library List request: ", print(response_json.status_code))
        psn_lib_json = response_json.json()
        return psn_lib_json

    def request_psn_game_json(self, p_game_obj):
        #File for testing only - live version will pull json from psn api
        #with open('staticfiles/psnvalue/DragonAgeInquisition_FullGame.json') as data_file:
        #with open('staticfiles/psnvalue/DarkSoulsIII_FullGame.json') as data_file:
        #    psn_game_json = json.load(data_file)
        response_json = requests.get(p_game_obj.json_url)
        psn_game_json = response_json.json()
        return psn_game_json
