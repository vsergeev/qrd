# QR Decoder
# Supports QR code versions 1-40 containing numeric, alphanumeric, or 8-bit
# byte data. BCH and Reed-Solomon error correction not implemented.
#
# Note: the image processing is rudimentary. It detects the image origin by
# the first black pixel encountered starting from the top-left corner. It
# detects the bit pixel width by doing a horizontal and vertical scan from the
# origin and finding the smallest run of black pixels. It detects the image
# width by finding the last black pixel on a horizontal scan starting from the
# origin, and the QR size by dividing this width by the bit pixel width.
# This is suitable for online generated pixel perfect QR codes, but may need
# some help (pre-processing) for less perfect images.
#
# Vanya Sergeev - <vsergeev@gmail.com>

from PIL import Image
import sys

if (len(sys.argv) < 2 or len(sys.argv) > 4):
	print "Usage: %s <image> [force bit length] [force QR version]" % sys.argv[0]
	sys.exit()

im = Image.open(sys.argv[1]).convert("1")
pix = im.load()
(xImLen, yImLen) = im.size

###############################################################################
### Auto-detect image origin, bit length, Qr version, and convert image pixels
### to bits
###############################################################################

# Find the origin of the image
ORIGIN = None
for j in range(yImLen):
	for i in range(xImLen):
		# Detect the first black pixel
		if (not pix[i,j]):
			ORIGIN = (i,j)
			break
	if (ORIGIN != None):
		break

# If an explicit bit size wasn't specified
if (len(sys.argv) < 3):
	# Find the shortest black run length on the origin row
	BIT_SIZE = None
	i = 0
	for x in range(xImLen):
		if (pix[x, ORIGIN[1]]):
			if (i > 0 and (BIT_SIZE == None or i < BIT_SIZE)):
				BIT_SIZE = i
				i = 0
		else:
			i += 1
	i = 0
	# Find the shortest black run length on the origin column
	for y in range(yImLen):
		if (pix[ORIGIN[0], y]):
			if (i > 0 and (BIT_SIZE == None or i < BIT_SIZE)):
				BIT_SIZE = i
				i = 0
		else:
			i += 1
else:
	BIT_SIZE = int(sys.argv[2])
	
# If an explicit QR version wasn't specified
if (len(sys.argv) < 4):
	# Find length in the X direction of the QR code
	X_LEN = 0
	for x in range(xImLen):
		if (not pix[x, ORIGIN[1]]): X_LEN = x

	# Deduce the QR version of the code
	xBits = (X_LEN-ORIGIN[0])/BIT_SIZE
	# Bump up/down xBits by 1 or 2 to the closest real QR size
	xError = ((xBits-21) % 4)
	if (xError == 3): xBits += 1
	elif (xError == 1): xBits -= 1
	elif (xError == 2):
		print "Error auto-detecting QR size/version!"
		print "Please specify one with third argument."
		sys.exit()

	yBits = xBits
	qrVersion = ((xBits-21)/4)+1
else:
	qrVersion = int(sys.argv[3])
	xBits = 21+4*(qrVersion-1)
	yBits = xBits

print "Found image bit origin: (%d, %d)" % (ORIGIN[0], ORIGIN[1])
if (len(sys.argv) < 3):
	print "Found image bit length: %d" % BIT_SIZE
if (len(sys.argv) < 4):
	print "Auto-detected QR version: %d" % qrVersion

if (qrVersion < 0 or qrVersion > 40):
	print "Error: unknown QR version!"
	sys.exit()

# Collect the bits
qrBits = []
for j in range(yBits):
	qrBits.append([])
	for i in range(xBits):
		qrBits[j].append(1*(not pix[ORIGIN[0]+BIT_SIZE/2+BIT_SIZE*i, ORIGIN[1]+BIT_SIZE/2+BIT_SIZE*j]))

# Print out the bits
print ""
print "Image Bits:"
for j in range(yBits):
	for i in range(xBits):
		if (qrBits[j][i]):
			print "#",
		else:
			print "_",
	print ""

###############################################################################
### Generate the QR lookup table for this QR version
###############################################################################

