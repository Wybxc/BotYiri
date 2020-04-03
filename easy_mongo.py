import pymongo


class mongoCollectionWrapper():
    def __init__(self, collection):
        self._collection = collection
        self._dict = {}
        for pair in self._collection.find({'name': {'$exists': True}, 'value': {'$exists': True}}):
            self._dict[pair['name']] = pair['value']
    
    def __getitem__(self, index):        
        return self._dict[index]

    def __setitem__(self, index, value):
        if not self._collection.find_one_and_replace({'name': index}, {'name': index, 'value': value}):
            self._collection.insert_one({'name': index, 'value': value})
            self._dict[index] = value
    
    def remove(self, index):
        self._collection.find_one_and_delete({'name': index})
        return self._dict.pop(index, None)        

    def remove_by_value(self, value):
        node = self._collection.find_one_and_delete({'value': value})
        names = []
        while node:
            self._dict.pop(node['name'], None)
            names.append(node['name'])
            node = self._collection.find_one_and_delete({'value': value})
        return names

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def items(self):
        return self._dict.items()

    def __repr__(self):
        return repr(self._dict)
    
    def __str__(self):
        return str(self._dict)


class easyMongo():
    def __init__(self, name):
        self._mongoClient = pymongo.MongoClient('mongodb://localhost:27017/')
        self._messageDB = self._mongoClient[name]
        self._wrappers = {}

    def __getitem__(self, index):
        if not self._wrappers.get(index):
            self._wrappers[index] = mongoCollectionWrapper(self._messageDB[index])
        return self._wrappers[index]
