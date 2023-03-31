import spotipy
import argparse
from spotipy.oauth2 import SpotifyPKCE

import constants
from utils import *

np.set_printoptions(precision = 2, suppress = 0)
    
CLIENT_ID =  "d80693fb76ed473b8a101b73aa936f9b"
REDIRECT_URI = "http://spotifychords.se"
SCOPE = "user-read-playback-state"

TRACK_PARAMETERS = ['num_samples', 'tempo', 'time_signature', 'key', 'mode']
BARS_PARAMETERS = ['start', 'duration', 'confidence']
SECTIONS_PARAMETERS = ['start', 'duration', 'loudness', 'tempo', 'key', 'mode', 'time_signature']
SEGMENT_PARAMETERS = ['start', 'duration', 'pitches']

DICT_PARAMETERS = [TRACK_PARAMETERS, BARS_PARAMETERS, SECTIONS_PARAMETERS, SEGMENT_PARAMETERS]

def main():

    # Parse (optional) arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-sc", "--save_chords", action = 'store_true', help = "Save the chord progression to file.")
    parser.add_argument("-sn", "--save_notes", action = 'store_true', help = "Save the sequence of notes to file.")
    args = parser.parse_args()
    save_chords = args.save_chords
    save_notes = args.save_notes

    # Connect to client
    auth_manager = SpotifyPKCE(CLIENT_ID, scope = SCOPE, redirect_uri = REDIRECT_URI)
    spotify = spotipy.Spotify(auth_manager = auth_manager)

    # Algorithm parameters
    cost = rpt.costs.CostL1()
    min_size = 2
    jump = 1
    pen = 3

    threshold_fraction_a = 0.15
    threshold_fraction_b = 0.25

    #distance_function = return_cosine_distance
    distance_function = return_hamming_distance

    chords_path = "./progression.txt"
    notes_path = "./notes.txt"

    current_track_id = ""

    listening = True

    while listening:
        
        currently_playing_track = refresh_currently_playing_track(spotify)

        if currently_playing_track is None:
            continue

        if (currently_playing_track["id"] != current_track_id):

            current_track_id = currently_playing_track["id"]
            audio_analysis = refresh_audio_analysis(spotify, current_track_id, DICT_PARAMETERS)

            segments = audio_analysis["segments"]

            pitches = extract_pitches(segments)
            signal = np.asarray(pitches)

            interval_vectors_raw = get_interval_vectors(signal, threshold_fraction_a)
            chord_breakpoints = return_breakpoints(interval_vectors_raw, cost, min_size, jump, pen)
            breakpoint_times = get_breakpoint_times(chord_breakpoints, segments)

            preprocessed_pitches = preprocess_pitches(signal, chord_breakpoints)
            interval_vectors = get_interval_vectors(preprocessed_pitches, threshold_fraction_b)
            
            if save_chords:
                song_name = currently_playing_track["name"]
                save_chords_to_file(chords_path, song_name, distance_function, breakpoint_times, interval_vectors, constants.chord_map,
                                                                                                                   constants.pitch_map)
            if save_notes:
                song_name = currently_playing_track["name"]
                save_notes_to_file(notes_path, song_name, interval_vectors_raw, constants.pitch_map)
        
        current_progress = currently_playing_track["progress"]/1000
        current_time = format_time(current_progress)

        # Query data on segment that matches current position in track
        matching_index = return_matching_index(segments, current_progress)
        interval_vector = interval_vectors[matching_index]
        current_chord = map_vector_to_chord(interval_vector, distance_function, constants.chord_map,
                                                                                constants.pitch_map)

        out = "Progress: " + current_time + "\n" + "\n" 

        out += "Raw pitches:" + "\n"
        out += " C:   C#:  D:   D#   E:   F:   F#:  G:   G#:  A:   A#:  B:" + "\n"
        out += str(signal[matching_index]) + "\n"
        out += " C C#D D#E F F#G G#A A#B" + "\n"
        out += str(interval_vectors_raw[matching_index]) + "\n" +"\n"

        out += "Preprocessed pitches:" + "\n"
        out += " C:   C#:  D:   D#   E:   F:   F#:  G:   G#:  A:   A#:  B:" + "\n"
        out += str(preprocessed_pitches[matching_index]) + "\n"
        out += " C C#D D#E F F#G G#A A#B" + "\n"
        out += str(interval_vectors[matching_index]) + "\n" + "\n"

        out += "Chord:" + "\n"
        out += current_chord + "\n" + "\n"

        print(out, end = "\r")

if __name__ == "__main__":
    main()