# Alignment pattern center coordinates for each QR version (1-40), extracted
# from the QR ISO standard.
qrAlignmentPatterns = [[], [6, 18], [6, 22], [6, 26], [6, 30], [6, 34], [6, 22, 38], [6, 24, 42], [6, 26, 46], [6, 28, 50], [6, 30, 54], [6, 32, 58], [6, 34, 62], [6, 26, 46, 66], [6, 26, 48, 70], [6, 26, 50, 74], [6, 30, 54, 78], [6, 30, 56, 82], [6, 30, 58, 86], [6, 34, 62, 90], [6, 28, 50, 72, 94], [6, 26, 50, 74, 98], [6, 30, 54, 78, 102], [6, 28, 54, 80, 106], [6, 32, 58, 84, 110], [6, 30, 58, 86, 114], [6, 34, 62, 90, 118], [6, 26, 50, 74, 98, 122], [6, 30, 54, 78, 102, 126], [6, 26, 52, 78, 104, 130], [6, 30, 56, 82, 108, 134], [6, 34, 60, 86, 112, 138], [6, 30, 58, 86, 114, 142], [6, 34, 62, 90, 118, 146], [6, 30, 54, 78, 102, 126, 150], [6, 24, 50, 76, 102, 128, 154], [6, 28, 54, 80, 106, 132, 158], [6, 32, 58, 84, 110, 136, 162], [6, 26, 54, 82, 110, 138, 166], [6, 30, 58, 86, 114, 142, 170]]

# Compute the alignment pattern coordinates
qrAlignmentCoords = []
coordValues = qrAlignmentPatterns[qrVersion-1]
for x in coordValues:
	for y in coordValues:
		# If the center coordinate is not a position pattern, then add it to our coordinate list
		if (	not (x == min(coordValues) and y == min(coordValues)) and
			not (x == min(coordValues) and y == max(coordValues)) and
			not (x == max(coordValues) and y == min(coordValues))):
			qrAlignmentCoords.append((x,y))

def insideAlignmentPattern(i, j, alignmentCoords):
	for (x,y) in alignmentCoords:
		if abs(x-i) <= 2 and abs(y-j) <= 2:
			return True
	return False

# Generate the look up table
qrLookup = []
totalDataBits = 0
for j in range(yBits):
	qrLookup.append([])
	for i in range(xBits):
		# Top left position pattern
		if (i < 7 and j < 7): 			qrLookup[j].append(('P',0))
		# Top right position pattern
		elif (i >= (xBits-7) and j < 7): 	qrLookup[j].append(('P',0))
		# Bottom left position pattern
		elif (i < 7 and j >= (yBits-7)):	qrLookup[j].append(('P',0))
		# Top left blank wall
		elif (i == 7 and j < 8): 		qrLookup[j].append(('B',0))
		elif (i < 8 and j == 7):		qrLookup[j].append(('B',0))
		# Top right blank wall
		elif (i == xBits-7-1 and j < 8):	qrLookup[j].append(('B',0))
		elif (i >= xBits-7-1 and j == 7):	qrLookup[j].append(('B',0))
		# Bottom left blank wall
		elif (i == 7 and j >= (yBits-7-1)):	qrLookup[j].append(('B',0))
		elif (i < 8 and j == (yBits-7-1)):	qrLookup[j].append(('B',0))
		# Alignment positions
		elif (insideAlignmentPattern(i,j, qrAlignmentCoords)):	qrLookup[j].append(('A',0))
		# Vertical timing pattern
		elif (i == 6):				qrLookup[j].append(('T',0))
		# Horizontal timing pattern
		elif (j == 6):				qrLookup[j].append(('T',0))
		# Top right horizontal format bits
		elif (i >= xBits-7-1 and j == 8):	qrLookup[j].append(('G', ((7-(i-(xBits-7-1))))))
		# Top left vertical format bits
		elif (i == 8 and j < 9):		qrLookup[j].append(('F', (j if j < 6 else j-1)))
		# Top left horizontal format bits
		elif (i < 8 and j == 8):		qrLookup[j].append(('F', (14-i if i < 6 else 15-i)))
		# One dark bit above bottom left format bits
		elif (i == 8 and j == yBits-7-1):	qrLookup[j].append(('D',0))
		# Bottom left vertical format bits
		elif (i == 8 and j > yBits-7-1):	qrLookup[j].append(('G', (j-(yBits-7-1)+7)))
		# Version bits only exist in version 7 and up
		# Top right version bits
		elif (qrVersion >= 7 and i >= xBits-7-1-3 and j < 6):	qrLookup[j].append(('V', (i-(xBits-7-1-3)+3*j)))
		# Bottom left version bits
		elif (qrVersion >= 7 and i < 6 and j >= yBits-7-1-3):	qrLookup[j].append(('R', (j-(yBits-7-1-3)+3*i)))
		else:
			qrLookup[j].append(('.',0))
			totalDataBits += 1

