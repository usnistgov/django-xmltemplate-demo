import unittest as test
import os, pdb
from mongoengine import connect

from xmltemplate import validate as val

datadir = os.path.join(os.path.dirname(__file__), "data")
XSDNS = val.XSD_NS
XSDPRE = "{"+XSDNS+"}"

def setUpMongo():
    return connect(host=os.environ['MONGO_TESTDB_URL'])

def tearDownMongo(mc):
    try:
        db = mc.get_default_database()
        mc.drop_database(db.name)
    except Exception, ex:
        pass

def getContent(datafile, dir=datadir):
    filepath = os.path.join(dir, datafile)
    with open(filepath) as fd:
        return fd.read()

class TestValidatorNoDB(test.TestCase):

    def setUp(self):
        self.mc = setUpMongo()

    def tearDown(self):
        tearDownMongo(self.mc)
        self.mc.close()
        self.mc = None

    
    def test_parse(self):
        schemafile = "experiments.xsd"
        content = getContent(schemafile)

        tree = val.Validator.parse(content)
        self.assertEquals(tree.getroot().tag, XSDPRE+"schema")
        
    def test_bad_parse(self):
        schemafile = "badform.xsd"
        content = getContent(schemafile)

        with self.assertRaises(val.ValidationError):
            tree = val.Validator.parse(content)

    def test_simple_validate(self):
        schemafile = "experiments.xsd"
        content = getContent(schemafile)

        v8r = val.lxmlValidator(content)
        
        
        





TESTS = "TestValidator".split()

def test_suite():
    suite = test.TestSuite()
    suite.addTests([test.makeSuite(TestValidator)])
    return suite

if __name__ == '__main__':
    test.main()

