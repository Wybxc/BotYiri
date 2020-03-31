import pymongo


class mongoCollectionWrapper():
    def __init__(self, collection):
        self._collection = collection
    
    def __getitem__(self, index):
        node = self._collection.find_one({'name': index})
        if node:
            return node['value']
        return None

    def __setitem__(self, index, value):
        if not self._collection.find_one_and_replace({'name': index}, {'name': index, 'value': value}):
            self._collection.insert_one({'name': index, 'value': value})


class easyMongo():
    def __init__(self, name):
        self._mongoClient = pymongo.MongoClient('mongodb://localhost:27017/')
        self._messageDB = self._mongoClient[name]

    def __getitem__(self, index):
        return mongoCollectionWrapper(self._messageDB[index])