# Add data bits to look up table

# Start in the bottom right corner
y = yBits-1
x = xBits-1
bitCounter = 7
byteCounter = 0
goingUp = True
symbol = '.'

i = 0
while (i < totalDataBits):
	# Skip over the vertical timing pattern
	if (x == 6):
		x -= 1
		continue

	# Only place a data bit if this is a data space
	if (qrLookup[y][x][0] == '.'):
		qrLookup[y][x] = (symbol, bitCounter+byteCounter*8)
		bitCounter -= 1
		if (bitCounter < 0):
			byteCounter += 1
			bitCounter = 7
			# If we're on the last block, we might be enumerating
			# the mod 8 remainder bits
			if ((bitCounter + byteCounter * 8) == totalDataBits):
				bitCounter -= 8 - (totalDataBits % 8)
			symbol = '.' if symbol == '_' else '_'
		i += 1

	# If we're on an odd column, move to the left
	if ( (x > 6 and ((x+1) % 2) != 0) or (x < 6 and (x % 2) != 0) ):
		newX = x-1
		newY = y
	# If we're on an even column, move up/down and right 
	else:
		newX = x+1
		if (goingUp): newY = y-1
		else: newY = y+1

	# If we're out of bounds, move to the left and switch direction
	if (newY < 0 or newY == yBits):
		goingUp = not goingUp
		newY = y
		newX -= 2

	x = newX
	y = newY
	

# Print out the look up table
print ""
print "Lookup Table Generated:"
for j in range(yBits):
	for i in range(xBits):
		if (qrLookup[j][i][0] == '.' or qrLookup[j][i][0] == '_'): print "%03d" % qrLookup[j][i][1],
		else: print "%s  " % qrLookup[j][i][0],
	print ""


###############################################################################
### Extract the raw QR bits using the look up table
###############################################################################

maskedFormat1Bits = [0]*15
maskedFormat2Bits = [0]*15
version1Bits = [0]*18
version2Bits = [0]*18
interleavedDataBits = [0]*(totalDataBits+5)

# Extract the bits from the QR code
for j in range(yBits):
	for i in range(xBits):
		(t, index) = qrLookup[j][i]
		# First format bits
		if (t == 'F'): 			maskedFormat1Bits[index] = qrBits[j][i]
		# Second format bits
		elif (t == 'G'):		maskedFormat2Bits[index] = qrBits[j][i]
		# First version bits
		elif (t == 'V'):		version1Bits[index] = qrBits[j][i]
		# Second version bits
		elif (t == 'R'):		version2Bits[index] = qrBits[j][i]
		# Data bits
		elif (t == '.' or t == '_'):	interleavedDataBits[index] = qrBits[j][i]

###############################################################################
### Unmask and decode the Format Bits, Unmask the Data Bits
###############################################################################

def xor_bits(a, b):
	return [(a[i] ^ b[i]) for i in range(len(a))]

def bits2num(bits):
	num = 0
	for i in range(len(bits)):
		num |= (1 << i)*(bits[i])
	return num

# Unmask Format Bits
qrFormatMask = [1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0]
qrFormatMask.reverse()
format1Bits = xor_bits(qrFormatMask, maskedFormat1Bits)
format2Bits = xor_bits(qrFormatMask, maskedFormat2Bits)

# Decode the ECC level from the format bits
dECCLevel = bits2num(format1Bits[len(format1Bits)-2:len(format1Bits)])
if (dECCLevel == 0): dECCLevelStr = "M"
elif (dECCLevel == 1): dECCLevelStr = "L"
elif (dECCLevel == 2): dECCLevelStr = "H"
elif (dECCLevel == 3): dECCLevelStr = "Q"

# Decode the mask pattern code from the format bits
dMaskPattern = bits2num(format1Bits[len(format1Bits)-5:len(format1Bits)-2])

