import ruptures as rpt
import numpy as np

# Returns 2D array containing all pitch vectors in a track
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

    if currently_playing_track is None:
        print("Play a song...", end = "\r")
        return(None)

    if currently_playing_track['item'] is None:
        return(None)
    
    else:
        currently_playing_track = {'id': currently_playing_track['item']['id'],
                                   'name': currently_playing_track['item']['name'],
                                   'progress': currently_playing_track['progress_ms']}

    return(currently_playing_track)
    
def refresh_audio_analysis(client, id, track_parameters,
                                       bars_parameters,
                                       section_parameters,
                                       segment_parameters):

        audio_analysis = client.audio_analysis(track_id = id)
        audio_analysis = {'track': dict((k, audio_analysis['track'][k]) for k in track_parameters),
                          'bars': return_dict_list_subset(audio_analysis['bars'], bars_parameters),
                          'sections': return_dict_list_subset(audio_analysis['sections'], section_parameters),
                          'segments': return_dict_list_subset(audio_analysis['segments'], segment_parameters)}

        return(audio_analysis)

def return_matching_index(segments, progress):

    N = len(segments)
    
    matching_index = next(index for index in range(N) if
                          ((segments[index]["start"] <= progress) and (progress <= segments[index]["start"] + segments[index]["duration"])))

    return(matching_index)

def format_time(time):

    (mins, seconds) = divmod(time, 60)
    mins =  int(mins)
    seconds = int(seconds)

    time = str(mins) + ":%02d" % seconds

    return(time)

# Return time series segmentation
def return_breakpoints(signal, custom_cost, min_size, jump, pen):

    threshold = 0.25
    thresh_signal = get_interval_vectors(signal, threshold)

    algo = rpt.Pelt(min_size = min_size, jump = jump, custom_cost = custom_cost).fit(signal)
    my_bkps = algo.predict(pen = pen)

    return(my_bkps)

# Takes a 2D array of pitches and returns a piecewise constant averaged signal
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

    #max_values = np.max(signals, axis = 1)
    #output_array = signals > max_values.reshape(max_values.shape[0], 1) * threshold_fraction
    output_array = signals > threshold_fraction
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
            dist += 1
    
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

# Returns the sequence of chords derived from a 2D matrix of interval vectors
def get_chord_progression(interval_vectors, chord_map, pitch_map):

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

    return(chord_progression)

def compile_notes(interval_vectors, pitch_map):

    samples = []

    for pitches in interval_vectors:
        pitch_indeces = [i for i in range(len(pitches)) if pitches[i] == 1]
        
        notes = []
        for i in pitch_indeces:
            note = pitch_map[i]
            notes.append(note)
        
        samples.append(notes)
    
    return(samples)

def save_chords_to_file(path, song_name, breakpoint_times, interval_vectors, chord_map, pitch_map):
    
    print("Writing chord progression to \"" + path + "\" \n")

    f = open(path, "w")
    f.truncate(0)
    
    f.write("Song name: " + song_name + "\n\n")

    f.write("Chord breakpoints: \n")
    for breakpoint in breakpoint_times:
        f.write(breakpoint + " ")
    f.write("\n\n")

    chord_progression = get_chord_progression(interval_vectors, chord_map, pitch_map)

    f.write("Chord progression: \n")
    for chord in chord_progression:
        f.write(chord + " ")
    f.write("\n\n")

    unique_chords = np.unique(chord_progression)

    f.write("Unique chords: \n")
    f.write(str(unique_chords))
    f.close()

def save_notes_to_file(path, song_name, interval_vectors, pitch_map):
    
    notes = compile_notes(interval_vectors, pitch_map)
    
    print("Writing notes to \"" + path + "\" \n")

    f = open(path, "w")
    f.truncate(0)
    
    f.write("Song name: " + song_name + "\n\n")

    f.write("Notes: \n")
    for sample in notes:
        f.write(str(sample) + "\n")
    f.close()