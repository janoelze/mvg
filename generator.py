# pip install pytube
# aubio onset /Users/jan.oelze/Downloads/f8f57c888997479436508a740dab407f3f73378c.mp3
# from __future__ import print_function

# __future__ import unicode_literals

import aubio
import scenedetect
from pytube import YouTube
from operator import itemgetter
import random
from itertools import cycle

import datetime
import statistics
import youtube_dl
import csv
import math
import os
import sys
import argparse
import subprocess
import re
import json
import wave

from moviepy.editor import *
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
from scenedetect.stats_manager import StatsManager

from scenedetect.detectors.content_detector import ContentDetector

from aubio import source, tempo
from numpy import median, diff

from pydub import AudioSegment

import matplotlib.pyplot as plt

import warnings
warnings.simplefilter('module')

def get_file_bpm(path, params=None):
    log('getting audio bpm')
    """ Calculate the beats per minute (bpm) of a given file.
        path: path to the file
        param: dictionary of parameters
    """
    if params is None:
        params = {}
    # default:
    samplerate, win_s, hop_s = 44100, 1024, 512
    if 'mode' in params:
        if params.mode in ['super-fast']:
            # super fast
            samplerate, win_s, hop_s = 4000, 128, 64
        elif params.mode in ['fast']:
            # fast
            samplerate, win_s, hop_s = 8000, 512, 128
        elif params.mode in ['default']:
            pass
        else:
            raise ValueError("unknown mode {:s}".format(params.mode))
    # manual settings
    if 'samplerate' in params:
        samplerate = params.samplerate
    if 'win_s' in params:
        win_s = params.win_s
    if 'hop_s' in params:
        hop_s = params.hop_s

    s = source(path, samplerate, hop_s)
    samplerate = s.samplerate
    o = tempo("specdiff", win_s, hop_s, samplerate)
    # List of beats, in samples
    beats = []
    # Total number of frames read
    total_frames = 0

    while True:
        samples, read = s()
        is_beat = o(samples)
        if is_beat:
            this_beat = o.get_last_s()
            beats.append(this_beat)
            #if o.get_confidence() > .2 and len(beats) > 2.:
            #    break
        total_frames += read
        if read < hop_s:
            break

    def beats_to_bpm(beats, path):
        # if enough beats are found, convert to periods then to bpm
        if len(beats) > 1:
            if len(beats) < 4:
                print("few beats found in {:s}".format(path))
            bpms = 60./diff(beats)
            return median(bpms)
        else:
            print("not enough beats found in {:s}".format(path))
            return 0

    return beats_to_bpm(beats, path)

def log(str):
    print '>> %s: %s' % (datetime.datetime.now().strftime('%I:%M%p'), str)

def splitScenes(videoPath, jobDirectory):
    log('splitting scenes')
    return os.system('scenedetect --input "%s" --output "%s" detect-content list-scenes split-video' % (videoPath, jobDirectory))

def getAudio(audioId, jobDirectory):
    log('getting audio')

    outputFileName = '%s-audio-source' % (audioId)
    outtmpl = jobDirectory + "/" + outputFileName + ".%(ext)s"

    for filename in os.listdir(jobDirectory):
        if outputFileName in filename:
            log('audio is already downloaded')
            return '%s/%s' % (jobDirectory, filename)

    log('downloading audio')

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': outtmpl,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '265',
        }],
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        path = ydl.download(['http://www.youtube.com/watch?v=%s' % audioId])

        for filename in os.listdir(jobDirectory):
            if outputFileName in filename:
                return '%s/%s' % (jobDirectory, filename)

def getVideo(videoId, jobDirectory):
    log('getting video')

    outputFileName = '%s-video-source' % (videoId)
    outtmpl = jobDirectory + "/" + outputFileName + ".%(ext)s"

    for filename in os.listdir(jobDirectory):
        if outputFileName in filename:
            log('video is already downloaded')
            return '%s/%s' % (jobDirectory, filename)

    log('downloading video')

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]/best',
        'outtmpl': outtmpl,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        path = ydl.download(['http://www.youtube.com/watch?v=%s' % videoId])

        for filename in os.listdir(jobDirectory):
            if outputFileName in filename:
                return '%s/%s' % (jobDirectory, filename)

