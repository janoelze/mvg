import os
import random
from helpers import log, data_read, data_write

from moviepy.editor import *
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
from scenedetect.stats_manager import StatsManager

class ClipMatching(object):
    """docstring for ClipMatching"""
    def __init__(self, opts):
        super(ClipMatching, self).__init__()
        self.opts = opts

    def match(self, clipList, filteredSegments, clipCache):
        maxDuration = 0

        for clip in clipList:
            if clip['length'] > maxDuration:
                maxDuration = clip['length']

        skip = 0
        selectedClipList = []
        currentSegment = 0
        lastEvent = -1
        previousClip = False
        currentClipIndex = random.randrange(len(clipList))
        changeScene = int(len(filteredSegments)/10)

        for segment in filteredSegments:
            foundClip = False
            retries = 0
            maxDelta = 4

            if random.randint(0, 10) > 8:
                maxDelta = 6

            i = 0

            # check if we passed an event
            for event in self.opts['events']:
                if segment['start'] > event and i > lastEvent:
                    lastEvent = i
                    currentClipIndex = random.randrange(len(clipList))
                    log('event trigger! changing currentSceneIndex to: %s' % (currentClipIndex))
                i = i + 1

            if segment['length'] > maxDuration:
                foundClip = random.choice(clipList)

            while not foundClip:
                delta = random.randint(maxDelta*-1, maxDelta)
                index = (currentClipIndex+delta)

                if index < len(clipList) and index > 0:
                    if clipList[currentClipIndex+delta]['length'] > (segment['length']+0.09):
                        candidate = clipList[currentClipIndex+delta]

                        if candidate['path'] in clipCache:
                            foundClip = candidate
                            foundScene = True
                        else:
                            retries = retries + 1
                    else:
                        retries = retries + 1
                else:
                    retries = retries + 1

                if retries > 20:
                    print 'more delta', maxDelta
                    maxDelta = maxDelta + 1
                    retries = 0

            log('found clip: %s (duration: %s, requred duration: %s)' % (foundClip['num'], foundClip['length'], segment['length']))

            if changeScene < 0:
                changeScene = random.randint(int(len(filteredSegments) * 0.02), int(len(filteredSegments) * 0.1))

                # newScene = False

                # while not newScene:
                #     checkIndex = random.randrange(len(clipList))

                #     print checkIndex

                #     if checkIndex > (currentClipIndex+4) and checkIndex < (currentClipIndex-4):
                #         newScene = checkIndex

                # currentClipIndex = newScene

                currentClipIndex = random.randrange(len(clipList))

                log('changing currentClipIndex to: %s' % (currentClipIndex))
            else:
                changeScene = changeScene - 1

            videoclip = clipCache[foundClip['path']]
            videoclip = videoclip.subclip(0, segment['length'])
            videoclip = videoclip.fx(vfx.loop, duration=segment['length'])

            selectedClipList.append(videoclip)

            currentSegment = currentSegment + 1

        return selectedClipList
