"""Calls made by the web client."""

import copy
import json
import sys

import validictory

from gmusicapi.exceptions import CallFailure, ValidationException
from gmusicapi.protocol import MetadataExpectations  # TODO migrate
from gmusicapi.newprotocol.shared import Call
from gmusicapi.utils import utils

base_url = 'https://play.google.com/music/'
service_url = base_url + 'services/'

#Shared response schemas, built to include metadata expectations.
song_schema = {
    "type": "object",
    "properties": {
        name: expt.get_schema() for
        name, expt in MetadataExpectations.get_all_expectations().items()
    },
    #don't allow metadata not in expectations
    "additionalProperties": False
}

song_array = {
    "type": "array",
    "items": song_schema
}

pl_schema = {
    "type": "object",
    "properties": {
        "continuation": {"type": "boolean"},
        "playlist": song_array,
        "playlistId": {"type": "string"},
        "unavailableTrackCount": {"type": "integer"},
        #only appears when loading multiple playlists
        "title": {"type": "string", "required": False},
        "continuationToken": {"type": "string", "required": False}
    },
    "additionalProperties": False
}

pl_array = {
    "type": "array",
    "items": pl_schema
}


class WcCall(Call):
    """Abstract base for web client calls."""

    send_xt = True
    send_sso = True

    #validictory schema for the response
    _res_schema = utils.NotImplementedField

    @classmethod
    def validate(cls, res):
        """Use validictory and a static schema (stored in cls._res_schema)."""
        try:
            return validictory.validate(res, cls._res_schema)
        except ValueError as e:
            trace = sys.exc_info()[2]
            raise ValidationException(str(e)), None, trace

    @classmethod
    def check_success(cls, res):
        #Failed responses always have a success=False key.
        #Some successful responses do not have a success=True key, however.
        #TODO remove utils.call_succeeded

        if 'success' in res and not res['success']:
            raise CallFailure(
                "the server reported failure. This is usually"
                "caused by bad arguments, but can also happen if requests"
                "are made too quickly (eg creating a playlist then"
                "modifying it before the server has created it)",
                cls.__name__)

    @classmethod
    def parse_response(cls, text):
        return cls._parse_json(text)


class AddPlaylist(WcCall):
    """Creates a new playlist."""

    static_method = 'POST'
    static_url = service_url + 'addplaylist'

    _res_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "title": {"type": "string"},
            "success": {"type": "boolean"},
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(title):
        """
        :param title: the title of the playlist to create.
        """
        return {'json': json.dumps({"title": title})}


class AddToPlaylist(WcCall):
    """Adds songs to a playlist."""
    static_method = 'POST'
    static_url = service_url + 'addtoplaylist'

    _res_schema = {
        "type": "object",
        "properties": {
            "playlistId": {"type": "string"},
            "songIds": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "songId": {"type": "string"},
                        "playlistEntryId": {"type": "string"}
                    }
                }
            }
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(playlist_id, song_ids):
        """
        :param playlist_id: id of the playlist to add to.
        :param song_ids: a list of song ids
        """
        #TODO unsure what type means here. Likely involves uploaded vs store/free.
        song_refs = [{'id': sid, 'type': 1} for sid in song_ids]

        return {
            'json': json.dumps(
                {"playlistId": playlist_id, "songRefs": song_refs}
            )
        }