# Unmask the data bits
for j in range(yBits):
	for i in range(xBits):
		(t, index) = qrLookup[j][i]
		xorBit = 0
		# Mask Patterns documented in the QR ISO standard
		if (dMaskPattern == 0):		xorBit = 1*( ((i+j) % 2) == 0 )
		elif (dMaskPattern == 1):	xorBit = 1*( (j % 2) == 0 )
		elif (dMaskPattern == 2):	xorBit = 1*( (i % 3) == 0 )
		elif (dMaskPattern == 3):	xorBit = 1*( ((i+j) % 3) == 0 )
		elif (dMaskPattern == 4):	xorBit = 1*( (((j/2)+(i/3)) % 2) == 0 )
		elif (dMaskPattern == 5):	xorBit = 1*( ( ((i*j) % 2) + ((i*j) % 3) ) == 0)
		elif (dMaskPattern == 6):	xorBit = 1*( ((((i*j) % 2) + ((i*j) % 3)) % 2) == 0)
		elif (dMaskPattern == 7):	xorBit = 1*( ( (((i*j) % 3) + ((i+j) % 2)) % 2) == 0)
		if (t == '.' or t == '_'):	interleavedDataBits[index] ^= xorBit

# A list of (number of error correction blocks, number of data blocks) tuples
# associated with each ECC level (L,M,Q,H), associated with each version (1-40)
# Extracted from the QR ISO standard
qrWordCounts = [[[(1, 19)], [(1, 16)], [(1, 13)], [(1, 9)]], [[(1, 34)], [(1, 28)], [(1, 22)], [(1, 16)]], [[(1, 55)], [(1, 44)], [(2, 17)], [(2, 13)]], [[(1, 80)], [(2, 32)], [(2, 24)], [(4, 9)]], [[(1, 108)], [(2, 43)], [(2, 15), (2, 16)], [(2, 11), (2, 12)]], [[(2, 68)], [(4, 27)], [(4, 19)], [(4, 15)]], [[(2, 78)], [(4, 31)], [(2, 14), (4, 15)], [(4, 13), (1, 14)]], [[(2, 97)], [(2, 38), (2, 39)], [(4, 18), (2, 19)], [(4, 14), (2, 15)]], [[(2, 116)], [(3, 36), (2, 37)], [(4, 16), (4, 17)], [(4, 12), (4, 13)]], [[(2, 68), (2, 69)], [(4, 43), (1, 44)], [(6, 19), (2, 20)], [(6, 15), (2, 16)]], [[(4, 81)], [(1, 50), (4, 51)], [(4, 22), (4, 23)], [(3, 12), (8, 13)]], [[(2, 92), (2, 93)], [(6, 36), (2, 37)], [(4, 20), (6, 21)], [(7, 14), (4, 15)]], [[(4, 107)], [(8, 37), (1, 38)], [(8, 20), (4, 21)], [(12, 11), (4, 12)]], [[(3, 115), (1, 116)], [(4, 40), (5, 41)], [(11, 16), (5, 17)], [(11, 12), (5, 13)]], [[(5, 87), (1, 88)], [(5, 41), (5, 42)], [(5, 24), (7, 25)], [(11, 12), (7, 13)]], [[(5, 98), (1, 99)], [(7, 45), (3, 46)], [(15, 19), (2, 20)], [(3, 15), (13, 16)]], [[(1, 107), (5, 108)], [(10, 46), (1, 47)], [(1, 22), (15, 23)], [(2, 14), (17, 15)]], [[(5, 120), (1, 121)], [(9, 43), (4, 44)], [(17, 22), (1, 23)], [(2, 14), (19, 15)]], [[(3, 113), (4, 114)], [(3, 44), (11, 45)], [(17, 21), (4, 22)], [(9, 13), (16, 14)]], [[(3, 107), (5, 108)], [(3, 41), (13, 42)], [(15, 24), (5, 25)], [(15, 15), (10, 16)]], [[(4, 116), (4, 117)], [(17, 42)], [(17, 22), (6, 23)], [(19, 16), (6, 17)]], [[(2, 111), (7, 112)], [(17, 46)], [(7, 24), (16, 25)], [(34, 13)]], [[(4, 121), (5, 122)], [(4, 47), (14, 48)], [(11, 24), (14, 25)], [(16, 15), (14, 16)]], [[(6, 117), (4, 118)], [(6, 45), (14, 46)], [(11, 24), (16, 25)], [(30, 16), (2, 17)]], [[(8, 106), (4, 107)], [(8, 47), (13, 48)], [(7, 24), (22, 25)], [(22, 15), (13, 16)]], [[(10, 114), (2, 115)], [(19, 46), (4, 47)], [(28, 22), (6, 23)], [(33, 16), (4, 17)]], [[(8, 122), (4, 123)], [(22, 45), (3, 46)], [(8, 23), (26, 24)], [(12, 15), (28, 16)]], [[(3, 117), (10, 118)], [(3, 45), (23, 46)], [(4, 24), (31, 25)], [(11, 15), (31, 16)]], [[(7, 116), (7, 117)], [(21, 45), (7, 46)], [(1, 23), (37, 24)], [(19, 15), (26, 16)]], [[(5, 115), (10, 116)], [(19, 47), (10, 48)], [(15, 24), (25, 25)], [(23, 15), (25, 16)]], [[(13, 115), (3, 116)], [(2, 46), (29, 47)], [(42, 24), (1, 25)], [(23, 15), (28, 16)]], [[(17, 115)], [(10, 46), (23, 47)], [(10, 24), (35, 25)], [(19, 15), (35, 16)]], [[(17, 115), (1, 116)], [(14, 46), (21, 47)], [(29, 24), (19, 25)], [(11, 15), (46, 16)]], [[(13, 115), (6, 116)], [(14, 46), (23, 47)], [(44, 24), (7, 25)], [(59, 16), (1, 17)]], [[(12, 121), (7, 122)], [(12, 47), (26, 48)], [(39, 24), (14, 25)], [(22, 15), (41, 16)]], [[(6, 121), (14, 122)], [(6, 47), (34, 48)], [(46, 24), (10, 25)], [(2, 15), (64, 16)]], [[(17, 122), (4, 123)], [(29, 46), (14, 47)], [(49, 24), (10, 25)], [(24, 15), (46, 16)]], [[(4, 122), (18, 123)], [(13, 46), (32, 47)], [(48, 24), (14, 25)], [(42, 15), (32, 16)]], [[(20, 117), (4, 118)], [(40, 47), (7, 48)], [(43, 24), (22, 25)], [(10, 15), (67, 16)]], [[(19, 118), (6, 119)], [(18, 47), (31, 48)], [(34, 24), (34, 25)], [(20, 15), (61, 16)]]]

