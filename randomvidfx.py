import os
import subprocess
import random

# Define file paths
audio_file = 'input.wav'
image_dir = 'alterimg/'
output_video = 'output.mp4'
temp_video = 'temp_output.mp4'

# Fade settings (user can adjust these values)
fade_in_duration = 5  # duration of fade in effect in seconds
fade_out_duration = 5  # duration of fade out effect in seconds

# Ensure the image directory exists
if not os.path.exists(image_dir):
    raise FileNotFoundError(f"Image directory '{image_dir}' not found.")

# Get all image files from the image directory
images = [os.path.join(image_dir, img) for img in sorted(os.listdir(image_dir)) if img.lower().endswith(('png', 'jpg', 'jpeg'))]

if len(images) < 2:
    raise ValueError("There should be at least two images for crossfade transitions.")

# Define available crossfade transitions (all the ones implemented in FFmpeg)
transitions = [
    'fade', 'fadeblack', 'fadewhite', 'distance', 'wipeleft', 'wiperight', 'wipeup', 'wipedown',
    'slideleft', 'slideright', 'slideup', 'slidedown', 'smoothleft', 'smoothright', 'smoothup', 'smoothdown',
    'circlecrop', 'rectcrop', 'circleclose', 'circleopen', 'horzclose', 'horzopen', 'vertclose', 'vertopen',
    'diagbl', 'diagbr', 'diagtl', 'diagtr', 'hlslice', 'hrslice', 'vuslice', 'vdslice',
    'dissolve', 'pixelize', 'radial', 'hblur', 'wipetl', 'wipetr', 'wipebl', 'wipebr',
    'fadegrays', 'squeezev', 'squeezeh', 'zoomin', 'hlwind', 'hrwind', 'vuwind', 'vdwind',
    'coverleft', 'coverright', 'coverup', 'coverdown', 'revealleft', 'revealright', 'revealup', 'revealdown'
]

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
fade_duration = 1  # duration of the crossfade in seconds

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
    if i == 0:
        filter_complex += f"[v{current_image}][v{next_image}]xfade=transition={transition}:duration={fade_duration}:offset={duration * i}[vout{i}];"
    else:
        filter_complex += f"[vout{i-1}][v{next_image}]xfade=transition={transition}:duration={fade_duration}:offset={duration * i}[vout{i}];"

# Ensure the last output is correctly assigned
filter_complex += f"[vout{num_images - 2}]format=yuv420p[video]"

# Create the ffmpeg command to generate the initial video
ffmpeg_command = f"ffmpeg -y {' '.join(image_inputs)} -i {audio_file} -filter_complex \"{filter_complex}\" -map '[video]' -map {num_images}:a -c:v libx264 -preset slow -crf 18 -c:a aac -b:a 192k -shortest {temp_video}"

# Run the ffmpeg command to create the initial video
try:
    subprocess.run(ffmpeg_command, shell=True, check=True)
    print(f"Temporary video created successfully: {temp_video}")
except subprocess.CalledProcessError as e:
    print(f"Error occurred: {e}")
    raise

# Add fade in and fade out effects to the video
fade_command = f"ffmpeg -y -i {temp_video} -filter_complex \"[0:v]fade=t=in:st=0:d={fade_in_duration},fade=t=out:st={audio_duration - fade_out_duration}:d={fade_out_duration}[v];[0:a]afade=t=in:st=0:d={fade_in_duration},afade=t=out:st={audio_duration - fade_out_duration}:d={fade_out_duration}[a]\" -map '[v]' -map '[a]' -c:v libx264 -preset slow -crf 18 -c:a aac -b:a 192k {output_video}"

# Run the ffmpeg command to add fade in/out effects
try:
    subprocess.run(fade_command, shell=True, check=True)
    print(f"Final video created successfully: {output_video}")
except subprocess.CalledProcessError as e:
    print(f"Error occurred: {e}")
    raise

# Clean up temporary video
if os.path.exists(temp_video):
    os.remove(temp_video)
