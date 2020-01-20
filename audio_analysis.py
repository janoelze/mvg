import os
from pydub import AudioSegment
from helpers import log
from numpy import median, diff
from aubio import source, tempo

class AudioAnalysis(object):
    """docstring for AssetDownloader"""
    def __init__(self, opts):
        super(AudioAnalysis, self).__init__()
        self.opts = opts

    def getEvents(self):
        log('getting audio stats')

        audioSegment = AudioSegment.from_wav(self.opts['audioPath'])

        # snips = snippet_pathfinder(l, title, condition)
        # audio_segment = AudioSegment.from_wav(audioWavPath)

        audioLength = len(audioSegment)
        audioSeconds = audioLength/1000

        # print audioLength
        timeSlice = 500
        offset = 0
        run = True
        rmsSpec = []
        # first_10_seconds = audioSegment[:ten_seconds]
        while run:
            if (offset+timeSlice) < audioLength:
                rms = audioSegment[offset:offset+timeSlice].rms
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

    def getLength(self):
        log('getting audio length')
        output = os.popen('ffprobe -i "%s"  -show_entries format=duration -v quiet -of csv="p=0"' % (self.opts['audioPath'])).read()
        return float(output)

    def getOnsets(self):
        log('extracting onsets')
        output = os.popen('aubio onset -t 0.8 -i "%s"' % self.opts['audioPath']).read()
        return output.split()

    def getBPM(self):
        path = self.opts['audioPath']
        log('getting audio bpm')
        """ Calculate the beats per minute (bpm) of a given file.
            path: path to the file
            param: dictionary of parameters
        """
        params = None
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
