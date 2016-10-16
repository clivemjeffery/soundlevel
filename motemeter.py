import time
from mote import Mote

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
	print("moteplot({0},{1},{2},{3})\t:\tr1={4}\tr2={5}\tr3={6}\tr4={7}".format(n, r, g, b, r1, r2, r3, r4))
		

def moteplotgreen():
	for strip in range(1,5):
		for pixel in range(16):
			mote.set_pixel(strip, pixel, 0, 255, 0)

def moteplot(x, xmin, xmax, r, g, b):
	p = int(round((x - xmin) * (64 / (xmax-xmin))))
	moteset(p, r, g, b)

def motemeter(value):
	print("motemeter({0})".format(value))
	mote.clear()
	if value > 128:
		value = 128
	moteplot(value, 0, 64, 0, 255, 0)
	moteplot(value, 65, 96, 255, 255, 0)
	moteplot(value, 97, 128, 255, 0, 0)
	mote.show()

def main():
	for i in range (0,129):
		motemeter(i)
		time.sleep(2)

if __name__=="__main__":
	main()
