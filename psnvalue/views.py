from django.views import generic
from django.http import HttpResponse
from django.http import Http404

from .models import Library, GameList
from .tasks import user_update_psn_library, user_update_weighted_rating, user_update_game_thumbnails

# Library homepage for admin user.
INDEX_TEMPLATE_ADMIN = 'psnvalue/index_admin.html'
# Library homepage for regular user.
INDEX_TEMPLATE_USER = 'psnvalue/index.html'
# Context object name for library list - used in the HTML.
INDEX_CON = 'library_list'

# Game list template page
GAMELIST_TEMPLATE = 'psnvalue/gamelist.html'
# Context object name for game list - used in the HTML.
GAMELIST_CON = 'game_list'
# The number of games to display on each page of results.
GAMELIST_GAMES_PER_PAGE = 40
# The minimum number of ratings needed by a game to be displayed.
GAMELIST_MIN_RATING_COUNT = 50
# The minimum price of a game to be displayed (used to exclude free to play).
GAMELIST_MIN_PRICE = 1
# The parameter name for the library id to display games for.
GAMELIST_LIBRARY_ID_PARAM = 'library_id'
# The ordering of results for the game list.
GAMELIST_ORDER_BY = '-plus_value_score'

class IndexView(generic.ListView):
    """
    Game library homepage view.

    Displays the list of game libraries and the date of last update for each library. If the admin
    user is logged in, a link will be displayed to allow for a manual update of a library.
    """
    context_object_name = INDEX_CON

    def get_template_names(self):
        """
        Return the game library home page for regular and admin users.
        """
        if self.request.user.is_staff:
            return [INDEX_TEMPLATE_ADMIN]
        else:
            return [INDEX_TEMPLATE_USER]

    def get_queryset(self):
        """
        Get all librarys from the database.
        """
        return Library.objects.all()

class GameListView(generic.ListView):
    """
    Game list view.

    View used for displaying the list of games, and their details, from the library. Results are paginated.
    """
    template_name = GAMELIST_TEMPLATE
    context_object_name = GAMELIST_CON
    paginate_by = GAMELIST_GAMES_PER_PAGE

    def get_queryset(self):
        """
        Get ordered and filtered list of Games.

        Filter games based on library id, count of ratings and price. Order by PS Plus value score.
        """
        return GameList.objects.filter(library_fk=self.kwargs[GAMELIST_LIBRARY_ID_PARAM], rating_count__gte=GAMELIST_MIN_RATING_COUNT, price__gte=GAMELIST_MIN_PRICE).order_by(GAMELIST_ORDER_BY)

def updatelib(request, library_id):
    """
    View used for updating the game library from PSN.

    Uses the PSN API to retrieve games that are absent from the local library and also to
    update games that are in the library with updated info. This update is performed
    asynchronously. Update can only be triggered through this view by an admin user.

    Args:
        request: The HTTP request
        library_id: The ID of the local library to update.
    Returns:
        The HTTP response.
    """
    if not request.user.is_staff:
        raise Http404("You do not have access to this resource.")
    user_update_psn_library.delay(library_id)
    return HttpResponse("You're at the psnvalue updatelib.")

def updateweightedrating(request, library_id):
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
    if not request.user.is_staff:
        raise Http404("You do not have access to this resource.")
    user_update_weighted_rating.delay(library_id)
    return HttpResponse("You're at the psnvalue update weighted rating.")

def updategamethumbs(request, library_id):
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
    if not request.user.is_staff:
        raise Http404("You do not have access to this resource.")
    user_update_game_thumbnails.delay(library_id)
    return HttpResponse("You're at the psnvalue update game thumbs.")
