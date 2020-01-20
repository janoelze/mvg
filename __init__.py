import os
import sys
from slugify import slugify

from file_reader import FileReader
from asset_downloader import AssetDownloader
from audio_analysis import AudioAnalysis
from image_analysis import ImageAnalysis
from onset_processor import OnsetProcessor
from video_splitter import VideoSplitter
from clip_matching import ClipMatching

from helpers import openFile, log, safeMakeDir, mergeAudioVideo, fetch_videos

from moviepy.editor import *
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
from scenedetect.stats_manager import StatsManager

def main():
    opts = {
        'videoId': 'UNq9gmY_Oz4',
        'audioId': 'uiu-mdOmFVs',
        'videoWidth': 720,
        'clipParts': 120
    }

    opts['jobDirectory'] = 'jobs/%s-%s' % (opts['audioId'], opts['videoId'])

    safeMakeDir(opts['jobDirectory'])

    WORKING_DIR = opts['jobDirectory']

    assetDownloader = AssetDownloader(
        opts=opts
        )

    audioData = {}

    audioData = assetDownloader.getAudio(opts['audioId'])
    videoData = assetDownloader.getVideo(opts['videoId'])

    opts['audioPath'] = audioData['path']
    opts['videoPath'] = videoData['path']

    opts['audioPath'] = 'hg.wav'
    # opts['videoPath'] = 'wavemotioninterference.mp4'
    audioData['title'] = 'out'

    # imageAnalysis = ImageAnalysis(opts=opts)

    # res = imageAnalysis.analyse_spectrogram('white.png')

    audioAnalysis = AudioAnalysis(opts=opts)

    opts['events'] = audioAnalysis.getEvents()
    opts['audioTotalLength'] = audioAnalysis.getLength()
    opts['audioOnsets'] = audioAnalysis.getOnsets()
    opts['audioBPM'] = audioAnalysis.getBPM()

    videoSplitter = VideoSplitter(opts=opts)

    clipList = videoSplitter.split(opts['videoPath'])

    onsetProcessor = OnsetProcessor(opts=opts)

    filteredSegments = onsetProcessor.thin(opts['audioOnsets'])

    clipMatching = ClipMatching(opts=opts)

    clipCache = fetch_videos(clipList)

    selectedClipList = clipMatching.match(clipList, filteredSegments, clipCache)

    opts['videoTargetPath'] = "%s/export.mp4" % opts['jobDirectory']
    opts['videoTargetPathWithAudio'] = "%s/%s.mp4" % (opts['jobDirectory'], slugify(audioData['title']))

    log('concatenatinating %s videoclips' % (len(selectedClipList)))

    video = concatenate_videoclips(selectedClipList)

    video.resize(width=opts['videoWidth'])

    log('writing video file to: %s' % (opts['videoTargetPath']))

    video.write_videofile(opts['videoTargetPath'], audio=False)

    mergeAudioVideo(opts['audioPath'], opts['videoTargetPath'], opts['videoTargetPathWithAudio'])

    openFile(opts['videoTargetPathWithAudio'])

if __name__ == '__main__':
    main()
