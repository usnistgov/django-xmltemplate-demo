import unittest as test
import os, pdb
from mongoengine import connect

from xmltemplate import models
from xmltemplate import schema

datadir = os.path.join(os.path.dirname(__file__), "data")

def setUpMongo():
    return connect(host=os.environ['MONGO_TESTDB_URL'])

def tearDownMongo(mc):
    try:
        db = mc.get_default_database()
        mc.drop_database(db.name)
    except Exception, ex:
        pass

    
@test.skipIf(not os.environ.get('MONGO_TESTDB_URL'),
             "test mongodb not available")
class TestMultiSchemas(test.TestCase):

    def setUp(self):
        self.mc = setUpMongo()

    def tearDown(self):
        tearDownMongo(self.mc)
        self.mc.close()
        self.mc = None

    def load_multi(self):
        pass

    def test_find_includers(self):
        schemafile = "experiments.xsd"
        schemapath = os.path.join(datadir, schemafile)
        schema.SchemaLoader.load_from_file(schemapath, schemafile, schemafile)

        schemafile = "microscopy-incl.xsd"
        schemapath = os.path.join(datadir, schemafile)
        # pdb.set_trace()
        schema.SchemaLoader.load_from_file(schemapath, schemafile)

        exp = models.Schema.get_by_name("experiments.xsd")
        self.assertEquals(exp.find_including_schema_names(),
                          ['microscopy-incl.xsd'])

    def test_recognize_location(self):
        schemafile = "experiments.xsd"
        schemapath = os.path.join(datadir, schemafile)
        schema.SchemaLoader.load_from_file(schemapath, schemafile)

        schemafile = "microscopy-incl.xsd"
        schemapath = os.path.join(datadir, schemafile)
        # pdb.set_trace()

        # location doesn't match
        with self.assertRaises(schema.FixableErrorsRemain):
            schema.SchemaLoader.load_from_file(schemapath, schemafile)

        loader = schema.SchemaLoader.from_file(schemapath, schemafile)
        loader.recognize_location("experiments.xsd", "experiments.xsd")
        loader.load()

        exp = models.Schema.get_by_name("experiments.xsd")
        self.assertEquals(exp.find_including_schema_names(),
                          ['microscopy-incl.xsd'])

    def test_find_importers(self):
        schemafile = "experiments.xsd"
        schemapath = os.path.join(datadir, schemafile)
        schema.SchemaLoader.load_from_file(schemapath, schemafile, schemafile)

        schemafile = "microscopy.xsd"
        schemapath = os.path.join(datadir, schemafile)
        # pdb.set_trace()
        schema.SchemaLoader.load_from_file(schemapath, schemafile)

        exp = models.Schema.get_by_name("experiments.xsd")
        self.assertEquals(exp.find_importing_schema_names(),
                          ['microscopy.xsd'])

    def test_recognize_ns(self):
        schemafile = "experiments.xsd"
        schemapath = os.path.join(datadir, schemafile)
        schema.SchemaLoader.load_from_file(schemapath, schemafile)

        # load again with a different name
        schemafile = "experiments.xsd"
        schemapath = os.path.join(datadir, schemafile)
        schema.SchemaLoader.load_from_file(schemapath, "experiments")

        schemafile = "microscopy.xsd"
        schemapath = os.path.join(datadir, schemafile)

        # location doesn't match
        with self.assertRaises(schema.FixableErrorsRemain):
            schema.SchemaLoader.load_from_file(schemapath, schemafile)

        loader = schema.SchemaLoader.from_file(schemapath, schemafile)
        loader.recognize_namespace("urn:experiments", "experiments.xsd")
        loader.load()

        exp = models.Schema.get_by_name("experiments.xsd")
        self.assertEquals(exp.find_importing_schema_names(),
                          ['microscopy.xsd'])

    def test_big_import(self):
        resmddir = os.path.join(datadir, "resmd")

        # res-md.xsd will cause http://www.w3.org/2009/01/xml.xsd to be
        # automatically loaded from the internet
        schemafile = "res-md.xsd"
        schemapath = os.path.join(resmddir, schemafile)
        # pdb.set_trace()
        schema.SchemaLoader.load_from_file(schemapath, schemafile, schemafile)

        schemafile = "res-app.xsd"
        schemapath = os.path.join(resmddir, schemafile)
        schema.SchemaLoader.load_from_file(schemapath, schemafile, schemafile)

        resmd = models.Schema.get_by_name("res-md.xsd")
        self.assertEquals(resmd.find_importing_schema_names(),
                          ['res-app.xsd'])

        xmlxsd = models.Schema.get_by_name("http://www.w3.org/2009/01/xml.xsd")
        importers = xmlxsd.find_importing_schema_names()
        self.assertIn('res-app.xsd', importers)
        self.assertIn('res-md.xsd', importers)

TESTS = ["TestMultiSchemas"]

def test_suite():
    suite = test.TestSuite()
    suite.addTests([test.makeSuite(TestMultiSchemas)])
    return suite

if __name__ == '__main__':
    test.main()
