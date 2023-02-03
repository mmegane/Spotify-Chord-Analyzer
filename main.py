import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import ruptures as rpt
import numpy as np

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

    time = str(mins) + ":%02d" % seconds

    return(time)

def return_breakpoints(pitches, model, min_size, jump, pen):
    #N = len(pitches)
    #dim = 12

    algo = rpt.Pelt(model = model, min_size = min_size, jump = jump).fit(signal)
    my_bkps = algo.predict(pen = pen)

    return(my_bkps)

def preprocess_pitches(pitches, breakpoints):

    breakpoints = np.insert(breakpoints, 0, 0)
    breakpoints[-1] -= 1

    N = len(breakpoints)

    preprocessed_pitches = np.empty(pitches.shape)

    for i in range(N - 1):

        a = breakpoints[i]
        b = breakpoints[i + 1]

        preprocessed_pitches[a:b, :] = np.mean(pitches[a:b, :], axis = 0)


    return(preprocessed_pitches)

def get_breakpoint_times(breakpoints, segments):


    N = len(breakpoints)

    times = []

    for i in breakpoints[:-1]:

        time = format_time(segments[i]["start"])
        times.append(time)

    return(times)

def get_interval_vectors(signals, threshold_fraction):

    max_values = np.max(signals, axis = 1)
    output_array = signals > max_values.reshape(max_values.shape[0], 1) * threshold_fraction
    output_array = output_array.astype(int)

    return(output_array)

# Return hamming distance between two equally sized binary vectors
def return_hamming_distance(a, b):

    N = len(a)

    if N != len(b):
        raise ValueError("Arguments must have equal length")

    dist = 0
    for i in range(N):

        value_a = a[i]
        value_b = b[i]

        if value_a != value_b:
            dist +=1
    
    return(dist)

# Return all hamming distances between two differently sized binary vectors
def return_hamming_distances(a, b):

    N_a = len(a)
    N_b = len(b)

    if N_b > N_b:
        raise ValueError("The second argument cannot be larger than the first")

    dists = []

    for i in range(N_a - N_b + 1):

        left_pad = i
        right_pad = (N_a - N_b) - i

        c = [0] * left_pad + b + [0] * right_pad

        dist = return_hamming_distance(a, c)
        
        dists.append(dist)
    
    return(dists)

def map_vector_to_chord(vector, chord_map, pitch_map):

    MAX_DIST = 12

    current_best_dist = MAX_DIST
    chord_quality = ""
    shift = 0
    pitch_vector = None

    for chord in chord_map:

        inversions = chord_map[chord]

        for inversion in inversions:
            dists = return_hamming_distances(vector, inversion[0])

            N = len(dists)

            for i in range(N):

                if dists[i] <= current_best_dist:

                    current_best_dist = dists[i]
                    chord_quality = chord
                    pitch_vector = inversion
                    shift = i

    output = chord_quality

    if chord_quality != "No chord":
        
        root_note_index = pitch_vector[1]
        pitch_index = shift + root_note_index
        pitch = pitch_map[pitch_index]
        output = pitch + chord_quality

    return(output)



# Connect to client
auth_manager = SpotifyOAuth(CLIENT_ID, CLIENT_SECRET, scope = SCOPE, redirect_uri = REDIRECT_URI)
spotify = spotipy.Spotify(auth_manager = auth_manager)


pitch_map = {0: "C", 1: "C#", 2: "D", 3: "D#", 4: "E", 5: "F", 6: "F#", 7: "G", 8: "G#", 9: "A", 10: "A#", 11: "B"}  

chord_map = {"Maj": [([1, 0, 0, 0, 1, 0, 0, 1], 0), ([1, 0, 0, 1, 0, 0, 0, 0, 1], 8), ([1, 0, 0, 0, 0, 1, 0, 0, 0, 1], 5)],
             "min": [([1, 0, 0, 1, 0, 0, 0, 1], 0), ([1, 0, 0, 0, 1, 0, 0, 0, 0, 2], 9), ([1, 0, 0, 0, 0, 1, 0, 0, 1], 5)],
             "Aug": [([1, 0, 0, 0, 1, 0, 0, 0, 1], 0)],
             "Dim": [([1, 0, 0, 1, 0, 0, 1], 0), ([1, 0, 0, 1, 0, 0, 0, 0 ,0, 1], 9), ([1, 0, 0, 0, 0 ,0, 1, 0, 0, 1], 6)],
             "Maj7": [([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1], 0), ([1, 0, 0, 1, 0, 0, 0, 1, 1], 8), ([1, 0, 0, 0, 1, 1, 0, 0, 0, 1], 5), ([1, 1, 0, 0, 0, 1, 0, 0, 1], 1)],
             "min7": [([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1], 0), ([1, 0, 0, 0, 1, 0, 0, 1, 0, 1], 9), ([1, 0, 0, 1, 0, 1, 0, 0, 1], 5), ([1, 0, 1, 0, 0, 1, 0, 0, 0, 1], 2)],
             "7": [([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1], 0), ([1, 0, 0, 1, 0, 0, 1, 0, 1], 8), ([1, 0, 0, 1, 0, 1, 0, 0, 0, 1], 5), ([1, 0, 1, 0, 0, 0, 1, 0, 0, 1], 2)],
             "No chord": [([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], None), ([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], None)]}

True

currently_playing_track = refresh_currently_playing_track(spotify)
current_track_id = currently_playing_track["id"]
audio_analysis = refresh_audio_analysis(spotify, current_track_id)
pitches = extract_pitches(audio_analysis["segments"])

model = "l1"
min_size = 3
jump = 1
pen = 1

threshold_fraction = 0.33

signal = np.asarray(pitches)
chord_breakpoints = return_breakpoints(signal, model, min_size, jump, pen)
breakpoint_times = get_breakpoint_times(chord_breakpoints, audio_analysis["segments"])
preprocessed_pitches = preprocess_pitches(signal, chord_breakpoints)
interval_vectors = get_interval_vectors(preprocessed_pitches, threshold_fraction)
interval_vectors_raw = get_interval_vectors(signal, threshold_fraction)

#chords = np.unique(preprocessed_pitches, axis = 0)

#print(preprocessed_pitches.shape)
#print(signal.shape)

a = 0
b = 200

"""

print(chord_breakpoints)
print()
print(breakpoint_times)
print()
print("Raw signal:")
print("  C:   C#:  D:   D#   E:   F:   F#:  G:   G#:  A:   A#:  B:")
print(signal[a:b,:])
print("  C:   C#:  D:   D#   E:   F:   F#:  G:   G#:  A:   A#:  B:")
print()
print ("  C C#D D#E F F#G G#A A#B")
print(interval_vectors_raw[a:b,:])
print ("  C C#D D#E F F#G G#A A#B")
print()
print("Preprocessed signal:")
print("  C:   C#:  D:   D#   E:   F:   F#:  G:   G#:  A:   A#:  B:")
print(preprocessed_pitches[a:b,:])
print("  C:   C#:  D:   D#   E:   F:   F#:  G:   G#:  A:   A#:  B:")
print()
print ("  C C#D D#E F F#G G#A A#B")
print(interval_vectors[a:b,:])
print ("  C C#D D#E F F#G G#A A#B")

"""
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


#print(*chords[a:b], sep = "\n")

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