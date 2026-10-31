import unittest
from unittest import mock

import kodistubs
from clouddrive.common.remote.provider import Provider
from clouddrive.common.ui import nfo
from clouddrive.common.ui.addon import CloudDriveAddon
from clouddrive.common.ui.utils import KodiUtils

kodistubs.use_temp_profile()

VIDEOS = ['mkv', 'mp4', 'avi']


def item(name, **extra):
    i = {'id': 'id-' + name, 'name': name, 'name_extension': name.rsplit('.', 1)[-1], 'size': 100, 'last_modified_date': '2026-10-01T10:00:00Z'}
    i.update(extra)
    return i


MOVIE_NFO = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<movie>
    <title>The Movie</title>
    <originaltitle>O Filme</originaltitle>
    <plot>Someone does something.</plot>
    <outline>Short plot.</outline>
    <tagline>Once.</tagline>
    <runtime>120</runtime>
    <mpaa>PG-13</mpaa>
    <premiered>2021-05-04</premiered>
    <genre>Drama</genre>
    <genre>Comedy</genre>
    <director>A Director</director>
    <credits>A Writer</credits>
    <studio>A Studio</studio>
    <ratings>
        <rating name="imdb" max="10"><value>6.1</value><votes>100</votes></rating>
        <rating name="themoviedb" max="10" default="true"><value>7.5</value><votes>1,234</votes></rating>
    </ratings>
    <uniqueid type="tmdb">123</uniqueid>
    <uniqueid type="imdb" default="true">tt0123456</uniqueid>
    <set><name>The Saga</name></set>
    <thumb aspect="poster">https://image.example.com/poster.jpg</thumb>
    <thumb aspect="poster">https://image.example.com/other-poster.jpg</thumb>
    <thumb aspect="clearlogo">https://image.example.com/logo.png</thumb>
    <thumb aspect="banner">/local/path/banner.jpg</thumb>
    <fanart><thumb>https://image.example.com/fanart.jpg</thumb></fanart>
    <actor><name>An Actor</name><role>Hero</role><order>0</order><thumb>https://image.example.com/actor.jpg</thumb></actor>
    <actor><name>Another</name><role>Villain</role><order>1</order></actor>
</movie>
https://www.themoviedb.org/movie/123
'''

EPISODE_NFO = '''<episodedetails>
    <title>Pilot</title>
    <showtitle>The Show</showtitle>
    <season>1</season>
    <episode>2</episode>
    <aired>2020-01-02</aired>
    <rating>8.2</rating>
    <thumb>https://image.example.com/episode.jpg</thumb>