class ChangePlaylistName(WcCall):
    """Changes the name of a playlist."""

    static_method = 'POST'
    static_url = service_url + 'modifyplaylist'

    _res_schema = {
        "type": "object",
        "properties": {},
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(playlist_id, new_name):
        """
        :param playlist_id: id of the playlist to rename.
        :param new_title: desired title.
        """
        return {
            'json': json.dumps(
                {"playlistId": playlist_id, "playlistName": new_name}
            )
        }


class ChangePlaylistOrder(WcCall):
    """Reorder existing tracks in a playlist."""

    static_method = 'POST'
    static_url = service_url + 'changeplaylistorder'

    _res_schema = {
        "type": "object",
        "properties": {
            "afterEntryId": {"type": "string", "blank": True},
            "playlistId": {"type": "string"},
            "movedSongIds": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(playlist_id, song_ids_moving, entry_ids_moving,
                     after_entry_id=None, before_entry_id=None):
        """
        :param playlist_id: id of the playlist getting reordered.
        :param song_ids_moving: a list of consecutive song ids. Matches entry_ids_moving.
        :param entry_ids_moving: a list of consecutive entry ids to move. Matches song_ids_moving.
        :param after_entry_id: the entry id to place these songs after. Default first position.
        :param before_entry_id: the entry id to place these songs before. Default last position.
        """

        # empty string means first/last position
        if after_entry_id is None:
            after_entry_id = ""
        if before_entry_id is None:
            before_entry_id = ""

        return {
            'json': json.dumps(
                {
                    "playlistId": playlist_id,
                    "movedSongIds": song_ids_moving,
                    "movedEntryIds": entry_ids_moving,
                    "afterEntryId": after_entry_id,
                    "beforeEntryId": before_entry_id
                }
            )
        }


class DeletePlaylist(WcCall):
    """Delete a playlist."""

    static_method = 'POST'
    static_url = service_url + 'deleteplaylist'

    _res_schema = {
        "type": "object",
        "properties": {
            "deleteId": {"type": "string"}
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(playlist_id):
        """
        :param playlist_id: id of the playlist to delete.
        """
        return {
            'json': json.dumps(
                {"id": playlist_id}
            )
        }


class DeleteSongs(WcCall):
    """Delete a song from the entire library or a single playlist."""

    static_method = 'POST'
    static_url = service_url + 'deletesong'

    _res_schema = {
        "type": "object",
        "properties": {
            "listId": {"type": "string"},
            "deleteIds":
            {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "additionalProperties": False
    }

    @staticmethod
    def dynamic_data(song_ids, playlist_id='all', entry_ids=None):
        """
        :param song_ids: a list of song ids.
        :param playlist_id: playlist id to delete from, or 'all' for deleting from library.
        :param entry_ids: when deleting from playlists, corresponding list of entry ids.
        """

        return {
            'json': json.dumps(
                {"songIds": song_ids, "entryIds": entry_ids, "listId": playlist_id}
            )
        }


class GetLibrarySongs(WcCall):
    """Loads tracks from the library.
    Since libraries can have many tracks, GM gives them back in chunks.
    Chunks will send a continuation token to get the next chunk.
    The first request needs no continuation token.
    The last response will not send a token.
    """

    static_method = 'POST'
    static_url = service_url + 'loadalltracks'

    _res_schema = {
        "type": "object",
        "properties": {
            "continuation": {"type": "boolean"},
            "differentialUpdate": {"type": "boolean"},
            "playlistId": {"type": "string"},
            "requestTime": {"type": "integer"},
            "playlist": song_array,
        },
        "additionalProperties": {
            "continuationToken": {"type": "string"}}
    }

    @staticmethod
    def dynamic_data(cont_token=None):
        """:param cont_token: (optional) token to get the next library chunk."""
        if not cont_token:
            req = {}
        else:
            req = {"continuationToken": cont_token}

        return {'json': json.dumps(req)}

    @staticmethod
    def filter_response(msg):
        """Don't log all songs, just a few."""
        filtered = copy.copy(msg)
        filtered['playlist'] = utils.truncate(msg['playlist'], max_els=2)

        return filtered


class ReportBadSongMatch(WcCall):
    """Request to signal the uploader to reupload a matched track."""

    static_method = 'POST'
    static_url = service_url + 'fixsongmatch'
    static_params = {'format': 'jsarray'}

    #This response is always the same.
    expected_response = [[0], []]

    @classmethod
    def validate(cls, res):
        if res != cls.expected_response:
            raise ValidationException("response != %r" % cls.expected_response)

    @staticmethod
    def dynamic_data(song_ids):
        return json.dumps([["", 1], [song_ids]])
