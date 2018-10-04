from statistics import pstdev, mean
from .models import Library, GameList, ContentDescriptors, GameContent
from django.utils import timezone

GAME_RATING_FIELD_NAME = 'rating'

class PSNLibraryDAO:

    def get_library(self, library_id):
        """
        Get a specific PSN library from the DB.

        Args:
            library_id: The ID of the library to fetch.
        Returns:
            Library: The Library if found, else None.
        """
        library = None
        try:
            library = Library.objects.get(pk=library_id)
        except Library.DoesNotExist:
            pass
        return library

    def get_game(self, library, game_id):
        """
        Get a specific game from the DB for a specific Library.

        Args:
            library: A specific library from the DB.
            game_id: The ID of the game to fetch from the specified library.
        Return:
            GameList: The Game if found, else None.
        """
        game = None
        try:
            game = GameList.objects.get(game_id=game_id, library_fk=library)
        except GameList.DoesNotExist:
            pass
        return game

    def get_all_games(self):
        """
        Get all games from the DB.

        Returns:
            QuerySet: A copy of the current QuerySet containing all games from the DB.
        """
        return GameList.objects.all()

    def add_skeleton_game_record(self, id, name, json_url, thumb_url, thumb_datastore_url, age, library):
        """
        Add a new game record to the DB with some basic information.

        Args:
            id: The PSN Store ID for the game.
            name: The PSN Store name for the game.
            json_url: The URL for the detailed game JSON in the PSN Store.
            thumb_url: The URL for the game's thumbnail in the PSN Store.
            thumb_datastore_url: The URL for the game's thumbnail in the PSN Library's image datastore.
            age: The age rating of the game.
            library: The PSN Library that this game belongs to.
        Return:
            GameList: The newly created Game.
        """
        return GameList.objects.create(game_id=id, game_name=name, json_url=json_url, image_url=thumb_url, image_datastore_url=thumb_datastore_url, age_rating=age, library_fk=library)

    def update_game(self, game):
        """
        Update a Game record in the DB.

        Args:
            game: The Game object with updated info.
        """
        game.last_updated = timezone.now()
        game.save()

    def get_or_create_content_descriptor(self, name, description):
        """
        Get the Content Descriptor for the specified name and description from the DB if it exists, else create it.

        Args:
            name: The name of the Content Descriptor
            description: The description of the Content Descriptor.
        Returns:
            ContentDescriptors: The newly created or fetched Content Descriptor.
        """
        return ContentDescriptors.objects.get_or_create(content_name=name, content_description=description)[0]

    def get_or_create_game_content(self, game, content_descriptor):
        """
        Get the Game Content for the specified Game and Content Descriptor from the DB if it exists, else create it.

        Args:
            game: The Game to add Game Content for.
            content_descriptor: The Content Descriptor for this Game Content.
        Returns:
            GameContent: The newly created or fetched Game Content.
        """
        return GameContent.objects.get_or_create(game_id_fk=game, content_descriptor_fk=content_descriptor)[0]

    def update_library_statistics(self, library):
        """
        Update the library statistics for a specified library.

        Library statistic are the mean rating in the library, the standard
        deviation from the mean and the datetime of the last update.

        Args:
            library: The Library to update statistics for.
        """
        list_of_game_ratings = self.get_all_game_ratings_in_library(library)
        library.library_rating_stdev = pstdev(list_of_game_ratings)
        library.library_rating_mean = mean(list_of_game_ratings)
        library.last_updated = timezone.now()
        library.save()

    def get_all_game_ratings_in_library(self, library):
        """
        Get a list of all the game ratings in a library.

        Used for calculation of library statistics.

        Args:
            library: The Library to get all game ratings for.
        Return
            ValueList: List of all game ratings in the library.
        """
        return GameList.objects.filter(library_fk=library).values_list(GAME_RATING_FIELD_NAME, flat=True)