</episodedetails>
<episodedetails><title>Second part</title><season>1</season><episode>3</episode></episodedetails>'''


class ParseTest(unittest.TestCase):
    def test_movie(self):
        parsed = nfo.parse(MOVIE_NFO)
        info = parsed['info']
        self.assertEqual((info['mediatype'], info['title'], info['originaltitle'], info['year'], info['duration']), ('movie', 'The Movie', 'O Filme', 2021, 7200))
        self.assertEqual((info['plot'], info['plotoutline'], info['tagline'], info['mpaa']), ('Someone does something.', 'Short plot.', 'Once.', 'PG-13'))
        self.assertEqual((info['genre'], info['director'], info['writer'], info['studio']), (['Drama', 'Comedy'], ['A Director'], ['A Writer'], ['A Studio']))
        self.assertEqual((info['rating'], info['votes'], info['imdbnumber'], info['set']), (7.5, '1234', 'tt0123456', 'The Saga'), 'the default rating')
        self.assertEqual(parsed['art'], {'poster': 'https://image.example.com/poster.jpg', 'clearlogo': 'https://image.example.com/logo.png',
                                         'fanart': 'https://image.example.com/fanart.jpg'}, 'only web addresses, the first of each')
        self.assertEqual(parsed['cast'], [{'name': 'An Actor', 'role': 'Hero', 'order': 0, 'thumbnail': 'https://image.example.com/actor.jpg'},
                                          {'name': 'Another', 'role': 'Villain', 'order': 1}])

    def test_episode(self):
        parsed = nfo.parse(EPISODE_NFO)
        info = parsed['info']
        self.assertEqual((info['mediatype'], info['title'], info['tvshowtitle'], info['season'], info['episode'], info['year'], info['rating']),
                         ('episode', 'Pilot', 'The Show', 1, 2, 2020, 8.2), 'the first episode of a multi-episode file')
        self.assertEqual(parsed['art'], {'thumb': 'https://image.example.com/episode.jpg'})

    def test_not_an_nfo(self):
        for text in ('', 'https://www.imdb.com/title/tt0123456/', '<movie><title>Broken</movie>', '<?xml version="1.0"?><other/>'):
            self.assertIsNone(nfo.parse(text), text)

    def test_entities_are_refused(self):
        bomb = '<?xml version="1.0"?><!DOCTYPE movie [<!ENTITY a "aaaaaaaaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">]><movie><title>&b;</title></movie>'
        self.assertIsNone(nfo.parse(bomb))

    def test_decoding(self):
        self.assertEqual(nfo.decode(u'﻿<movie/>'.encode('utf-8')), '<movie/>')
        self.assertEqual(nfo.decode(u'<movie><title>Ação</title></movie>'.encode('latin-1')), u'<movie><title>Ação</title></movie>')


class FindTest(unittest.TestCase):
    def test_files_named_after_the_video(self):
        items = [item('Movie (2021).mkv'), item('Movie (2021).nfo'), item('Movie (2021)-poster.jpg'), item('Movie (2021)-fanart.png'),
                 item('Movie (2021).tbn'), item('Other.mp4'), item('Other-thumb.jpg'), item('notes.txt'), item('Extras', folder={'child_count': 1})]
        found = nfo.find(items, VIDEOS)
        movie = found['id-Movie (2021).mkv']
        self.assertEqual(movie['nfo']['name'], 'Movie (2021).nfo')
        self.assertEqual({k: v['name'] for k, v in movie['art'].items()},
                         {'poster': 'Movie (2021)-poster.jpg', 'fanart': 'Movie (2021)-fanart.png', 'thumb': 'Movie (2021).tbn'})
        self.assertEqual((found['id-Other.mp4']['nfo'], found['id-Other.mp4']['art']['thumb']['name']), (None, 'Other-thumb.jpg'))
        self.assertEqual(len(found), 2)

    def test_folder_files(self):
        one = nfo.find([item('movie.mkv'), item('movie.NFO'), item('MOVIE.nfo'), item('poster.jpg'), item('fanart.jpg')], VIDEOS)
        self.assertEqual(one['id-movie.mkv']['nfo']['name'], 'movie.NFO', 'names in any case, the first one listed')
        folder = nfo.find([item('The Movie.mkv'), item('movie.nfo'), item('folder.jpg'), item('fanart.jpg'), item('The Movie-fanart.jpg')], VIDEOS)
        movie = folder['id-The Movie.mkv']
        self.assertEqual(movie['nfo']['name'], 'movie.nfo', "a folder's only movie")
        self.assertEqual({k: v['name'] for k, v in movie['art'].items()}, {'poster': 'folder.jpg', 'fanart': 'The Movie-fanart.jpg'})
        episodes = nfo.find([item('S01E01.mkv'), item('S01E02.mkv'), item('movie.nfo'), item('poster.jpg')], VIDEOS)
        self.assertEqual([e['nfo'] for e in episodes.values()], [None, None], 'movie.nfo is for one movie')
        self.assertEqual([e['art']['poster']['name'] for e in episodes.values()], ['poster.jpg', 'poster.jpg'])

    def test_nothing_to_show(self):
        self.assertEqual(nfo.find([item('a.mkv'), item('b.srt'), item('c.jpg')], VIDEOS), {})


class Addon(CloudDriveAddon):
    # Built without the constructor, which needs Kodi: nothing to release.
    def __del__(self):
        pass


class FakeProvider(Provider):
    download_requires_auth = False

    def __init__(self, files):
        super(FakeProvider, self).__init__('fake')
        self.files = files
        self.reads = []

    def get_item(self, item_driveid=None, item_id=None, path=None, find_subtitles=False, include_download_info=False):
        return {'id': item_id, 'download_info': {'url': 'https://files.example.com/' + item_id}}


class BrowsingTest(unittest.TestCase):
    def setUp(self):
        self.provider = FakeProvider({'id-Movie.nfo': MOVIE_NFO.encode('utf-8'), 'id-Broken.nfo': b'not xml'})
        self.addon = object.__new__(Addon)
        self.addon._addonid = 'test'
        self.addon._video_file_extensions = VIDEOS
        self.addon._cancel_operation = False
        self.addon.cancel_operation = lambda: False
        self.addon.get_provider = lambda: self.provider
        self.addon._get_item_play_url = lambda name, driveid, item_driveid=None, item_id=None, is_subtitle=False: 'http://127.0.0.1/download/%s/%s' % (driveid, item_id)
        self.drive = 'drive-' + self._testMethodName

    def read(self, url, data=None, **kwargs):
        request = mock.MagicMock()
        file_id = url.rsplit('/', 1)[-1]
        self.provider.reads.append(file_id)
        request.request.return_value = self.provider.files[file_id]
        return request

    def add(self, items):
        with mock.patch('clouddrive.common.ui.addon.Request', side_effect=self.read):
            self.addon._add_nfo_info(self.drive, items)
        return items

    def test_videos_get_their_nfo_and_artwork(self):
        items = self.add([item('Movie.mkv'), item('Movie.nfo'), item('Movie-poster.jpg'), item('Plain.mkv')])
        movie = items[0]['nfo']
        self.assertEqual((movie['info']['title'], movie['cast'][0]['name']), ('The Movie', 'An Actor'))
        self.assertEqual(movie['art']['poster'], 'http://127.0.0.1/download/%s/id-Movie-poster.jpg' % self.drive, 'the file next to it wins')
        self.assertEqual(movie['art']['fanart'], 'https://image.example.com/fanart.jpg')
        self.assertNotIn('nfo', items[3])

    def test_nfo_files_are_read_once(self):
        self.add([item('Movie.mkv'), item('Movie.nfo')])
        self.add([item('Movie.mkv'), item('Movie.nfo')])
        self.assertEqual(self.provider.reads, ['id-Movie.nfo'])
        self.add([item('Movie.mkv'), item('Movie.nfo', last_modified_date='2026-10-31T10:00:00Z')])
        self.assertEqual(len(self.provider.reads), 2, 'read again when changed')

    def test_many_at_once(self):
        names = ['E%02d' % n for n in range(12)]
        self.provider.files.update(('id-%s.nfo' % n, EPISODE_NFO.replace('Pilot', n).encode('utf-8')) for n in names)
        items = self.add([item(n + '.mkv') for n in names] + [item(n + '.nfo') for n in names])
        self.assertEqual([i['nfo']['info']['title'] for i in items[:12]], names)

    def test_unreadable_files_are_skipped(self):
        items = self.add([item('Broken.mkv'), item('Broken.nfo'), item('Big.mkv'), item('Big.nfo', size=nfo.MAX_SIZE + 1)])
        self.assertEqual(items[0]['nfo']['info'], {})
        self.assertEqual(self.provider.reads, ['id-Broken.nfo'], 'big ones are not read')

    def test_listing_shows_it(self):
        settings = {'page_size': '0', 'nfo_info': 'true'}
        with mock.patch.object(KodiUtils, 'get_addon_setting', side_effect=lambda setting_id, addonid=None: settings.get(setting_id, '')), \
                mock.patch.object(KodiUtils, 'get_cache_expiration_time', return_value=0):
            for setting, expected in (('true', True), ('false', False)):
                settings['nfo_info'] = setting
                shown = {}
                self.addon._content_type = 'video'
                self.addon._child_count_supported = False
                self.addon._account_manager = None
                self.provider.configure = lambda account_manager, driveid: None
                self.provider.get_folder_items = lambda *args, **kwargs: [item('Movie.mkv'), item('Movie.nfo')]
                self.addon._process_items = lambda items, driveid, next_page_url=None: shown.update(items=items)
                with mock.patch('clouddrive.common.ui.addon.Request', side_effect=self.read):
                    self.addon._list_folder(self.drive, item_id='f')
                self.assertEqual('nfo' in shown['items'][0], expected, setting)


    def test_list_items_show_it(self):
        self.addon._addon_url = 'plugin://test/'
        self.addon._content_type = 'video'
        self.addon._addon_handle = 1
        self.addon._common_addon = kodistubs.FakeAddon()
        self.addon._fresh_listing = False
        items = self.add([item('Movie.mkv'), item('Movie.nfo'), item('Movie-poster.jpg')])
        with mock.patch('clouddrive.common.ui.addon.xbmcplugin') as xbmcplugin, mock.patch('clouddrive.common.ui.addon.xbmcgui') as xbmcgui:
            xbmcgui.ListItem.side_effect = lambda label: mock.MagicMock(label=label)
            self.addon._process_items(items[:1], self.drive)
        [(url, list_item, is_folder)] = xbmcplugin.addDirectoryItems.call_args[0][1]
        info_type, info = list_item.setInfo.call_args[0]
        self.assertEqual((info_type, info['title'], info['mediatype'], info['size']), ('video', 'The Movie', 'movie', 100))
        self.assertEqual(list_item.setArt.call_args[0][0]['poster'], 'http://127.0.0.1/download/%s/id-Movie-poster.jpg' % self.drive)
        self.assertEqual(list_item.setCast.call_args[0][0][1]['name'], 'Another')


if __name__ == '__main__':
    unittest.main()
