import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from utils import *
from constants import *

np.set_printoptions(precision = 2, suppress = 0)

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

# Connect to client
auth_manager = SpotifyOAuth(CLIENT_ID, CLIENT_SECRET, scope = SCOPE, redirect_uri = REDIRECT_URI)
spotify = spotipy.Spotify(auth_manager = auth_manager)

# Algorithm parameters
cost = rpt.costs.CostL1()
#cost = rpt.costs.CostNormal()
min_size = 3
jump = 1
pen = 3
threshold_fraction = 0.40

# Print delay in seconds
delay = 1
delay_counter = 0
listening = True

current_track_id = ""

while listening:
    
    currently_playing_track = refresh_currently_playing_track(spotify)

    if currently_playing_track is None:
        continue

    if (currently_playing_track["id"] != current_track_id):

        current_track_id = currently_playing_track["id"]
        audio_analysis = refresh_audio_analysis(spotify, current_track_id, TRACK_PARAMETERS, 
                                                                           BARS_PARAMETERS,
                                                                           SECTIONS_PARAMETERS,
                                                                           SEGMENT_PARAMETERS)

        segments = audio_analysis["segments"]

        pitches = extract_pitches(segments)
        signal = np.asarray(pitches)

        chord_breakpoints = return_breakpoints(signal, cost, min_size, jump, pen)
        breakpoint_times = get_breakpoint_times(chord_breakpoints, segments)

        preprocessed_pitches = preprocess_pitches(signal, chord_breakpoints)
        interval_vectors = get_interval_vectors(preprocessed_pitches, threshold_fraction)
        interval_vectors_raw = get_interval_vectors(signal, threshold_fraction)

        print("Chord timepoints: \n")
        print(breakpoint_times)
        print("\n")

    current_progress = currently_playing_track["progress"]/1000
    current_time = format_time(current_progress)

    # Query data on segment that matches current position in track
    matching_index = return_matching_index(segments, current_progress)

    interval_vector = interval_vectors[matching_index]
    current_chord = map_vector_to_chord(interval_vector, chord_map, pitch_map)

    delay_counter %= delay

    if delay_counter == 0:

        out = "Progress: " + current_time + "\n" + "\n" 

        out += "Raw pitches:" + "\n"
        out += " C:   C#:  D:   D#   E:   F:   F#:  G:   G#:  A:   A#:  B:" + "\n"
        out += str(signal[matching_index]) + "\n"
        out += " C C#D D#E F F#G G#A A#B" + "\n"
        out += str(interval_vectors_raw[matching_index]) + "\n" + "\n"

        out += "Preprocessed pitches:" + "\n"
        out += " C:   C#:  D:   D#   E:   F:   F#:  G:   G#:  A:   A#:  B:" + "\n"
        out += str(preprocessed_pitches[matching_index]) + "\n"
        out += " C C#D D#E F F#G G#A A#B" + "\n"
        out += str(interval_vectors[matching_index]) + "\n" + "\n"

        out += "Chord:" + "\n"
        out += current_chord + "\n" + "\n"

        print(out, end = "\r")

    delay_counter += 1

'''
chords = []
for vector in interval_vectors:
    chord = map_vector_to_chord(vector, chord_map, pitch_map)
    chords.append(chord)


chord_progression = []

N = len(chords)
chords.insert(0, None)
for i in range(1, N):
    chord = chords[i]
    prev_chord = chords[i - 1]

    if chord != prev_chord:
        chord_progression.append(chord)

print(chord_progression)
'''