if (dECCLevel == 1): eccIndex = 0
elif (dECCLevel == 0): eccIndex = 1
elif (dECCLevel == 3): eccIndex = 2
elif (dECCLevel == 2): eccIndex = 3

# De-interleave the data bits
wordCounts = qrWordCounts[qrVersion-1][eccIndex]
totalDataWords = 0

# Assemble all of the data block indices
blocks = []
index = 0
for (b,n) in wordCounts:
	for i in range(b):
		block = []
		for j in range(n):
			block.append(index)
			index += 1
		blocks.append(block)
	totalDataWords += n*b

# Assemble the data word sequence
dataWordSequence = []
index = 0
while len(dataWordSequence) < totalDataWords:
	for j in range(len(blocks)):
		if (index < len(blocks[j])):
			dataWordSequence.append(blocks[j][index])
	index += 1	

# De-interleave the data bits, and put them in MSB first into data bits
dataBits = [0]*(8*totalDataWords)
i = 0
for index in dataWordSequence:
	index = index*8
	bits = interleavedDataBits[i:i+8]
	bits.reverse()
	dataBits[index:index+8] = bits
	i += 8

print ""
print "Decoding:"
print "[*] QR Version: \t", qrVersion	
print "[*] Format Bits #1: \t", format1Bits
print "[*] Format Bits #2: \t", format2Bits
if (qrVersion >= 7):
	print "[*] Version Bits #1: \t", version1Bits			
	print "[*] Version Bits #2: \t", version2Bits
print "[*] ECC Level: \t\t%s (%d)" % (dECCLevelStr, dECCLevel)
print "[*] Mask Pattern: \t%d" % (dMaskPattern)
print ""
print "[*] Unmasked, De-interleaved Data Bits: ", dataBits

