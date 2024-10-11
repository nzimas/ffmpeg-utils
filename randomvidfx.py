import subprocess
import random

# Input variables
audio = "input.wav"
image = "input.png"
output = "output.mp4"
frame_rate = 30  # Set the frame rate of the video

# List of all possible transitions
transitions = [
    "fade", "fadeblack", "fadewhite", "fadegrays", "wipeleft", "wiperight", "wipeup", "wipedown",
    "wipetl", "wipetr", "wipebl", "wipebr", "slideleft", "slideright", "slideup", "slidedown",
    "diagbl", "diagbr", "diagtl", "diagtr", "smoothleft", "smoothright", "smoothup", "smoothdown",
    "circlecrop", "rectcrop", "circleclose", "circleopen", "squeezeh", "squeezev", "pixelize",
    "radial", "zoomin", "hlwind", "hrwind", "vuwind", "vdwind", "coverleft", "coverright", 
    "coverup", "coverdown", "revealleft", "revealright", "revealup", "revealdown"
]

# Step 1: Get the duration of the WAV file in seconds
def get_audio_duration(audio_file):
    result = subprocess.run(
        ["ffmpeg", "-i", audio_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    for line in result.stdout.splitlines():
        if "Duration" in line:
            time_str = line.split(",")[0].split("Duration:")[1].strip()
            h, m, s = map(float, time_str.split(":"))
            return h * 3600 + m * 60 + s
    return None

audio_seconds = get_audio_duration(audio)

# Step 2: Merge WAV file and PNG to create a base MP4 with preserved audio quality
subprocess.run([
    "ffmpeg", "-loop", "1", "-i", image, "-i", audio, "-c:v", "libx264", "-tune", "stillimage", 
    "-c:a", "copy", "-pix_fmt", "yuv420p", "-shortest", "-vf", "scale=1400:1400", "-r", str(frame_rate), 
    "base_video.mp4"
])

# Step 3: Ensure diversity by avoiding consecutive repetitions and limiting the recent history of transitions
used_transitions = []
recent_limit = 3  # Limit of recently used transitions to avoid repetition
num_transitions = 9  # Number of transitions to apply

def get_random_transition():
    available_transitions = [t for t in transitions if t not in used_transitions[-recent_limit:]]
    chosen = random.choice(available_transitions)
    used_transitions.append(chosen)
    return chosen

# Step 4: Generate the filter_complex string with diverse random transitions
filter_complex = "[0:v] fps={}, hue=s=0.8:h=2, eq=contrast=1.5:brightness=-0.05:saturation=1.5, fade=t=in:st=0:d=2 [v1];".format(frame_rate)

for i in range(1, num_transitions + 1):
    next_video = i + 1
    offset = i * 5
    transition = get_random_transition()
    filter_complex += " [v{}]split[v{}a][v{}b];[v{}a][v{}b] xfade=transition={}:duration=2:offset={} [v{}];".format(
        i, i, i, i, i, transition, offset, next_video
    )

filter_complex += " [v{}] fade=t=out:st={}:d=2 [v12]".format(num_transitions + 1, audio_seconds - 2)

# Step 5: Apply the transitions and create the final output
subprocess.run([
    "ffmpeg", "-i", "base_video.mp4", "-filter_complex", filter_complex, "-map", "[v12]", "-map", "0:a",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level:v", "4.0", "-movflags", "+faststart",
    "-c:a", "copy", output
])

# Step 6: Clean up the intermediate files
subprocess.run(["rm", "base_video.mp4"])

print(f"Video processing complete: {output}")
