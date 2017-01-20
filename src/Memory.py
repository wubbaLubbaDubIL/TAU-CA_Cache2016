import config
import math
import copy
import sys

class AbstractMemory(object):
    def __init__(self, size, nextLevelMem):
        self.size = size
        self.nextLevel = nextLevelMem

    def initializeMemoryToZero(self):
        NotImplementedError

    def readData(self, addressInHex, blockSize):
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
    
    def __init__(self, size, nextLevelMem, busSizeToPrevLevel, accessTime):
        """
        initializing the memmory to zeros
        """
        super(MainMemory, self).__init__(size, nextLevelMem)
        self.memory = []
        self.size = size
        self.outputLogFileName = config.getMainMemoryStatusOutputFilePath()
        self.initializeMemoryToZero()
        self.nextLevel = nextLevelMem
        self.busSizeToPrevLevel = busSizeToPrevLevel
        self.accessTime = accessTime
        self.reads = 0
        self.writes = 0

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
    
    def getTotalActualAccessTime(self, BlockSize):
        busSize = self.busSizeToPrevLevel
        blockToBusSizeFactor = int(math.ceil(1.0*BlockSize/busSize))
        singleAccessTime = self.accessTime + blockToBusSizeFactor-1
        totalAccessTime = (self.reads + self.writes) * singleAccessTime
        return totalAccessTime
    
    def getBlockLocations(self, addressInInt, blockSize):
        addressBlockStartPos = addressInInt - (addressInInt%blockSize)
        addressBlockEndPos = addressBlockStartPos + blockSize
        return addressBlockStartPos, addressBlockEndPos
    
    def readData(self, addressInHex, blockSize):
        """
        returns the relevant block of data
        :param addressInHex: the desired address as string
        :param blockSize: the block size of the cache that asks to load the desired data
        :return: the desired block of data
        """
        self.reads += 1
        addressInInt = int(addressInHex, 16)
        addressBlockStartPos, addressBlockEndPos = self.getBlockLocations(addressInInt, blockSize)
        return self.memory[addressBlockStartPos:addressBlockEndPos]

    def writeData(self, data, addressInHex):
        """
        returns the relevant block of data, assuming len(data)==blockSize
        :param data: the desired data as array of strings
        :param addressInHex: the relevant address as string
        :return: None
        """
        self.writes += 1
        addressInInt = int(addressInHex, 16)
        blockSize = len(data)
        addressBlockStartPos, addressBlockEndPos = self.getBlockLocations(addressInInt, blockSize)
        self.memory[addressBlockStartPos:addressBlockEndPos] = data
        return

    def saveMemoryToFile(self, dstPath):
        with open(dstPath, 'w') as memoutFile:
            for i in range(self.size):
                memoutFile.write(self.memory[i] + "\n")
            memoutFile.close()

