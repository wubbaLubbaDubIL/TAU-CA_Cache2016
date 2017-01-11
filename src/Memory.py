import config
import math

class AbstractMemory(object):
    def __init__(self, size, nextLevelMem):
        self.size = size
        self.nextLevel = nextLevelMem

    def initializeMemoryToZero(self):
        NotImplementedError

    def readData(self, addressInHex):
        NotImplementedError

    def writeData(self, data, addressInHex):
        NotImplementedError

    def saveMemoryToFile(self, dstPath):
        NotImplementedError

class MainMemory(AbstractMemory):
    '''
    this class will represent the main memmory
    '''

    memory = []
    
    def __init__(self, size, nextLevelMem=None):
        """
        initializing the memmory to zeros
        """
        super(MainMemory, self).__init__(size, nextLevelMem)
        self.memory = []
        self.size = size
        self.outputLogFileName = config.getMainMemoryStatusOutputFilePath()
        self.initializeMemoryToZero()
        self.nextLevel = nextLevelMem

    def initializeMemoryToZero(self):
        self.memory = ['00' for i in range(self.size)]

    def getMemoryDataFromFile(self, meminFilePath):
        """
        fetching the initial main memory status from the memin file
        :param meminFilePath: the path to the memin.txt file
        :return: none
        """
        with open(meminFilePath, 'r') as memfile:
            i = 0
            for line in memfile.readlines():
                hexData = line.strip()
                if len(hexData) == 2:  # each line should be 1 Byte
                    try:
                        int(hexData, 16)  # if doesn't contain chars [0-9, a-f]
                        self.memory[i] = hexData
                    except:
                        if ValueError:
                            raise ValueError("memin file contains a bad line: " + hexData)
                        elif IndexError:
                            raise IndexError("memin file has data bigger than 16MB.")
                    i += 1
                else:
                    raise ValueError("memin file contains a bad line: " + hexData)

    def readData(self, addressInHex):
        addressInInt = int(addressInHex, 16)
        # TODO: need to add later time that took to get the memory to stats
        return self.memory[addressInInt]

    def writeData(self, data, addressInHex):
        addressInInt = int(addressInHex, 16)
        # TODO: need to add later time that took to write into the memory to stats
        self.memory[addressInInt] = data
        return

    def saveMemoryToFile(self, dstPath):
        with open(dstPath, 'w') as memoutFile:
            for i in range(self.size):
                memoutFile.write(self.memory[i] + "\n")
            memoutFile.close()

class Cache(AbstractMemory):
    def __init__(self, size, blockSize, cacheAssociativity, nextLevelMem):
        super(Cache, self).__init__(size, nextLevelMem)
        self.data = {}
        self.size = size
        self.blockSize = blockSize
        self.associativity = cacheAssociativity
        self.nextLevel = nextLevelMem
        self.numberOfBlocks = size / blockSize
        self.numberOfSets = self.size / self.associativity
        self.offsetSize = int(math.log(self.blockSize, 2))
        self.indexSize = int(math.log(self.numberOfSets, 2))
        self.tagSize = config.addressSize - self.indexSize - self.offsetSize
        self.readHits = 0
        self.readMisses = 0
        self.writeHits = 0
        self.writeMisses = 0
        self.initializeMemoryToZero()

    def initializeMemoryToZero(self):
        NotImplementedError

    def readData(self, addressInHex):
        NotImplementedError

    def writeData(self, data, addressInHex):
        NotImplementedError

    def saveMemoryToFile(self, dstPath):
        NotImplementedError

    def parseHexAddress(self, addressInHex):
        addressInBinary = bin(int(addressInHex, 16))[2:].zfill(config.addressSize)
        offset = addressInBinary[-self.offsetSize:]
        index = addressInBinary[-(self.offsetSize + self.indexSize):-self.offsetSize]
        if index == '':
            index = '0'
        tag = addressInBinary[:-(self.offsetSize + self.indexSize)]
        return offset, index, tag

    def saveMemoryToFile(self, dstPath):
        NotImplementedError

# TODO: not sure we need that. maybe better to work with lines?
class MemoryBlock(object):
    # https://github.com/lucianohgo/CacheSimulator/blob/master/src/block.py

    def __init__(self, blockSize, address):
        self.size = blockSize
        self.address = address
        self.valid = False
