from .models import Library, GameList, ContentDescriptors, GameContent
from django.utils import timezone

class PSNLibraryDAO:

    def get_library(self, library_id):
        library = None
        try:
            library = Library.objects.get(pk=library_id)
        except Library.DoesNotExist:
            pass
        return library

    def get_game(self, library, game_id):
        game = None
        try:
            game = GameList.objects.get(game_id=game_id, library_fk=library)
        except GameList.DoesNotExist:
            pass
        return game

    def add_skeleton_game_record(self, id, name, url, thumb, thumb_datastore, age, library):
        return GameList.objects.create(game_id=id, game_name=name, json_url=url, image_url=thumb, image_datastore_url=thumb_datastore, age_rating=age, library_fk=library)

    def update_game(self, game):
        game.last_updated = timezone.now()
        game.save()

    def get_or_create_content_descriptor(self, name, description):
        return ContentDescriptors.objects.get_or_create(content_name=name, content_description=description)[0]

    def get_or_create_game_content(self, game, content_descriptor):
        return GameContent.objects.get_or_create(game_id_fk=game, content_descriptor_fk=content_descriptor)[0]

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
            
