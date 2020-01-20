import os
import random
import glob
from helpers import humanize_time, safeMakeDir, log, getVideoDuration
from helpers import log, data_read, data_write

class VideoSplitter(object):
    """docstring for VideoSplitter"""
    def __init__(self, opts):
        super(VideoSplitter, self).__init__()
        self.opts = opts

    def split(self, videoPath):
        clipList = []
        videoDuration = getVideoDuration(self.opts['videoPath'])
        numParts = self.opts['clipParts']

        safeMakeDir('%s/parts' % self.opts['jobDirectory'])

        durationsTable = [1,2,3,5,10,20,50]

        data = data_read('clipList', self.opts)

        if data:
            return data
        else:
            for i in range(0, numParts):
                clipDuration = random.choice(durationsTable)
                clipStart = random.randint(0, int(videoDuration))

                if clipStart > 10 and (clipStart + clipDuration) < videoDuration:
                    outPath = '%s/parts/out-%s-%s.mp4' % (self.opts['jobDirectory'], clipDuration, i)

                    log('clipping: %s => %s' % (clipStart, clipDuration))

                    if not os.path.exists(outPath):
                        os.popen('ffmpeg -n -ss %s -i %s -c copy -t %s %s' % (humanize_time(clipStart), videoPath, humanize_time(clipDuration), outPath))

                    clipList.append({
                        'num': i,
                        'path': outPath,
                        'start': clipStart,
                        'length': clipDuration
                    })

            data_write('clipList', clipList, self.opts)

        return clipList

