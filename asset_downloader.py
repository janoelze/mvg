import os
import youtube_dl
from helpers import data_read, data_write

class AssetDownloader(object):
    """docstring for AssetDownloader"""
    def __init__(self, opts):
        super(AssetDownloader, self).__init__()
        self.opts = opts

    def fileAlreadyDownloaded(self, ytId):
        return data_read('asset-%s' % ytId, self.opts)

    def download(self, ytId, outputFileName, ydl_opts):
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            path = ydl.download(['http://www.youtube.com/watch?v=%s' % ytId])
            info_dict = ydl.extract_info(ytId, download=False)

            for filename in os.listdir(self.opts['jobDirectory']):
                if outputFileName in filename:
                    fileKey = 'asset-%s' % ytId

                    data_write(fileKey, {
                        'title': info_dict.get('title', None),
                        'id': info_dict.get("id", None),
                        'url': info_dict.get("url", None),
                        'path': '%s/%s' % (self.opts['jobDirectory'], filename)
                    }, self.opts)

                    return data_read(fileKey, self.opts)

    def getVideo(self, ytId):
        outputFileName = '%s-source' % ytId
        outtmpl = self.opts['jobDirectory'] + "/" + outputFileName + ".%(ext)s"
        existingFile = self.fileAlreadyDownloaded(ytId)

        if existingFile:
            return existingFile
        else:
            return self.download(ytId, outputFileName, {
                'format': 'bestvideo[ext=mp4]/best',
                'outtmpl': outtmpl,
            })

    def getAudio(self, ytId):
        outputFileName = '%s-source' % ytId
        outtmpl = self.opts['jobDirectory'] + "/" + outputFileName + ".%(ext)s"
        existingFile = self.fileAlreadyDownloaded(ytId)

        if existingFile:
            return existingFile
        else:
            return self.download(ytId, outputFileName, {
                'format': 'bestaudio/best',
                'outtmpl': outtmpl,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '265',
                }],
            })