def extractOnsets(audioPath):
    log('extracting onsets')
    output = os.popen('aubio onset -t 0.8 -i "%s"' % audioPath).read()
    return output.split()

def loadVideoSafe(path):
    try:
        log('checking: %s' % path)
        videoclip = VideoFileClip(path)

        if videoclip.duration:
            return videoclip
    except Exception as e:
        return False

def mergeAudioVideo(audioPath, videoPath, targetPath):
    log('muxing video')
    output = os.popen('ffmpeg -y -i "%s" -r 30 -i "%s" -shortest -c:v copy "%s"' % (audioPath, videoPath, targetPath)).read()

def getAudioLength(audioPath):
    log('getting audio length')
    output = os.popen('ffprobe -i "%s"  -show_entries format=duration -v quiet -of csv="p=0"' % (audioPath)).read()
    return float(output)

def humanize_time(secs):
    mins, secs = divmod(secs, 60)
    hours, mins = divmod(mins, 60)
    return '%02d:%02d:%02d' % (hours, mins, secs) + str('.0')

def get_segment_stats(audio_segment):
    log('getting audio stats')

    # snips = snippet_pathfinder(l, title, condition)
    # audio_segment = AudioSegment.from_wav(audioWavPath)

    audioLength = len(audio_segment)
    audioSeconds = audioLength/1000

    # print audioLength
    timeSlice = 500
    offset = 0
    run = True
    rmsSpec = []
    # first_10_seconds = audio_segment[:ten_seconds]
    while run:
        if (offset+timeSlice) < audioLength:
            rms = audio_segment[offset:offset+timeSlice].rms
            rms = round(rms / 200)
            rmsSpec.append(rms)
        else:
            run = False
        offset = offset + timeSlice

    lastFive = []
    smoothed = []
    i = 0
    num = 2
    for rms in rmsSpec:
        i = i + 1
        lastFive.append(int(rms))
        if i >= num:
            smoothed.append(int(median(lastFive[-num:])))
            i = 0
            # treshold = medianValue * 0.1

    stats = {
        'min': min(smoothed),
        'max': max(smoothed),
        'median': median(smoothed)
    }

    events = []

    treshold = int(stats['max'] * 0.15)
    previousValue = 0
    i = 0
    lastEvent = 0
    for val in smoothed:
        i = i + 1
        event = False
        eventText = ' '
        currentSeconds = (audioSeconds / len(smoothed)) * i
        change = abs(previousValue-val)

        if change > treshold and lastEvent < (i-2):
            event = True
            lastEvent = i
            eventText = 'E'
            events.append(currentSeconds)

        print "%s (%ss): %s \t %s" % (eventText, currentSeconds, change, '|' * int(val))
        previousValue = val

    return events

