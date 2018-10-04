import requests
import time

# Spacing between library api requests
PSN_API_SPACING_LIB = 5
# Spacing between game api requests
PSN_API_SPACING_GAME = 2
# This controls the returning of game JSON during our request for the count of games.
PSN_API_COUNT_OF_GAMES_URL_SUFFIX = '0'
#PSN Library Total Results
PSN_JSON_ELEM_TOTAL_RESULTS = 'total_results'

class PSNStoreAPI:
    """
    Library Requests
    """
    def request_psn_lib_json(self, library_url):
        """
        Request the JSON detailing the contents of the PSN Store.

        This JSON contain basic game data with a link to the detailed game JSON. A request is first
        made to the store to find out how many games are in the store. Then, after a short sleep,
        a second request is made to the store requesting the JSON for that count of games.

        Args:
            library_url: The URL for the PSN Store JSON.
        Returns:
            JSON: JSON containing the basic details of all games in the PSN Store.
        """
        lib_total_results = self.get_psn_lib_total_results(library_url)
        time.sleep(PSN_API_SPACING_LIB)
        return self.make_psn_lib_json_api_request(library_url, lib_total_results)

    def get_psn_lib_total_results(self, library_url):
        """
        Get the count of games in the PSN Store.

        This is done by requesting 0 games from the store. In the resulting JSON, the total
        count of available games is detailed.

        Args:
            library_url: The URL for the PSN Store JSON.
        Returns:
            number: The count of games in the store.
        """
        request_url = library_url+PSN_API_COUNT_OF_GAMES_URL_SUFFIX
        print("URL: ", request_url)
        response_json = requests.get(request_url)
        print("Status Code for Game Count request: ", print(response_json.status_code))
        psn_lib_json = response_json.json()
        return psn_lib_json[PSN_JSON_ELEM_TOTAL_RESULTS]

    def make_psn_lib_json_api_request(self, library_url, count_to_fetch):
        """
        Get the basic game details for a specified number of games in the PSN store.

        Args:
            library_url: The URL for the PSN Store JSON.
            count_to_fetch: The count of games to fetch from the store.
        Returns:
            JSON: JSON containing the basic details of the specified number of games in the PSN Store.
        """
        request_url = library_url+str(count_to_fetch)
        print("URL: ", request_url)
        response_json = requests.get(request_url)
        print("Status Code for Library List request: ", print(response_json.status_code))
        return response_json.json()

    """
    Game Requests
    """
    def request_psn_game_json(self, detailed_game_json_url):
        """
        Get the detailed JSON for a game in the PSN Store.

        Sleep after this request to ensure requests are spaced out.

        Args:
            detailed_game_json_url: The URL for the detailed game JSON.
        Return:
            JSON: The detailed game JSON.
        """
        response_json = requests.get(detailed_game_json_url)
        time.sleep(PSN_API_SPACING_GAME)
        psn_game_json = response_json.json()
        return psn_game_json
