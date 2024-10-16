import os
import subprocess
import random
import numpy as np

# Define file paths
audio_file = 'input.wav'
image_dir = 'alterimg/'
output_video = 'output.mp4'
temp_video = 'temp_output.mp4'
output_glitched_video = 'output_glitched.mp4'

# Fade and transition settings (user can adjust these values)
fade_in_duration = 1  # duration of fade in effect in seconds
fade_out_duration = 1  # duration of fade out effect in seconds
transition_time_min = 0.5  # minimum duration of each transition in seconds
transition_time_max = 1  # maximum duration of each transition in seconds

# Glitch effect settings (user can adjust these values)
glitch_freq = 3  # defines the number of times an effect is applied
glitch_duration_min = 1  # minimum duration of the effect in seconds
glitch_duration_max = 2  # maximum duration of the effect in seconds
random_glitch_type = 'evenly'  # 'evenly' or 'random' distribution of glitches

# Ensure the image directory exists
if not os.path.exists(image_dir):
    raise FileNotFoundError(f"Image directory '{image_dir}' not found.")

# Get all image files from the image directory
images = [os.path.join(image_dir, img) for img in sorted(os.listdir(image_dir)) if img.lower().endswith(('png', 'jpg', 'jpeg'))]

if len(images) < 2:
    raise ValueError("There should be at least two images for crossfade transitions.")

# Define available crossfade transitions
transitions = [
    'fade', 'fadeblack', 'fadewhite', 'distance',
    'smoothleft', 'smoothright', 'smoothup', 'smoothdown',
    'circlecrop', 'rectcrop', 'circleclose', 'circleopen', 'horzclose', 'horzopen', 'vertclose', 'vertopen',
    'diagbl', 'diagbr', 'diagtl', 'diagtr', 'hlslice', 'hrslice', 'vuslice', 'vdslice',
    'dissolve', 'pixelize', 'radial', 'hblur', 'fadegrays', 'squeezev', 'squeezeh', 'zoomin',
    'hlwind', 'hrwind', 'vuwind', 'vdwind', ]

# Get the duration of the audio file
try:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    audio_duration = float(result.stdout)
except Exception as e:
    raise RuntimeError(f"Failed to get audio duration: {e}")

