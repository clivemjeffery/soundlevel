import pyaudio
import pydub
import wave
import signal
import sys
from io import BytesIO
from mote import Mote

FRAMES_PER_BUFFER = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
AUDIO_SEGMENT_LENGTH = 0.5

_soundmeter = None
mote = Mote()
mote.configure_channel(1, 16, False)
mote.clear()

def moteshow(n):
	# show n lights on the strip
	mote.clear()
	if (n > -1) and (n < 17):
		for pixel in range(n):
			mote.set_pixel(1, pixel, 255, 0, 0)
	mote.show()

class Meter(object):

	class StopException(Exception):
		pass

	def __init__(self, segment_length=None):
		"""
		:param float segment_length: A float representing `AUDIO_SEGMENT_LENGTH`
		"""
		print("__init__")
		global _soundmeter
		_soundmeter = self  # Register this object globally for use in signal handlers (see below)
		self.output = BytesIO()
		self.audio = pyaudio.PyAudio()
		self.stream = self.audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=FRAMES_PER_BUFFER)
		self.segment_length = segment_length
		self.is_running = False
		self._graceful = False  # Graceful stop switch
		self._data = {}

	def record(self):
		"""
		Record PyAudio stream into StringIO output
		This generator keeps stream open; the stream is closed in stop()
		"""
		while True:
			frames = []
			self.stream.start_stream()
			for i in range(self.num_frames):
				data = self.stream.read(FRAMES_PER_BUFFER)
				frames.append(data)
			self.output.seek(0)
			w = wave.open(self.output, 'wb')
			w.setnchannels(CHANNELS)
			w.setsampwidth(self.audio.get_sample_size(FORMAT))
			w.setframerate(RATE)
			w.writeframes(b''.join(frames))
			w.close()
			yield

	def start(self):
		segment = self.segment_length or AUDIO_SEGMENT_LENGTH
		self.num_frames = int(RATE / FRAMES_PER_BUFFER * segment)
		try:
			self.is_running = True
			record = self.record()
			while not self._graceful:
				next(record)  # Record stream `AUDIO_SEGMENT_LENGTH' long in the generator method 'record'
				data = self.output.getvalue()
				segment = pydub.AudioSegment(data)
				rms = segment.rms
				dbfs = segment.dBFS
				self.meter(rms, dbfs)
			self.is_running = False
			self.stop()

		except self.__class__.StopException:
			self.is_running = False
			self.stop()

	def meter(self, rms, dbfs):
		if not self._graceful:
			m100 = "-" * (100 + int(round(dbfs)))
			m16 = int(round(16 * (1 + dbfs/70))) # how many lights to light?
			sys.stdout.write("\r{0} - {1}".format(m16, dbfs))
			sys.stdout.flush()
			moteshow(m16)
			
	def graceful(self):
		"""Graceful stop so that the while loop in start() will stop after the
		 current recording cycle"""
		self._graceful = True

	def stop(self):
		"""Stop the stream and terminate PyAudio"""
		if not self._graceful:
			self._graceful = True
		self.stream.stop_stream()
		self.audio.terminate()
		mote.clear()

def main():
	m = Meter()
	m.start()

# Signal handlers
def sigint_handler(signum, frame):
	sys.stdout.write('\n')
	_soundmeter.graceful()

# Register signal handlers
signal.signal(signal.SIGINT, sigint_handler)

if __name__=="__main__":
	main()