###############################################################################
### Decode the data bitstream
###############################################################################

def bits2num_msb(bits):
	num = 0
	for i in range(len(bits)):
		num |= (1 << len(bits)-1-i)*(bits[i])
	return num

# QR Alphanumeric table extracted from the QR ISO Standard
qrAlphanumTable = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', ' ', '$', '%', '*', '+', '-', '.', '/', ':']

i = 0
while i < (totalDataBits-(totalDataBits % 8)):
	# Extract the mode from the header
	dMode = bits2num_msb(dataBits[i:i+4])
	if (dMode == 0x1):	dModeStr = "Numeric"
	elif (dMode == 0x2):	dModeStr = "Alphanumeric"
	elif (dMode == 0x4):	dModeStr = "8-bit Byte"
	elif (dMode == 0x8):	dModeStr = "Kanji"
	elif (dMode == 0x3):	dModeStr = "Structured Append"
	elif (dMode == 0x5):	dModeStr = "FNC1 (First position)"
	elif (dMode == 0x9):	dModeStr = "FNC1 (Second position)"
	elif (dMode == 0x7):	dModeStr = "ECI"
	elif (dMode == 0x0):	dModeStr = "Terminator"
	else:			dModeStr = "Unknown"
	i += 4

	print ""
	print "[*] Found Mode: %s (%d)" % (dModeStr, dMode)

	# Figure out the character count length
	numCharBits = 0
	if (dMode == 0x1):
		if (qrVersion < 10): numCharBits = 10
		elif (qrVersion < 27): numCharBits = 12
		else: numCharBits = 14
	elif (dMode == 0x2):
		if (qrVersion < 10): numCharBits = 9
		elif (qrVersion < 27): numCharBits = 11
		else: numCharBits = 13
	elif (dMode == 0x4):
		if (qrVersion < 10): numCharBits = 8
		elif (qrVersion < 27): numCharBits = 16
		else: numCharBits = 16
	elif (dMode == 0x8):
		if (qrVersion < 10): numCharBits = 8
		elif (qrVersion < 27): numCharBits = 10
		else: numCharBits = 12

	# Extract the length from the header
	dLength = 0
	if (numCharBits > 0):
		dLength = bits2num_msb(dataBits[i:i+numCharBits])
		i += numCharBits
		print "[*] Found Length: %d" % dLength

	# Process the different types of modes:

	# Detect terminator
	if (dMode == 0x0):
		break

	# Decode Numeric data
	if (dMode == 0x1):
		dNumericalStr = ""
		while (dLength > 0):
			if (dLength >= 3):
				number = bits2num_msb(dataBits[i:i+10])
				i += 10
				dLength -= 3
				dNumericalStr += "%03d" % number
			else:
				number = bits2num_msb(dataBits[i:i+7])
				i += 7
				dLength -= 2
				dNumericalStr += "%02d" % number
		print "[*] Decoded Data: %s" % dNumericalStr

	# Decode Alphanumeric data
	elif (dMode == 0x2):
		dAlphanumValues = []
		while (dLength > 0):
			if (dLength > 1):
				decimal = bits2num_msb(dataBits[i:i+11])
				i += 11
				dLength -= 2
				dAlphanumValues.append( (decimal-(decimal % 45)) / 45)
				dAlphanumValues.append(decimal % 45)
			else:
				decimal = bits2num_msb(dataBits[i:i+6])
				i += 6
				dLength -= 1
				dAlphanumValues.append(decimal)

		dAlphanumStr = ""
		for index in dAlphanumValues:
			if (index >= len(qrAlphanumTable)):
				break
			dAlphanumStr += qrAlphanumTable[index]
		print "[*] Decoded Data: %s" % dAlphanumStr

	# Decode 8-bit Byte data
	elif (dMode == 0x4):
		dByteValues = []
		while (dLength > 0):
			dByteValues.append(bits2num_msb(dataBits[i:i+8]))
			i += 8
			dLength -= 1

		print "[*] Decoded Data as bytes:",
		for x in dByteValues:
			print "%02X" % x,
		print ""

		dByteStr = ""
		for x in dByteValues:
			dByteStr += "%c" % x
		print "[*] Decoded Data as string: %s" % dByteStr

	else:
		print "[*] Unsupported mode"
		break

