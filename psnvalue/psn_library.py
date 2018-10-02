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
from celery.utils.log import get_task_logger
from .psn_library_dao import PSNLibraryDAO
from requests.packages.urllib3.exceptions import InsecureRequestWarning

#PSN Library Name
PSN_MODEL_LIBRARY_NAME = 'PS4'
#PSN Default Rating Value
PSN_MODEL_RATING_DEFAULT_VALUE = 1
#PSN Default Rating Count
PSN_MODEL_RATING_DEFAULT_COUNT = 0
#PSN Default Age Rating
PSN_DEFAULT_AGE_RATING = 0
#Spacing between library api requests
PSN_API_SPACING_LIB = 5
#Spacing between game api requests
PSN_API_SPACING_GAME = 2

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

    psn_library_dao = PSNLibraryDAO()

    """
    Celery Task - Sync PSN library with PSN Store.
    """
    def sync_library_with_store(self, library_id):
        """
        Syncs the local PSN library with the PSN store.

        Requests the full PSN Store JSON, which contains a list of all games in
        the PSN Store. This JSON is then used to update the local PSN library.

        Args:
            library_id: The ID of the local library to update.
        """
        # Get the PSN Library from the DB
        psn_library = self.psn_library_dao.get_library(library_id)

        if(psn_library != None):
            try:
                # Get the PSN Store JSON
                psn_lib_json = self.request_psn_lib_json(psn_library.library_url)

                # Update the PSN library with the PSN Store JSON
                self.update_psn_library(psn_library, psn_lib_json)

            except Exception as e:
                traceback.print_exc()

    def update_psn_library(self, library, library_json):
        """
        Update the PSN Library using the PSN Store JSON.

        The PSN Store JSON contains a list of all games. Each game entry contains a url
        to the full details for that game. The details at this url are used to add new
        games to the PSN library, or update games already contained within it.

        Args:
            library: The PSN library object from the DB.
            library_json: The full library JSON returned by the PSN Store API.
        """
        count = 0 # TODO remove
        for simple_game_json in library_json[PSN_JSON_ELEM_EACH_GAME]:
            try:
                if(self.game_is_valid(simple_game_json)):

                    if(count >= 5): # TODO remove
                        break
                    count += 1

                    print(simple_game_json[PSN_JSON_ELEM_GAME_NAME])
                    detailed_game_json_url = simple_game_json[PSN_JSON_ELEM_GAME_URL]
                    detailed_game_json = self.request_psn_game_json(detailed_game_json_url)
                    game = self.psn_library_dao.get_game(library, detailed_game_json[PSN_JSON_ELEM_GAME_ID])

                    if(game == None):
                        self.add_game(library, detailed_game_json, detailed_game_json_url)
                    else:
                        self.update_game(library, detailed_game_json, game)

                    # Sleep for short time to space our requests to the PSN API.
                    time.sleep(PSN_API_SPACING_GAME)

            except Exception as e:
                # The PSN store has some inconsistencies. When I've seen KeyErrors for the PSN_JSON_ELEM_GAME_PRICE_BLOCK element
                # its been because a game was still listed in the store for pre-order after it already came out. So ignore these.
                if(PSN_JSON_ELEM_GAME_PRICE_BLOCK not in str(e)):
                    print("Exception processing game: ", simple_game_json[PSN_JSON_ELEM_GAME_NAME])
                    traceback.print_exc()

        # Update Library statistics, such as std dev, for rating weighting
        super().update_library_statistics(library)

    @transaction.atomic
    def add_game(self, library, detailed_game_json, detailed_game_json_url):
        """
        Add a new game to the PSN Library.

        First add a skeleton record with basic (unchanging) game info to the DB. Then add game
        content records for this game (these are also unchanging). Finally, send the skeleton
        record to the update method to add all of the variable game data e.g. price, rating etc.

        This operation is an atomic transaction.

        Args:
            library: The PSN library object from the DB.
            detailed_game_json: The full detailed game info JSON.
            detailed_game_json_url: The url contained in the library JSON
                                    that returns the detailed game json.
        """
        game = self.add_skeleton_game_record(library, detailed_game_json, detailed_game_json_url)
        self.set_psn_game_content(game, detailed_game_json)
        self.update_game(library, detailed_game_json, game)

    def add_skeleton_game_record(self, library, detailed_game_json, detailed_game_json_url):
        """
        Add a skeleton record with basic (unchanging) game info to the DB.

        Args:
            library: The PSN library object from the DB.
            detailed_game_json: The full detailed game info JSON.
            detailed_game_json_url: The url contained in the library JSON
                                    that returns the detailed game json.
        """
        url = detailed_game_json_url
        id = detailed_game_json[PSN_JSON_ELEM_GAME_ID]
        name = detailed_game_json[PSN_JSON_ELEM_GAME_NAME]
        thumb = self.get_psn_thumbnail(detailed_game_json[PSN_JSON_ELEM_GAME_IMAGES])
        thumb_datastore = self.upload_thumb_to_cloudinary(thumb)
        age = detailed_game_json[PSN_JSON_ELEM_GAME_AGERATING]
        return self.psn_library_dao.add_skeleton_game_record(id, name, url, thumb, thumb_datastore, age, library)

    def set_psn_game_content(self, game, detailed_game_json):
        """
        Set the content descriptors for the game.

        Content descriptors are not mandatory for a game. Some examples are 'Online', 'Drugs', 'Violence' etc.

        Args:
            game: The game in the PSN library to add content descriptors for.
            detailed_game_json: The full detailed game info JSON.
        """
        # Check if there is a content descriptors json block
        if (PSN_JSON_ELEM_EACH_GAME_CONTENT in detailed_game_json) and (detailed_game_json[PSN_JSON_ELEM_EACH_GAME_CONTENT]):
            for eachContentDescr in detailed_game_json[PSN_JSON_ELEM_EACH_GAME_CONTENT]:
                content_descriptor = self.psn_library_dao.get_or_create_content_descriptor(eachContentDescr[PSN_JSON_ELEM_GAME_CONTENT_NAME], eachContentDescr[PSN_JSON_ELEM_GAME_CONTENT_DESCR])
                self.psn_library_dao.get_or_create_game_content(game, content_descriptor)

    @transaction.atomic
    def update_game(self, library, detailed_game_json, game):
        """
        Update a game's details in the PSN library.

        Variable data, such as price, ratings and the resulting value, is updated with
        data from the PSN store.

        This operation is an atomic transaction.

        Args:
            library: The PSN library object from the DB.
            detailed_game_json: The full detailed game info JSON.
            game: The game in the PSN libray to update.
        """
        # Set the price
        self.set_psn_game_price(game, detailed_game_json)
        # Set the ratings (both new ratings in psn and updated weighting)
        self.set_psn_game_ratings(library, game, detailed_game_json[PSN_JSON_ELEM_GAME_RATING_BLOCK])
        # Set the game value
        self.set_psn_game_value(library, game)
        # Update the game object in the DB
        self.psn_library_dao.update_game(game)

    def set_psn_game_price(self, game, detailed_game_json):
        """
        Set the price details for a game in the PSN library

        Args:
            game: The game to set price details for.
            detailed_game_json: The full detailed game info JSON.
        """
        game.price = detailed_game_json[PSN_JSON_ELEM_GAME_PRICE_BLOCK][PSN_JSON_ELEM_GAME_PRICE]
        discount_dtls_tuple = self.get_psn_game_discounts(detailed_game_json[PSN_JSON_ELEM_GAME_PRICE_BLOCK])
        game.base_discount = discount_dtls_tuple.rates.base
        game.plus_discount = discount_dtls_tuple.rates.plus
        game.base_price = discount_dtls_tuple.prices.base
        game.plus_price = discount_dtls_tuple.prices.plus

    def set_psn_game_ratings(self, library, game, game_rating_block_json):
        """
        Set the ratings details for a game in the PSN library.

        These ratings include both the ratings info from the PSN store, and also
        a weighted rating based on global statistics for the PSN library.

        Args:
            library: The PSN library object from the DB.
            game: The game to set ratings details for.
            game_rating_block_json: The block of JSON containing the ratings data.
        """
        game.rating = game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_VALUE] if game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_VALUE] else PSN_MODEL_RATING_DEFAULT_VALUE
        game.rating_count = game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_COUNT] if game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_COUNT] else PSN_MODEL_RATING_DEFAULT_COUNT
        game.weighted_rating = self.apply_weighted_game_rating(library, game)

    def set_psn_game_value(self, library, game):
        game.base_value_score = self.calculate_game_value(library, game, False)
        game.plus_value_score = self.calculate_game_value(library, game, True)

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

    def upload_thumb_to_cloudinary(self, p_thumbnail_url):
        upload_result = cloudinary.uploader.upload(p_thumbnail_url)
        return upload_result['url']

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

    """
    PSN Library Statistics
    """
    # DEFAULT_GAME_PRICE - anything less than one causes division by zero errors
    DEFAULT_GAME_PRICE = 1
    DEFAULT_GAME_WEIGHTED_RATING = 1

    # Apply a weight based on the rating deviation from the mean and the count of ratings.
    def apply_weighted_game_rating(self, library, game):
        # Determine if this game is above or below the mean rating. Necessary for applying different weighting algorithm.
        aboveMean = self.rating_above_mean(library, game)

        # Determine the weight to apply to rating count.
        countVal = (float(game.rating_count)/125)

        # Determine weighting to apply based on rating deviation from the mean.
        ratingConstant = 1 if aboveMean else -1
        ratingVal = round((float(game.rating)) * (ratingConstant+((float(game.rating) - library.library_rating_mean)/library.library_rating_stdev)),2)

        # Apply different weights depending if the game rating is above or below mean.
        finalVal = 0
        if(aboveMean):
            finalVal = (ratingVal+countVal)
        else:
            finalVal = (ratingVal-countVal)

        # Account for a weighted rating of zero
        return self.DEFAULT_GAME_WEIGHTED_RATING if finalVal == 0.0 else finalVal

    # Calculate value based on the price and discount relative to the weighted rating.
    def calculate_game_value(self, library, p_game_obj, p_plus):
        game_price = 0.0
        game_rating = 0.0
        discount_weight = 0.0

        # Determine the final price, accounting for free games
        if(p_plus == True):
            game_price = p_game_obj.plus_price
        else:
            game_price = p_game_obj.base_price

        game_price = round(game_price if game_price > 0.0 else self.DEFAULT_GAME_PRICE)

        # Determine the weight to apply to the discount.
        if(p_plus == True):
            discount_weight = 1+(p_game_obj.plus_discount/100)
        else:
            discount_weight = 1+(p_game_obj.base_discount/100)

        # Apply the discount weight to the weighted rating.
        if(self.rating_above_mean(library, p_game_obj)):
            game_rating = ((p_game_obj.weighted_rating)*discount_weight)*100
        else:
            game_rating = ((p_game_obj.weighted_rating)/discount_weight)*100

        return round(1/(game_price/game_rating)*100)

    def rating_above_mean(self, library, p_game_obj):
        return (((float(p_game_obj.rating) - library.library_rating_mean)/library.library_rating_stdev) > 0)

    """
    PSN API Requests
    """
    def request_psn_lib_json(self, p_library_url):
        lib_total_results = self.get_psn_lib_total_results(p_library_url)
        return self.make_psn_lib_json_api_request(p_library_url, lib_total_results)

    def get_psn_lib_total_results(self, p_psn_lib_url):
        response_json = requests.get(p_psn_lib_url+'0')
        print("URL: ", p_psn_lib_url+'1')
        print("Status Code for Game Count request: ", print(response_json.status_code))
        # Sleep for short time to space our requests to the PSN API.
        time.sleep(PSN_API_SPACING_LIB)
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

    def request_psn_game_json(self, detailed_game_json_url):
        response_json = requests.get(detailed_game_json_url)
        psn_game_json = response_json.json()
        return psn_game_json

    """
    Celery Task - Update Thumbnails
    """
    def upload_thumbnails_to_cloudinary(self, p_library_id):
        """
        View used for updating the stored game thumbnails.

        Each game in the library is iterated over and the game thumbnail is retrieved using the thumbnail
        URL stored in the DB. The image at this URL is then stored in the library storage. This update is
        performed asynchronously. Update can only be triggered through this view by an admin user.

        Args:
            request: The HTTP request
            library_id: The ID of the local libray whose games we want to update.
        Returns:
            The HTTP response.
        """
        count = 0

        # Get the Library Object from the DB
        library_obj = super().get_library_obj(p_library_id)

        # Get all games from the DB
        all_games_objs = super().get_all_game_objs(library_obj)

        for each_game_obj in all_games_objs:
            print("Game: ", each_game_obj.game_name)
            each_game_obj.image_datastore_url = self.upload_thumb_to_cloudinary(each_game_obj.image_url)
            super().update_game_obj(each_game_obj)

    """
    Celery Task - Update Weighted Ratings
    """
    def update_weighted_ratings(self, library_id):
        """
        View used for updating the weighted rating for each game in the library.

        Each game in the library is iterated over and the weighted rating of the game, and its
        corresponding value are calculated and updated in the DB. This allows for changes in the
        value formula to be applied quickly. This update is performed asynchronously. Update can
        only be triggered through this view by an admin user.

        Args:
            request: The HTTP request
            library_id: The ID of the local libray whose games we want to update.
        Returns:
            The HTTP response.
        """
        # Get the Library Object from the DB
        psn_library = self.psn_library_dao.get_library(library_id)

        # Get all games from the DB
        all_games = super().get_all_game_objs(psn_library)

        for each_game in all_games:
            print("Game: ", each_game.game_name)
            each_game.weighted_rating = self.apply_weighted_game_rating(psn_library, each_game)
            self.set_psn_game_value(psn_library, each_game)
            self.psn_library_dao.update_game(each_game)
