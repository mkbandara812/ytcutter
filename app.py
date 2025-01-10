from flask import Flask, render_template, request, send_file, jsonify
from yt_dlp import YoutubeDL
from moviepy.editor import VideoFileClip
from moviepy.video.fx import resize
import os
import re

app = Flask(__name__, template_folder='.')  # Change this to look in the main folder
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
                'format': 'mp4',
                'outtmpl': os.path.join(UPLOAD_FOLDER, 'downloaded_video.mp4')
            }
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            video_path = os.path.join(UPLOAD_FOLDER, 'downloaded_video.mp4')
            output_path = os.path.join(UPLOAD_FOLDER, output_filename)

            # Crop and resize video
            with VideoFileClip(video_path) as video:
                cropped_video = video.subclip(start_time, end_time)
                cropped_video = resize.resize(cropped_video, width=1280)
                cropped_video.write_videofile(output_path, codec='libx264')

            os.remove(video_path)
            return send_file(output_path, as_attachment=True)

        except Exception as e:
            return f"Error: {str(e)}", 400

    return render_template('index.html')  # Ensure index.html is in the main folder

if __name__ == '__main__':
    app.run(debug=True)
