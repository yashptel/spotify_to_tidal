#!/usr/bin/env python3

import argparse
from mutagen.mp4 import MP4, MP4Cover
from pathlib import Path
import requests
import sys
import tidalapi
import tidalapi_patch
tidalapi_patch.patch()
from tqdm import tqdm
import yaml

def track_file_name(track, url):
    source_extension = url.split('/')[-1].split('?')[0].split('.')[-1]
    extension = 'm4a' if source_extension == 'mp4' else source_extension
    name = "{} - {}{}.{}".format(track.artist.name, track.name, " ({})".format(track.version) if track.version else "", extension)
    return name

def download_track(tidal_session, track, folder):
    media_url = tidal_session.get_media_url(track.id)
    file_path = Path(folder) / make_safe_filename(track_file_name(track, media_url))
    if file_path.exists():
        print("Skipping existing file {}".format(str(file_path.name)))
        return
    with tqdm.wrapattr(open(file_path, 'wb+'), "write", miniters=1, desc = "Downloading {}".format(str(file_path.name))) as fout:
        for chunk in requests.get(media_url):
            fout.write(chunk)
    return file_path

def download_track_with_metadata(tidal_session, track, folder):
    file_path = download_track(tidal_session, track, folder)
    # for some reason Serato thinks the track is corrupt unless the below code
    # is in a separate function from download_track
    set_metadata(track, file_path)

def set_metadata(track, filename):
    if not filename.suffix == '.m4a':
        # flac not supported yet
        return
    f = MP4(str(filename))
    f.tags.clear()
    f.tags['\xa9ART'] = track.artist.name
    f.tags['\xa9nam'] = "{}{}".format(track.name, " ({})".format(track.version) if track.version else "")
    f.tags['\xa9alb'] = track.album.name
    if track.album.release_date:
        f.tags['\xa9day'] = str(track.album.release_date.year)
    with requests.get(track.album.picture(320,320)) as result:
        if result.ok:
            f.tags['covr'] = [ MP4Cover(result.content) ]
    f.save()

def download_playlist(tidal_session, playlist, folder):
    folder = Path(folder) / make_safe_filename(playlist.name)
    if not folder.exists():
        folder.mkdir()
    print("Save location: {}".format(str(folder)))
    for track in tidal_session.get_playlist_tracks(playlist.id):
        download_track_with_metadata(tidal_session, track, folder)

def open_tidal_session(config):
    quality_mapping = {'low': tidalapi.Quality.low, 'high': tidalapi.Quality.high, 'lossless': tidalapi.Quality.lossless}
    quality = quality_mapping[config.get('quality', 'high').lower()]
    session = tidalapi.Session(tidalapi.Config(quality=quality))
    session.login(config['username'], config['password'])
    return session

def make_safe_filename(name):
    return name.translate({ord(c): None for c in '\/:*?"<>|'})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('uri', help='URI of the song or playlist to download')
    parser.add_argument('--config', default='config.yml', help='location of the config file')
    parser.add_argument('--output_folder', help='Folder to save the file to')
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    tidal_session = open_tidal_session(config['tidal'])
    output_folder = args.output_folder if args.output_folder else config.get('save_path', Path.cwd())
    if not tidal_session.check_login():
        sys.exit("Could not connect to Tidal")
    if not Path(output_folder).exists():
        sys.exit("Path '{}' does not exist".format(output_folder))
    id = args.uri.split('/')[-1]
    if '-' in id:
        playlist = tidal_session.get_playlist(id)
        download_playlist(tidal_session, playlist, output_folder)
    else:
        track = tidal_session.get_track(id)
        file_path = download_track_with_metadata(tidal_session, track, output_folder)