def main():
    videoId = 'DksSPZTZES0' # cry me a river
    videoId = '6Uqb4Jy0GTg' # el topo trailer
    # videoId = 'R8ZF_ISU2Xg' # beyonce
    # videoId = 'D-9T7LnEUuE' # papi
    # videoId = 'zCy5WQ9S4c0' # terminator
    # videoId = 'QdzNo_PAjOI' # computer
    # videoId = '4m1EFMoRFvY' # ring on it
    # videoId = 'fiaWsgtJrNI' # nick land
    # videoId = '5h9EQaEl55o' # tom green
    # videoId = 'x1YkHJJi-tc' # forbidden colors
    # videoId = '9qJKxaWb0_A'
    # videoId = 'zCy5WQ9S4c0'
    # videoId = 'wVQn1h3Rfmk'
    videoId = 'MdWAViiisek'
    # videoId = '3evdupFlpv4'
    # videoId = 'SKy_87XoVDk' # mode
    videoId = '5PJZz04JGjs' # seinfeld

    audioId = 'GsM1wgL1JDg' #DeineLtan
    audioId = 'cwQgjq0mCdE' # robyn

    jobDirectory = 'jobs/%s' % videoId
    sceneFilePath = '%s/source-Scenes.csv' % jobDirectory

    if not os.path.exists(jobDirectory):
        log('creating job directory')
        os.makedirs(jobDirectory)

    videoPath = getVideo(videoId, jobDirectory)
    audioPath = getAudio(audioId, jobDirectory)

    log('videoPath is: %s' % videoPath)
    log('audioPath is: %s' % audioPath)

    onsets = extractOnsets(audioPath)
    audioLength = getAudioLength(audioPath)
    audioBPM = get_file_bpm(audioPath)
    totalBeats = (audioLength / 60) * audioBPM

    log('detected %s onsets' % len(onsets))
    log('audioLength is: %s' % audioLength)
    log('audioBPM is: %s' % audioBPM)
    log('totalBeats is: %s' % totalBeats)

    log('init AudioSegment')

    audioSegment = AudioSegment.from_wav(audioPath)

    events = get_segment_stats(audioSegment)

    # if not os.path.exists(sceneFilePath):
    #     res = splitScenes(videoPath, jobDirectory)

    durationStr = os.popen('ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 %s' % (videoPath)).read()
    duration = float(durationStr)+1
    numParts = 120
    # partLength = duration / numParts

    clipList = []
    masterClip = VideoFileClip(videoPath)

    # print duration

    clipCache = {}

    for i in range(0, numParts):
        clipDuration = random.randint(0, 20)
        clipStart = random.randint(0, int(duration))

        if random.randint(0, 20) > 15:
            clipDuration = random.randint(0, 50)

        if (clipStart+clipDuration) < duration:
            outPath = '%s/out-%s.mp4' % (jobDirectory, i)
            # print humanize_time(clipStart)

            if not os.path.exists(outPath):
                durationStr = os.popen('ffmpeg -n -ss %s -i %s -c copy -t %s %s' % (humanize_time(clipStart), videoPath, humanize_time(clipDuration), outPath)).read()

            res = loadVideoSafe(outPath)

            if res:
                clipCache[outPath] = res

                clipList.append({
                    'num': i,
                    'path': '%s/out-%s.mp4' % (jobDirectory, i),
                    'start': clipStart,
                    'length': clipDuration
                })

    clipList = sorted(clipList, key=itemgetter('start'))

    log('found %s clips' % len(clipList))

    log('creating segment list')

    previousBeat = 0
    segments = []
    i = 0

    for onset in onsets:
        onset = float(onset)
        length = onset - previousBeat

        if onset == 0 and (i+1) < (len(onsets)-1):
            length = float(onsets[i+1])

        segments.append({
            'start': onset,
            'length': length
            })

        previousBeat = onset
        i = i + 1

    log('thinning %s segments' % len(segments))

    segments = sorted(segments, key=itemgetter('length'), reverse=True)

    i = 0
    remove = 0
    for segment in segments:
        if i > totalBeats:
            segment['delete'] = True
            remove = remove + 1
        i = i + 1

    segments = sorted(segments, key=itemgetter('start'))

    log('flagged %s segments for deletion' % remove)

    i = 0

    log('removing segments')

    for segment in segments:
        if 'delete' in segment and segment['delete']:
            if (i-1) > 0:
                segments[i-1]['length'] = segments[i-1]['length'] + segment['length']
                del segments[i]
        i = i + 1

    log('finished thinning, %s segments remaining' % len(segments))

    lengthValues = []

    for segment in segments:
        lengthValues.append(segment['length'])

    medianLength = median(lengthValues)

    log('median segment length is: %s' % medianLength)

    skip = 0
    segmentI = 0
    previousScene = False
    currentClipIndex = random.randrange(len(clipList))
    changeScene = int(len(segments)/10)
    maxDuration = 0
    maxDuration = 0

    for clip in clipList:
        if clip['length'] > maxDuration:
            maxDuration = clip['length']

    log('finding segment video candidates')
    log('currentSceneIndex is: %s' % (currentClipIndex))

    selectedClipList = []
    lastClip = False
    lastEvent = -1

    # print clipList

    for segment in segments:
        clip = False
        retries = 0
        maxDelta = 4
        loopDuration = 0

        if random.randint(0, 10) > 8:
            maxDelta = 6

        i = 0
        for event in events:
            if segment['start'] > event and i > lastEvent:
                lastEvent = i
                currentClipIndex = random.randrange(len(clipList))
                log('event trigger')
                log('changing currentSceneIndex to: %s' % (currentClipIndex))
            i = i + 1

        # log('search for: %s' % (segment['length']))

        if segment['length'] > maxDuration:
            clip = random.choice(clipList)

        while not clip:
            delta = random.randint(maxDelta*-1, maxDelta)
            index = (currentClipIndex+delta)

            if index < len(clipList) and index > 0:
                if clipList[currentClipIndex+delta]['length'] > (segment['length']+0.09):
                    candidate = clipList[currentClipIndex+delta]
                    # clipCache[candidate['path']] = res
                    clip = candidate
                    foundScene = True

                    # if candidate['path'] not in clipCache:
                    #     print 'checking', candidate

                    #     res = loadVideoSafe(candidate)

                    #     print 'res is', res

                    #     if res:
                    #         clipCache[candidate['path']] = res
                    #         lastClip = candidate
                    #         clip = candidate
                    #         foundScene = True
                    #     else:
                    #         del clipList[currentClipIndex+delta]
                    #         retries = retries + 1
                    #     # try:
                    #     #     print 'checking', candidate

                    #     #     videoclip = VideoFileClip(candidate['path'])
                    #     #     clipCache[candidate['path']] = videoclip

                    #     #     print videoclip.duration

                    #     #     foundScene = True
                    #     #     clip = candidate
                    #     # except Exception as e:
                    #     #     print e
                    #     #     pass
                    #     #     # sys.exit()
                else:
                    retries = retries + 1
            else:
                retries = retries + 1

            if retries > 20:
                # clip = lastClip
                print 'more delta', maxDelta
                maxDelta = maxDelta + 1
                retries = 0

        log('found clip: %s (duration: %s, requred duration: %s)' % (clip['num'], clip['length'], segment['length']))

        if changeScene < 0:
            changeScene = random.randint(int(len(segments) * 0.02), int(len(segments) * 0.1))
            currentSceneIndex = random.randrange(len(clipList))
            log('changing currentSceneIndex to: %s' % (currentSceneIndex))
        else:
            changeScene = changeScene - 1

        # print clip

        # sys.exit()

        # print clip

        # print clip['start']

        # videoclip = masterClip.subclip(0, 10)

        # videoclip = masterClip.subclip(clip['start']+2, 4)

        # if clip['path'] in clipCache:
            
        # else:
        #     log('loading videoclip: %s' % (clip['path']))
        #     # print clip['start'], segment['length']
        #     # videoclip = masterClip.subclip(0, 10)
        #     # clipCache[clip['num']] = videoclip

        #     try:
        #         videoclip = VideoFileClip(clip['path'])
        #     except Exception as e:
        #         # print e
        #         sys.exit()

        #     clipCache[clip['path']] = videoclip

        # print 'adding', clip['path']

        videoclip = clipCache[clip['path']]
        videoclip = videoclip.subclip(0, segment['length'])
        videoclip = videoclip.fx(vfx.loop, duration=segment['length'])

        selectedClipList.append(videoclip)

        segmentI = segmentI + 1

        # break

        # if segmentI > 30:
        #     break

    videoTargetPath = "%s/export.mp4" % jobDirectory
    videoTargetPathWithAudio = "%s/export-audio.mp4" % jobDirectory

    log('concatenatinating %s videoclips' % (len(selectedClipList)))

    video = concatenate_videoclips(selectedClipList)

    log('writing video file to: %s' % (videoTargetPath))

    video.write_videofile(videoTargetPath, audio=False)

    mergeAudioVideo(audioPath, videoTargetPath, videoTargetPathWithAudio)

if __name__ == '__main__':
    main()
