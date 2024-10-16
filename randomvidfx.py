import os
import subprocess
import random

# Define file paths
audio_file = 'input.wav'
image_dir = 'alterimg/'
output_video = 'output.mp4'
temp_video = 'temp_output.mp4'
output_glitched_video = 'output_glitched.mp4'

# Fade and transition settings (user can adjust these values)
fade_in_duration = 2  # duration of fade in effect in seconds
fade_out_duration = 2  # duration of fade out effect in seconds
transition_time_min = 0.5  # minimum duration of each transition in seconds
transition_time_max = 2.0  # maximum duration of each transition in seconds

# Ensure the image directory exists
if not os.path.exists(image_dir):
    raise FileNotFoundError(f"Image directory '{image_dir}' not found.")

# Get all image files from the image directory
images = [os.path.join(image_dir, img) for img in sorted(os.listdir(image_dir)) if img.lower().endswith(('png', 'jpg', 'jpeg'))]

if len(images) < 2:
    raise ValueError("There should be at least two images for crossfade transitions.")

# Define available crossfade transitions (all the ones implemented in FFmpeg excluding slide and wipe)
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

# Generate filter complex command for ffmpeg
image_inputs = []
filter_complex = ""
duration = 5  # duration of each image in seconds
# Randomly set transition duration within the user-defined range
fade_duration = random.uniform(transition_time_min, transition_time_max)  # duration of the crossfade in seconds

# Calculate the total number of images needed to match the audio duration
num_images = int(audio_duration // (duration - fade_duration)) + 1

# Add each image as an input to ffmpeg (repeat images if necessary)
for i in range(num_images):
    image_index = i % len(images)
    image_inputs.append(f"-loop 1 -t {duration + fade_duration} -i \"{images[image_index]}\"")
    filter_complex += f"[{i}:v]format=yuv420p,scale=1400:1400,setsar=1[v{i}];"

# Add crossfade transitions for looping images
for i in range(num_images - 1):
    current_image = i
    next_image = i + 1
    transition = random.choice(transitions)
    fade_duration = random.uniform(transition_time_min, transition_time_max)  # Randomize the transition duration
    if i == 0:
        filter_complex += f"[v{current_image}][v{next_image}]xfade=transition={transition}:duration={fade_duration}:offset={duration * i}[vout{i}];"
    else:
        filter_complex += f"[vout{i-1}][v{next_image}]xfade=transition={transition}:duration={fade_duration}:offset={duration * i}[vout{i}];"

# Ensure the last output is correctly assigned
filter_complex += f"[vout{num_images - 2}]format=yuv420p[video]"

# Create the ffmpeg command to generate the initial video
ffmpeg_command = f"ffmpeg -y {' '.join(image_inputs)} -i {audio_file} -filter_complex \"{filter_complex}\" -map '[video]' -map {num_images}:a -c:v libx264 -preset slow -crf 18 -c:a aac -b:a 320k -shortest {temp_video}"

# Run the ffmpeg command to create the initial video
try:
    subprocess.run(ffmpeg_command, shell=True, check=True)
    print(f"Temporary video created successfully: {temp_video}")
except subprocess.CalledProcessError as e:
    print(f"Error occurred: {e}")
    raise

# Add fade in and fade out effects to the video
fade_command = f"ffmpeg -y -i {temp_video} -filter_complex \"[0:v]fade=t=in:st=0:d={fade_in_duration},fade=t=out:st={audio_duration - fade_out_duration}:d={fade_out_duration}[v];[0:a]afade=t=in:st=0:d={fade_in_duration},afade=t=out:st={audio_duration - fade_out_duration}:d={fade_out_duration}[a]\" -map '[v]' -map '[a]' -c:v libx264 -preset slow -crf 18 -c:a aac -b:a 320k {output_video}"

# Run the ffmpeg command to add fade in/out effects
try:
    subprocess.run(fade_command, shell=True, check=True)
    print(f"Final video created successfully: {output_video}")
except subprocess.CalledProcessError as e:
    print(f"Error occurred: {e}")
    raise

# Apply glitch and stuttering effects to random segments of the video
num_glitches = random.randint(2, 5)  # Random number of glitches between 2 and 5
current_input = output_video
segment_durations = []
for _ in range(num_glitches):
    start_time = random.uniform(0, audio_duration - 3)  # Random start time
    duration = random.uniform(1, 3)  # Duration between 1 and 3 seconds
    segment_durations.append((start_time, duration))

# Apply each glitch effect in sequence
for i, (start_time, duration) in enumerate(segment_durations):
    effect = random.choice(["tblend=all_mode=and", "fps=fps=10", "hflip", "vflip", "edgedetect=low=0.1:high=0.3"])
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
for i in range(num_glitches - 1):
    intermediate_file = f"glitched_{i}.mp4"
    if os.path.exists(intermediate_file):
        os.remove(intermediate_file)