# Calculate the total number of images needed to match the audio duration
duration_per_image = 5  # duration each image is displayed before transition
fade_duration = random.uniform(transition_time_min, transition_time_max)
image_duration_with_transition = duration_per_image - fade_duration
num_images = int((audio_duration + fade_duration) // image_duration_with_transition) + 1

# Generate filter complex command for ffmpeg
image_inputs = []
filter_complex = ""

# Add each image as an input to ffmpeg (repeat images if necessary)
for i in range(num_images):
    image_index = i % len(images)
    image_inputs.append(f"-loop 1 -t {duration_per_image} -i \"{images[image_index]}\"")
    filter_complex += f"[{i}:v]format=yuv420p,scale=1400:1400,setsar=1[v{i}];"

# Add crossfade transitions for looping images
for i in range(num_images - 1):
    current_image = i
    next_image = i + 1
    transition = random.choice(transitions)
    fade_duration = random.uniform(transition_time_min, transition_time_max)  # Randomize the transition duration
    offset = image_duration_with_transition * i
    if i == 0:
        filter_complex += f"[v{current_image}][v{next_image}]xfade=transition={transition}:duration={fade_duration}:offset={offset}[vout{i}];"
    else:
        filter_complex += f"[vout{i-1}][v{next_image}]xfade=transition={transition}:duration={fade_duration}:offset={offset}[vout{i}];"

# Ensure the last output is correctly assigned
filter_complex += f"[vout{num_images - 2}]format=yuv420p[video]"

# Create the ffmpeg command to generate the initial video with transitions and fades (output.mp4)
ffmpeg_command = f"ffmpeg -y {' '.join(image_inputs)} -i {audio_file} -filter_complex \"{filter_complex}\" -map '[video]' -map {num_images}:a -c:v libx264 -preset slow -crf 18 -c:a aac -b:a 320k {temp_video}"

# Run the ffmpeg command to create the initial video
try:
    subprocess.run(ffmpeg_command, shell=True, check=True)
    print(f"Temporary video created successfully: {temp_video}")
except subprocess.CalledProcessError as e:
    print(f"Error occurred: {e}")
    raise

# Add fade in and fade out effects to the initial video
fade_command = f"ffmpeg -y -i {temp_video} -vf \"fade=t=in:st=0:d={fade_in_duration},fade=t=out:st={audio_duration - fade_out_duration}:d={fade_out_duration}\" -af \"afade=t=in:st=0:d={fade_in_duration},afade=t=out:st={audio_duration - fade_out_duration}:d={fade_out_duration}\" -c:v libx264 -preset slow -crf 18 -c:a aac -b:a 320k {output_video}"

# Run the ffmpeg command to add fade in/out effects
try:
    subprocess.run(fade_command, shell=True, check=True)
    print(f"Final video with transitions and fades created successfully: {output_video}")
except subprocess.CalledProcessError as e:
    print(f"Error occurred: {e}")
    raise

# Apply glitch and stuttering effects to random segments of the video to create output_glitched.mp4
segment_durations = []
if random_glitch_type == 'evenly':
    # Evenly distribute glitch effects throughout the video
    segment_positions = np.linspace(0, audio_duration - glitch_duration_max, glitch_freq)
    for pos in segment_positions:
        duration = random.uniform(glitch_duration_min, glitch_duration_max)
        segment_durations.append((pos, duration))
else:
    # Randomly distribute glitch effects
    for _ in range(glitch_freq):
        start_time = random.uniform(0, audio_duration - glitch_duration_max)  # Random start time
        duration = random.uniform(glitch_duration_min, glitch_duration_max)  # Duration between min and max
        segment_durations.append((start_time, duration))

current_input = output_video

# Reset effects available to ensure randomization every time
effects_available = [
    "frei0r=distort0r:0.5|0.01", "frei0r=nervous", "frei0r=pixeliz0r:0.5", "frei0r=kaleid0sc0pe:0.1", "frei0r=elastic_scale:0.6",
    "frei0r=invert0r:0.5", "frei0r=saturat0r:0.5", "frei0r=glitch0r:0.5|0.5|0.5|0.5", "frei0r=glow", "frei0r=scanline0r:1",
    "frei0r=contrast0r:1", "frei0r=pixs0r:1", "edgedetect=low=0.1:high=0.3", "negate", "geq=lum_expr='random(1)*255'",
    "frei0r=baltan", "frei0r=cluster:1", "frei0r=contrast0r:1", "frei0r=letterb0xed", "frei0r=vignette", "frei0r=emboss"
]

# Apply each glitch effect in sequence
for i, (start_time, duration) in enumerate(segment_durations):
    # Randomly select an effect for each glitch segment
    effect = random.choice(effects_available)
    glitched_output = f"glitched_{i}.mp4"
    filter_complex_glitch = f"[0:v]trim=start={start_time}:duration={duration},setpts=PTS-STARTPTS,{effect}[g];[0:v][g]overlay=enable='between(t,{start_time},{start_time + duration})'[v]"
    glitch_command = f"ffmpeg -y -i {current_input} -filter_complex \"{filter_complex_glitch}\" -map '[v]' -map 0:a -c:v libx264 -preset slow -crf 18 -c:a aac -b:a 320k {glitched_output}"

    # Run the ffmpeg command to apply the glitch effect
    try:
        subprocess.run(glitch_command, shell=True, check=True)
        print(f"Glitch effect applied successfully: {glitched_output}")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
        raise

    # Update the current input for the next iteration
    current_input = glitched_output

# Rename the final output to output_glitched.mp4
os.rename(current_input, output_glitched_video)

# Clean up temporary video
if os.path.exists(temp_video):
    os.remove(temp_video)

# Clean up intermediate glitched files
for i in range(glitch_freq - 1):
    intermediate_file = f"glitched_{i}.mp4"
    if os.path.exists(intermediate_file):
        os.remove(intermediate_file)
