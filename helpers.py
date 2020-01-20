import os
import datetime
import json

from moviepy.editor import *
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
from scenedetect.stats_manager import StatsManager

def data_read(key, opts):
    filePath = '%s/data/%s.json' % (opts['jobDirectory'], key)

    if os.path.exists(filePath):
        with open(filePath) as f:
            return json.load(f)
    else:
        return False

def data_write(key, data, opts):
    dataDir = '%s/data' % opts['jobDirectory']
    dataPath = '%s/%s.json' % (dataDir, key)

    if not os.path.exists(dataDir):
        safeMakeDir(dataDir)

    with open(dataPath, 'w') as f:
        json.dump(data, f)

def humanize_time(secs):
    mins, secs = divmod(secs, 60)
    hours, mins = divmod(mins, 60)
    return '%02d:%02d:%02d' % (hours, mins, secs) + str('.0')

def safeMakeDir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def openFile(path):
    output = os.popen('open "%s";' % (path))

def log(str):
    print '>> %s: %s' % (datetime.datetime.now().strftime('%I:%M%p'), str)

def getVideoDuration(videoPath):
    log('getVideoDuration')
    output = os.popen('ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 %s' % (videoPath)).read()
    return float(output)

def mergeAudioVideo(audioPath, videoPath, targetPath):
    log('muxing video')
    output = os.popen('ffmpeg -y -i "%s" -r 30 -i "%s" -shortest -c:v copy "%s"' % (audioPath, videoPath, targetPath)).read()

def fetch_videos(clipList):
    clipCache = {}

    for clip in clipList:
        res = loadVideoSafe(clip['path'])

        if res != False:
            clipCache[clip['path']] = res

    return clipCache

def loadVideoSafe(path):
    try:
        if os.path.exists(path):
            log('checking: %s' % path)

            videoclip = VideoFileClip(path)

            if videoclip.duration:
                return videoclip
        else:
            return False
    except Exception as e:
        return False
