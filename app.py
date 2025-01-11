from flask import Flask, render_template, request, send_file, jsonify
from yt_dlp import YoutubeDL
from moviepy.config import change_settings
from moviepy.editor import VideoFileClip, AudioFileClip
from moviepy.video.fx import resize
import os
import re

# FFmpeg configuration
change_settings({"FFMPEG_BINARY": r"C:\ffmpeg-7.0.2-full_build\bin\ffmpeg.exe"})

app = Flask(__name__, template_folder='.')
UPLOAD_FOLDER = "cropped_videos"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_video_duration(url):
    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('duration', 0)
    except:
        return 0

@app.route('/get-video-info', methods=['POST'])
def get_video_info():
    url = request.form.get('youtube_url')
    duration = get_video_duration(url)
    return jsonify({
        'duration': duration,
        'duration_formatted': f"{duration//60}:{duration%60:02d}"
    })

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['youtube_url']
        start_time = float(request.form['start_time'])
        end_time = float(request.form['end_time'])

        try:
            # Download YouTube video
            video_id = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url).group(1)
            output_filename = f'clip_{video_id}_{start_time:.0f}_{end_time:.0f}.mp4'
            
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',  # Get best video and audio
                'outtmpl': os.path.join(UPLOAD_FOLDER, 'downloaded_video.mp4'),
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            video_path = os.path.join(UPLOAD_FOLDER, 'downloaded_video.mp4')
            output_path = os.path.join(UPLOAD_FOLDER, output_filename)

            # Calculate dimensions for 9:16 aspect ratio
            target_width = 720
            target_height = int(target_width * 16/9)  # This will be 1280

            # Crop and resize video with audio
            print("Loading video...")
            with VideoFileClip(video_path) as video:
                print("Extracting audio...")
                audio = video.audio  # Get the audio from original video
                
                print("Cropping video...")
                # Extract the subclip with audio
                cropped_video = video.subclip(start_time, end_time)
                cropped_video = cropped_video.set_audio(audio.subclip(start_time, end_time))
                
                print("Resizing video...")
                # Resize to 9:16 aspect ratio
                resized_video = resize.resize(cropped_video, width=target_width, height=target_height)
                
                print("Writing final video...")
                # Write the final video with audio
                resized_video.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile=os.path.join(UPLOAD_FOLDER, "temp-audio.m4a"),
                    remove_temp=True,
                    fps=24,  # Explicitly set FPS
                    preset='ultrafast'
                )

            # Clean up
            os.remove(video_path)
            return send_file(output_path, as_attachment=True)

        except Exception as e:
            print(f"Error occurred: {str(e)}")  # Debug print
            return f"Error: {str(e)}", 400

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)