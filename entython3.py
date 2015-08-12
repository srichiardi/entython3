from weakref import WeakValueDictionary
from datetime import datetime
import csv
import sys


class Entity:
    __mainEntityTypes = []
    __attributeTypes = []
    __passportHeaders = ["ENTYTHON_GROUP", "ENTITY_TYPE", "ENTITY_ID"]
    __instances = {}
    
    
    def __init__(self, entType, entName, attrTypes=[]):
        self.type = entType
        self.name = entName
        self.group = None
        self.attributes = {}
        for item in attrTypes:
            self.attributes[item] = []
        # adding entity to the collection
        try:
            Entity.__instances[self.type][self.name] = self
        except KeyError:
            Entity.__instances[self.type] = { self.name : self}
        

    def joinGroup(self, alienEntity=None):
        ''' 2 different groups competing '''
        # if another entity is being declared as argument of the function
        if alienEntity:
            # if both groups are set and are not the same negotiate which group to choose
            if self.group and alienEntity.group and (self.group.name != alienEntity.group.name):
                # local group wins
                if self.group.size >= alienEntity.group.size:
                    self.group.annexGroup(alienEntity.group)
                # alien group wins
                else:
                    alienEntity.group.annexGroup(self.group)
            # if only the imported entity has a group set alien group wins
            elif not self.group and alienEntity.group:
                self.group = alienEntity.group
                self.group.addMember(self)
        # assigning his own new group if both local and alien groups are none
        elif not self.group:
            self.group = Group()
            self.group.addMember(self)
        # if the group was already set then do nothing

    
    def getPrintableDicts(self):
        ''' arrange dicts: ENTYTHON_GRUOP | MET | ME_ID | ATTR_1 | ATTR_2 | ... '''
        if self.group:
            groupName = self.group.name
        else:
            groupName = ""
        
        dictList = []
        nextAttr = True
        
        while nextAttr == True:
            tempDict = {}
            nextAttr = False
            tempDict = { Entity.__passportHeaders[0] : groupName,
                        Entity.__passportHeaders[1] : self.type,
                        Entity.__passportHeaders[2] : self.name }
            
            for key in self.attributes.keys():
                try:
                    value = self.attributes[key].pop()
                    nextAttr = True
                except IndexError:
                    value = ''
                finally:
                    tempDict[key] = value
                    
            if nextAttr:
                dictList.append(tempDict)
        
        return dictList
    

    def linkTo(self, attribute):
        ''' linking main entity to attribute entity '''
        if attribute.name not in self.attributes[attribute.type]:
            self.attributes[attribute.type].append(attribute.name)
            # and adding self entity to attribute entity
            attribute.attributes[self.type].append(self.name)
            
            # negotiate group with attribute
            attribute.joinGroup(self)
            
    
    def nextNodes(self):
        ''' returns a list of attribute entities directly linked to the current one '''
        nodesList = []
        for attrType in self.attributes.keys():
            for attrID in self.attributes[attrType]:
                nextNode = Entity.__instances[attrType][attrID]
                nodesList.append(nextNode)

        return nodesList
    
    
    @classmethod
    def getEntity(cls, meType, name, attrTypes):
        ''' method to check if an entity exists before creating one '''
        try:
            instance = cls.__instances[meType][name]
        except KeyError:
            instance = cls(meType, name, attrTypes)
        # make sure to add new attributes if not previously included
        else:
            for aType in attrTypes:
                if aType not in instance.attributes.keys():
                    instance.attributes[aType] = []
            
        return instance
    
    
    @classmethod
    def importFromFile(cls, csvFileName):
        ''' take a CSV file as input, reads it and create main and attribute entities,
        groups and links in between '''
        fileToRead = open(csvFileName, "r")
        csvReader = csv.reader(fileToRead, delimiter=',', dialect='excel',
                               quotechar='"')
        # fetch headers
        headers = next(csvReader)
        
        # quit the process if file contains less than 2 columns
        if len(headers) < 2:
            sys.exit('Import error: not enough columns in the imported file!')
        
        # map headers to columns with dictionary comprehension
        headerDict = { value : idx for idx, value in enumerate(headers) }
        
        met = headers[0] # Main Entity Type, "met" for short, is always the first column
        
        cls.__mainEntityTypes.append(met)
        
        # remove main entity from dictionary for iteration through attributes only 
        headerDict.pop(met)
        
        # remove group type from dictionary: ignoring old groups to avoid them be considered attributes
        if cls.__passportHeaders[0] in headerDict.keys():
            headerDict.pop(cls.__passportHeaders[0])

        aTypes = headerDict.keys()
        
        # update the class var listing all attribute types, including new from later imports
        for attrType in aTypes:
            if attrType not in cls.__attributeTypes:
                cls.__attributeTypes.append(attrType)
                
        # Main Entity Count
        mec = 0

        # main import loop begins
        for line in csvReader:
            # skip line if main entity is empty
            if line[0] == "":
                continue
            
            mainEnt = cls.getEntity(met, line[0], aTypes)
            mec += 1
            # assign new group (or confirm current)
            # only main entities create groups, attributes receive them and transfer them
            mainEnt.joinGroup()
            
            for attrType in aTypes:
                idx = headerDict[attrType]
                # skip if attribute is empty
                if line[idx] == "":
                    continue
                
                attribute = cls.getEntity(attrType, line[idx], [met])
                # add attributes to the entity, and join same group
                mainEnt.linkTo(attribute) 
                    
        fileToRead.close()
        
        gn = len(Group._Group__groupInstances)
        
        print('Import completed. Imported {} entities type "{}", in {} group(s).'.format(mec, met, gn))
        
        
    @classmethod
    def printStats(cls):
        ''' providing information on all groups:
        nr of main entities, tot nr of groups, nr of groups with more than 50 main entities,
        nr of groups with less than 2 main entities (unlinked potentially linkable),
        attribute entities linked to many main entities (most popular)... '''
        pass
    
    
    @classmethod
    def exportToFile(cls, folderPath):
        ''' print main entities, relative attributes and groups they belong in CSV format. '''
        fileName = folderPath + "/entython_export_%s.csv" % datetime.now().strftime("%Y%m%d_%H-%M-%S")
        csvFileToWrite = open(fileName, 'a')
        
        fieldNames = cls.__passportHeaders
        fieldNames.extend(cls.__attributeTypes)
        
        csvWriter = csv.DictWriter(csvFileToWrite, fieldNames, restval='', delimiter=',',
                                   extrasaction='ignore', dialect='excel', quotechar='"')
        csvWriter.writeheader()
        # iterate through main entities
        for mainEntityType in cls.__mainEntityTypes:
            for entity in cls.__instances[mainEntityType].values():
                entityRecords = entity.getPrintableDicts()
                csvWriter.writerows(entityRecords)
            
        csvFileToWrite.close()
        


class Group:
    __groupCount = 0 # for naming purpose only
    __groupInstances = WeakValueDictionary()
    
    
    def __init__(self):
        Group.__groupCount += 1
        self.members = []
        self.name = "G-%d" % Group.__groupCount
        self.size = 0
        Group.__groupInstances[self.name] = self


    def addMember(self, newMember):
        ''' add new group member entities to the group list '''
        if newMember not in self.members:
            self.members.append(newMember)
            self.size += 1


    def annexGroup(self, otherGroup):
        ''' transfer members from one group to another and update members' group membership '''
        for member in otherGroup.members:
            self.addMember(member)
            member.group = self
        # remove empty group
        del otherGroup
        
    
    def getMembersByType(self, membType):
        ''' return a list of all members belonging to the same entity type '''
        memberList = []
        for member in self.members:
            if member.type == membType:
                memberList.append(member)
        return memberList
    
    
    @classmethod
    def getGroupByName(cls, groupName):
        ''' at import stage allows to relink an existing group or create a new one '''
        # existing group
        try:
            group = cls.__groupInstances[groupName]
        # new group with old imported name
        except KeyError:
            group = cls()
        return group

