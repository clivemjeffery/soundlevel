import pyaudio
import pydub
import wave
import signal
import sys
from io import BytesIO
from mote import Mote
from accumulator import Accumulator

FRAMES_PER_BUFFER = 2048
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
AUDIO_SEGMENT_LENGTH = 0.5 # seconds
ACCUMULATE = 240 # segments (i.e. twice the seconds for desired mins)

_soundmeter = None
mote = Mote()
mote.configure_channel(1, 16, False)
mote.configure_channel(2, 16, False)
mote.configure_channel(3, 16, False)
mote.configure_channel(4, 16, False)
mote.clear()

def clamp16(n):
    return max(min(16, n), 0)

def moteset(n, r, g, b):
	# strip 1 (increasing pixels)
	r1 = clamp16(n) # values between 1 and 16
	for pixel in range(r1):
		mote.set_pixel(1, pixel, r, g, b)
	# strip 2 (inc.)
	r2 = clamp16(n-16) # values between 17 and 32
	for pixel in range(r2):
		mote.set_pixel(2, pixel, r, g, b)
	# strip 3 (decreasing pixels)
	r3 = clamp16(n-32) # values between 33 and 48
	for pixel in range(15, 15-r3, -1):
		mote.set_pixel(3, pixel, r, g, b)
	# strip 4 (dec.)
	r4 = clamp16(n-48) # values betwene 47 and 64
	for pixel in range(15, 15-r4, -1):
		mote.set_pixel(4, pixel, r, g, b)
	#print("moteplot({0},{1},{2},{3})\t:\tr1={4}\tr2={5}\tr3={6}\tr4={7}".format(n, r, g, b, r1, r2, r3, r4))
		

def moteflash():
	mote.clear()
	for strip in range(1,5):
		for pixel in range(16):
			mote.set_pixel(strip, pixel, 0, 0, 255)
	mote.show()

def moteplot(x, xmin, xmax, r, g, b):
	p = int(round((x - xmin) * (64 / (xmax-xmin))))
	moteset(p, r, g, b)

def motemeter(value):
	bright = 127
	#print("motemeter({0})".format(value))
	mote.clear()
	if value > 128:
		value = 128
	moteplot(value, 0, 64, 0, bright, 0)
	moteplot(value, 65, 96, bright, bright, 0)
	moteplot(value, 97, 128, bright, 0, 0)
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
		self.acc = Accumulator(-100,0)
		self.points = 0

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
			if self.acc.n < ACCUMULATE:
				self.acc.addValue(dbfs)
			else:
				if self.acc.mean() < -40:
					self.points = self.points + 1
					moteflash()
				sys.stdout.write("\nAccumulation: min{:+8.3f}\tmax{:+8.3f}\tmean{:+8.3f}\tpoints{:4d}\n".format(self.acc.min_value, self.acc.max_value, self.acc.mean(), self.points))
				self.acc = Accumulator(-100,0) # reset accumulator
			mm = 128 + dbfs # motemeter value
			sys.stdout.write("\r{:+08.3f}\t{:+08.3f}".format(dbfs,mm))
			sys.stdout.flush()
			motemeter(mm)
			
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
		sys.stdout.write("\nPoints={0}\n".format(self.points))
		mote.clear()
		mote.show()

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
