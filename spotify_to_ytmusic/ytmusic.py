import os
import re
from collections import OrderedDict

from ytmusicapi import YTMusic

from spotify_to_ytmusic.utils.match import get_best_fit_song_id
from spotify_to_ytmusic.settings import Settings

from concurrent.futures import ThreadPoolExecutor

path = os.path.dirname(os.path.realpath(__file__)) + os.sep


class YTMusicTransfer:
    def __init__(self):
        settings = Settings()
        headers = settings["youtube"]["headers"]
        assert headers.startswith("{"), "ytmusicapi headers not set or invalid"
        self.api = YTMusic(headers, settings["youtube"]["user_id"])

    def create_playlist(self, name, info, privacy="PRIVATE", tracks=None):
        return self.api.create_playlist(name, info, privacy, video_ids=tracks)




    def search_songs(self, tracks):
        videoIds = []
        songs = list(tracks)
        notFound = []
        print("Searching YouTube...")

        # Function to handle results
        def handle_result(result, query):
            if result is None:
                notFound.append(query)
            else:
                videoIds.append(result)
        
        def search_song(api, song):
            name = re.sub(r" \(feat.*\..+\)", "", song["name"])
            query = song["artist"] + " " + name
            query = query.replace(" &", "")
            result = api.search(query)
            print("Searching for: " + query)
            if len(result) == 0:
                return None, query
            else:
                return get_best_fit_song_id(result, song), query

        with ThreadPoolExecutor() as executor:  # You can also use ProcessPoolExecutor for CPU-bound tasks
            futures = [executor.submit(search_song, self.api, song) for song in songs]
            for future in futures:
                result, query = future.result()
                handle_result(result, query)

        with open(path + "noresults_youtube.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(notFound))
            f.write("\n")

        return videoIds

    def add_playlist_items(self, playlistId, videoIds):
        videoIds = OrderedDict.fromkeys(videoIds)
        self.api.add_playlist_items(playlistId, videoIds)

    def get_playlist_id(self, name):
        pl = self.api.get_library_playlists(10000)
        try:
            playlist = next(x for x in pl if x["title"].find(name) != -1)["playlistId"]
            return playlist
        except:
            raise Exception("Playlist title not found in playlists")

    def remove_songs(self, playlistId):
        items = self.api.get_playlist(playlistId, 10000)
        if "tracks" in items:
            self.api.remove_playlist_items(playlistId, items["tracks"])

    def remove_playlists(self, pattern):
        playlists = self.api.get_library_playlists(10000)
        p = re.compile("{0}".format(pattern))
        matches = [pl for pl in playlists if p.match(pl["title"])]
        print("The following playlists will be removed:")
        print("\n".join([pl["title"] for pl in matches]))
        print("Please confirm (y/n):")

        choice = input().lower()
        if choice[:1] == "y":
            [self.api.delete_playlist(pl["playlistId"]) for pl in matches]
            print(str(len(matches)) + " playlists deleted.")
        else:
            print("Aborted. No playlists were deleted.")
