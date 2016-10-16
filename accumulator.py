class Accumulator():
	def __init__(self, lowlimit, highlimit):
		self.last_value = 0
		self.value = 0.0
		self.max_value = lowlimit 
		self.min_value = highlimit
		self.n = 0
		self.lowlimit = lowlimit
		self.highlimit = highlimit
		
	def addValue(self, value):
		self.last_value = value
		if (value >= self.lowlimit) and (value <= self.highlimit):
			self.value += value
			self.n += 1
			if (self.max_value < value):
				self.max_value = value
			if (self.min_value > value):
				self.min_value = value
		
	def mean(self):
		if self.n > 0:
			return self.value / self.n
		else:
			return 0
