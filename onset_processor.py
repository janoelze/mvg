import os
import random
from helpers import log, data_read, data_write
from operator import itemgetter

class OnsetProcessor(object):
    """docstring for OnsetProcessor"""
    def __init__(self, opts):
        super(OnsetProcessor, self).__init__()
        self.opts = opts

    def removeDispensableSegments(self, segments):
        segments = sorted(segments, key=itemgetter('start'))

        log('removing dispensable segments from %s segments' % len(segments))

        i = 0
        removed = 0

        for segment in segments:
            if 'delete' in segment and segment['delete']:
                if (i-1) > 0:
                    segments[i-1]['length'] = segments[i-1]['length'] + segment['length']
                    removed = removed + 1
                    del segments[i]
            i = i + 1

        log('removed %s segments' % removed)

        return segments

    def getSegments(self, onsets):
        segments = []
        previousBeat = 0
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

        return segments

    def flagDispensableSegments(self, segments, totalBeats):
        segments = sorted(segments, key=itemgetter('length'), reverse=True)

        i = 0

        log('flagging dispensable segments')

        for segment in segments:
            if i > (totalBeats * 1.1):
                segment['delete'] = True
            i = i + 1

        return segments

    def thin(self, onsets):
        log('creating segment list')

        data = data_read('onsets', self.opts)

        if data:
            return data
        else:
            totalBeats = (self.opts['audioTotalLength'] / 60) * self.opts['audioBPM']

            segments = self.getSegments(onsets)
            segments = self.flagDispensableSegments(segments, totalBeats)
            segments = self.removeDispensableSegments(segments)

            data_write('onsets', segments, self.opts)

            return segments
