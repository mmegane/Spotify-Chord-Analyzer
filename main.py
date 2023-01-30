import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import ruptures as rpt
import numpy as np

with open('secret.txt', 'r') as file:
    secret = file.read()
    
CLIENT_ID =  "d80693fb76ed473b8a101b73aa936f9b"
CLIENT_SECRET = secret
REDIRECT_URI = "http://spotifychords.se"

SCOPE = "user-read-playback-state"

TRACK_PARAMETERS = ['num_samples', 'tempo', 'time_signature', 'key', 'mode']
BARS_PARAMETERS = ['start', 'duration', 'confidence']
SECTIONS_PARAMETERS = ['start', 'duration', 'loudness', 'tempo', 'key', 'mode', 'time_signature']
SEGMENT_PARAMETERS = ['start', 'duration', 'pitches']

# Return 2D array containing all pitch vectors in a track
def extract_pitches(segments):

    output_list = []

    for segment in segments:
        pitches_i = segment["pitches"]
        output_list.append(pitches_i)

    return(output_list)

# Returns subset of keys from a list of dicts
def return_dict_list_subset(dict_list, keys):
    output_list = []

    for dictionary in dict_list:
        output_list.append(dict((k, dictionary[k]) for k in keys))

    return(output_list)

def refresh_currently_playing_track(client):
    currently_playing_track = client.current_user_playing_track()

    if currently_playing_track is not None:
        currently_playing_track = {'id': currently_playing_track['item']['id'],
                                   'name': currently_playing_track['item']['name'],
                                   'progress': currently_playing_track['progress_ms']}
    return(currently_playing_track)
    
def refresh_audio_analysis(client, id):
        audio_analysis = client.audio_analysis(track_id = id)
        audio_analysis = {'track': dict((k, audio_analysis['track'][k]) for k in TRACK_PARAMETERS),
                          'bars': return_dict_list_subset(audio_analysis['bars'], BARS_PARAMETERS),
                          'sections': return_dict_list_subset(audio_analysis['sections'], SECTIONS_PARAMETERS),
                          'segments': return_dict_list_subset(audio_analysis['segments'], SEGMENT_PARAMETERS)}

        return(audio_analysis)

def return_matching_segment(segments, progress):

    matching_segment = next(item for item in segments if
                          ((item["start"] < progress) and (progress <= item["start"] + item["duration"])))

    return(matching_segment)

def format_time(time):

    (mins, seconds) = divmod(time, 60)
    mins =  int(mins)
    seconds = int(seconds)

    return((mins, seconds))

# Connect to client
auth_manager = SpotifyOAuth(CLIENT_ID, CLIENT_SECRET, scope = SCOPE, redirect_uri = REDIRECT_URI)
spotify = spotipy.Spotify(auth_manager = auth_manager)

current_track_id = ""
pitch_map = {0: "C", 1: "C#", 2: "D", 3: "D#", 4: "E", 5: "F", 6: "F#", 7: "G", 8: "G#", 9: "A", 10: "A#", 11: "B"}

currently_playing_track = refresh_currently_playing_track(spotify)
current_track_id = currently_playing_track["id"]
audio_analysis = refresh_audio_analysis(spotify, current_track_id)
pitches = extract_pitches(audio_analysis["segments"])

num_samples = audio_analysis["track"]["num_samples"]

n = len(pitches)
dim = 12

model = "l1" # "l2", "rbf"
min_size = 3
jump = 1
pen = 3

signal = np.asarray(pitches)

algo = rpt.Pelt(model = model, min_size = min_size, jump = jump).fit(signal)
my_bkps = algo.predict(pen = pen)
print(my_bkps)

model = "l2"

algo = rpt.Pelt(model = model, min_size = min_size, jump = jump).fit(signal)
my_bkps = algo.predict(pen = pen)
print(my_bkps)

model = "rbf"

algo = rpt.Pelt(model = model, min_size = min_size, jump = jump).fit(signal)
my_bkps = algo.predict(pen = pen)
print(my_bkps)

listening = False

while listening:
    
    currently_playing_track = refresh_currently_playing_track(spotify)

    if currently_playing_track is None:
        continue

    if (currently_playing_track["id"] != current_track_id):
        current_track_id = currently_playing_track["id"]
        audio_analysis = refresh_audio_analysis(spotify, current_track_id)

    current_progress = currently_playing_track["progress"]/1000

    # Query data on segment that matches current position in track
    matching_segment = return_matching_segment(audio_analysis["segments"], current_progress)

    pitches = matching_segment["pitches"]

    out = ""

    (mins, seconds) = format_time(current_progress)

    out += "Progress: " + str(mins) + ":%02d" % seconds + "\n"

    for i in range(12):
        out += pitch_map[i] + ": %f" % pitches[i] + "\n"

    print(out)