class Cache(AbstractMemory):
    def __init__(self, size, blockSize, cacheAssociativity, nextLevelMem, hitTimeCycles, busSizeToPrevLevel, accessTime):
        super(Cache, self).__init__(size, nextLevelMem)
        self.data = []
        self.size = size
        self.blockSize = blockSize
        self.associativity = cacheAssociativity
        self.nextLevel = nextLevelMem
        self.numberOfBlocks = self.size / self.blockSize
        self.numberOfSets = self.numberOfBlocks / self.associativity
        self.offsetSize = int(math.log(self.blockSize, 2))
        self.indexSize = int(math.log(self.numberOfSets, 2))
        self.tagSize = 8*config.addressSize - self.indexSize - self.offsetSize
        self.readHits = 0
        self.readMisses = 0
        self.writeHits = 0
        self.writeMisses = 0
        self.hitTimeCycles = hitTimeCycles
        self.busSizeToPrevLevel = busSizeToPrevLevel
        self.accessTime = accessTime
        self.initializeMemoryToZero()

    def initializeMemoryToZero(self):
        wayDict = {'dirty': False,
                   'valid': False,
                   'tag': '-1',
                   'data': ['00' for i in range(self.blockSize)]}
        indexDict = {'way'+str(num): copy.deepcopy(wayDict) for num in range(self.associativity)}
        indexDict['LRU'] = 'way0'
        self.data = [copy.deepcopy(indexDict) for i in range(self.numberOfSets)]
    
    def getTotalActualAccessTime(self, BlockSize):
        busSize = self.busSizeToPrevLevel
        blockToBusSizeFactor = int(math.ceil(1.0*BlockSize/busSize))
        singleAccessTime = self.accessTime * blockToBusSizeFactor
        totalAccessTime = (self.readHits + self.writeHits
                           + self.readMisses + self.writeMisses) * singleAccessTime
        return totalAccessTime
    
    def getBlockLocations(self, addressInInt, blockSize):
        addressBlockStartPos = addressInInt - (addressInInt%blockSize)
        addressBlockEndPos = addressBlockStartPos + blockSize
        return addressBlockStartPos, addressBlockEndPos
    
    def otherWay(self, way):
        if way == 'way0':
            return 'way1'
        return 'way0'

    def lookForAddressInCache(self, indexInInt, tagInBinary):
        hit = False
        _set = self.data[indexInInt]
        for way in [key for key in _set.keys() if 'way' in key]:
            if _set[way]['tag'] == tagInBinary and _set[way]['valid']:
                hit = True
                return hit, way
        return hit, _set['LRU']
    
    def calcAddressOfBlockInHex(self, indexInInt, tagInBinary):
        addressInBinary = (tagInBinary + bin(indexInInt)[2:].zfill(self.indexSize)).ljust(8*config.addressSize, '0')
        addressInHex = hex(int(addressInBinary, 2))[2:]
        return addressInHex
              
    def writeData(self, data, addressInHex):
        offsetInInt, indexInInt, tagInBinary = self.parseHexAddress(addressInHex)
        hit, way = self.lookForAddressInCache(indexInInt, tagInBinary) # way will be the found way or what's in LRU if not found
        if hit:
            self.writeHits += 1
        else:
            self.writeMisses += 1
            blockIsDirty = self.data[indexInInt][way]['dirty']
            if blockIsDirty:
                blockAddressInHex = self.calcAddressOfBlockInHex(indexInInt, self.data[indexInInt][way]['tag'])
                self.nextLevel.writeData(self.data[indexInInt][way]['data'], blockAddressInHex)
            self.data[indexInInt][way]['data'] = self.nextLevel.readData(addressInHex, self.blockSize)
        offsetBlockStartPos, offsetBlockEndPos = self.getBlockLocations(offsetInInt, len(data))
        self.data[indexInInt][way]['data'][offsetBlockStartPos:offsetBlockEndPos] = data
        self.data[indexInInt][way]['dirty'] = True
        self.data[indexInInt][way]['valid'] = True
        self.data[indexInInt][way]['tag'] = tagInBinary
        if self.associativity == 2:
            self.data[indexInInt]['LRU'] = self.otherWay(way)

    def readData(self, addressInHex, blockSize):
        offsetInInt, indexInInt, tagInBinary = self.parseHexAddress(addressInHex)
        hit, way = self.lookForAddressInCache(indexInInt, tagInBinary) # way will be the found way or what's in LRU if not found
        if hit:
            self.readHits += 1
        else:
            self.readMisses += 1
            if self.data[indexInInt][way]['dirty']:
                blockAddressInHex = self.calcAddressOfBlockInHex(indexInInt, self.data[indexInInt][way]['tag'])
                self.nextLevel.writeData(self.data[indexInInt][way]['data'], blockAddressInHex)
            self.data[indexInInt][way]['data'] = self.nextLevel.readData(addressInHex, self.blockSize)
            self.data[indexInInt][way]['valid'] = True
            self.data[indexInInt][way]['tag'] = tagInBinary
            self.data[indexInInt][way]['dirty'] = False
        offsetBlockStartPos, offsetBlockEndPos = self.getBlockLocations(offsetInInt, blockSize)
        return self.data[indexInInt][way]['data'][offsetBlockStartPos:offsetBlockEndPos]
    
    def saveMemoryToFile(self, dstPath):
        if 'way1' in dstPath:
            way = 'way1'
        else:
            way = 'way0'
        with open(dstPath, 'w') as memoutFile:
            for line in self.data:
                memoutFile.write('\n'.join(line[way]['data']) + "\n")
            memoutFile.close()

    def parseHexAddress(self, addressInHex):
        addressInBinary = bin(int(addressInHex, 16))[2:].zfill(8*config.addressSize)
        offset = addressInBinary[-self.offsetSize:]
        index = addressInBinary[-(self.offsetSize + self.indexSize):-self.offsetSize]
        if index == '':
            index = '0'
        tag = addressInBinary[:-(self.offsetSize + self.indexSize)]
        return int(offset, 2), int(index, 2), tag

# TODO: not sure we need that. maybe better to work with lines?
class MemoryBlock(object):
    # https://github.com/lucianohgo/CacheSimulator/blob/master/src/block.py

    def __init__(self, blockSize, address):
        self.size = blockSize
        self.address = address
        self.valid = False
