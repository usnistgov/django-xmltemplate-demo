# import mgi.settings as settings
# from django import test
import unittest as test
import os, pdb
from mongoengine import connect

from xmltemplate import models
from xmltemplate import schema
from xmltemplate import validate as val

datadir = os.path.join(os.path.dirname(__file__), "data")

class TestSchemaLoader(test.TestCase):

    def test_ctr(self):
        loc = "schema.xsd"
        loader = schema.SchemaLoader("<schema />", loc, location=loc)
        self.assertEqual(loader.content, "<schema />")
        self.assertEqual(loader.location, loc)
        self.assertEqual(loader.name, loc)
        self.assertIsNone(loader.tree)

        self.assertIsNone(loader._hash)
        self.assertIsNotNone(loader.digest)
        
        self.assertEqual(len(loader.includes), 0)
        self.assertEqual(len(loader.imports), 0)

    def test_from_stream(self):
        schemafile = os.path.join(datadir, "experiments.xsd")
        with open(schemafile) as fd:
            loader = schema.SchemaLoader.from_stream(fd, "exp",
                                                     "experiments.xsd")
        self.assertEquals(loader.name, "exp")
        self.assertEquals(loader.location, "experiments.xsd")
        self.assertTrue("<?xml" in loader.content)

        with open(schemafile) as fd:
            loader = schema.SchemaLoader.from_stream(fd, "exp")
        self.assertEquals(loader.name, "exp")
        self.assertIsNone(loader.location)
        self.assertTrue("<?xml" in loader.content)

    def test_from_file(self):
        schemafile = os.path.join(datadir, "experiments.xsd")
        loader = schema.SchemaLoader.from_file(schemafile, "exp",
                                               "experiments.xsd")
        self.assertEquals(loader.name, "exp")
        self.assertEquals(loader.location, "experiments.xsd")
        self.assertTrue("<?xml" in loader.content)
        
        loader = schema.SchemaLoader.from_file(schemafile, "exp")
        self.assertEquals(loader.name, "exp")
        self.assertEquals(loader.location, schemafile)
        self.assertTrue("<?xml" in loader.content)
        
        loader = schema.SchemaLoader.from_file(schemafile)
        self.assertEquals(loader.name, schemafile)
        self.assertEquals(loader.location, schemafile)
        self.assertTrue("<?xml" in loader.content)

    def test_xml_validate(self):
        loader = create_loader("mylab.xsd")
        self.assertIsNone(loader.tree)
        self.assertIsNone(loader.valid8r)
        loader.xml_validate()
        self.assertIsNotNone(loader.tree)
        self.assertIsNone(loader.valid8r)

        loader = create_loader("badform.xsd")
        self.assertIsNone(loader.tree)
        with self.assertRaises(val.ValidationError):
            loader.xml_validate()
        self.assertIsNone(loader.tree)
        self.assertIsNone(loader.valid8r)

        # bad xsd is not caught in this method
        loader = create_loader("badxsd.xsd")
        self.assertIsNone(loader.tree)
        loader.xml_validate()
        self.assertIsNotNone(loader.tree)
        self.assertIsNone(loader.valid8r)
        
    def test_xsd_validate(self):
        loader = create_loader("mylab.xsd")
        self.assertIsNone(loader.tree)
        self.assertIsNone(loader.valid8r)
        loader.xsd_validate()
        self.assertIsNotNone(loader.tree)
        self.assertIsNotNone(loader.valid8r)

        loader = create_loader("badform.xsd")
        self.assertIsNone(loader.tree)
        self.assertIsNone(loader.valid8r)
        with self.assertRaises(val.ValidationError):
            loader.xsd_validate()
        self.assertIsNone(loader.tree)
        self.assertIsNone(loader.valid8r)

        loader = create_loader("badxsd.xsd")
        self.assertIsNone(loader.tree)
        with self.assertRaises(val.SchemaValidationError):
            loader.xsd_validate()
        self.assertIsNotNone(loader.tree)
        self.assertIsNone(loader.valid8r)
        
    def test_get_validation_errors(self):
        loader = create_loader("mylab.xsd")
        self.assertIsNone(loader.tree)
        errors = loader.get_validation_errors()
        self.assertIsNotNone(loader.tree)
        self.assertEquals(len(errors), 0)

        loader = create_loader("badform.xsd")
        self.assertIsNone(loader.tree)
        errors = loader.get_validation_errors()
        self.assertIsNone(loader.tree)
        self.assertEquals(len(errors), 1)

        loader = create_loader("badxsd.xsd")
        self.assertIsNone(loader.tree)
        errors = loader.get_validation_errors()
        self.assertIsNotNone(loader.tree)
        self.assertEquals(len(errors), 1)

    def test_check_namespace(self):
        loader = create_loader("mylab.xsd")
        self.assertIsNone(loader.tree)
        self.assertEquals(loader.name, "mylab.xsd")
        loader.check_namespace()
        self.assertIsNotNone(loader.tree)
        self.assertEquals(loader.namespace, "urn:mylab")


    def test_check_namespace2(self):
        loader = create_loader("nons.xsd", "nons")
        self.assertIsNone(loader.tree)
        self.assertEquals(loader.name, "nons")
        loader.check_namespace()
        self.assertIsNotNone(loader.tree)
        self.assertEquals(loader.namespace, "")

        loader = create_loader("nons.xsd")
        self.assertIsNone(loader.tree)
        self.assertIsNone(loader.namespace)
        loader.check_namespace()
        self.assertIsNotNone(loader.tree)
        self.assertEquals(loader.namespace, "")

        loader = create_loader("nons.xsd")
        self.assertIsNone(loader.tree)
        self.assertIsNone(loader.namespace)
        loader.name = "goober"
        loader.location = None
        loader.check_namespace()
        self.assertIsNotNone(loader.tree)
        self.assertEquals(loader.namespace, "")

        loader = create_loader("nons.xsd")
        self.assertIsNone(loader.tree)
        self.assertIsNone(loader.namespace)
        loader.location = None
        loader.check_namespace()
        self.assertIsNotNone(loader.tree)
        self.assertEquals(loader.namespace, "")

    def test_extract_prefixes(self):
        loader = create_loader("mylab.xsd", "mylab")
        self.assertIsNone(loader.tree)
        self.assertEquals(len(loader.prefixes), 0)
        loader.extract_prefixes()
        self.assertIsNotNone(loader.tree)
        self.assertIn("m", loader.prefixes)
        self.assertEquals(loader.prefixes['m'], "urn:mylab")
        self.assertIn("xs", loader.prefixes)
        self.assertEquals(loader.prefixes['xs'], "http://www.w3.org/2001/XMLSchema")
        self.assertEquals(len(loader.prefixes), 2)

@test.skipIf(not os.environ.get('MONGO_TESTDB_URL'),
             "test mongodb not available")
class TestSchemaLoaderDB(test.TestCase):

    def setUp(self):
        self.mc = setUpMongo()

    def tearDown(self):
        tearDownMongo(self.mc)
        self.mc.close()
        self.mc = None

    def test_load_simple(self):
        schemafile = "mylab.xsd"
        loader = create_loader(schemafile)
        loader.name = schemafile

        loader.load()

        schema = models.Schema.get_by_name(schemafile)
        self.assertIsNotNone(schema)
        self.assertEquals(schema.name, schemafile)
        self.assertEquals(schema.location, schemafile)
        self.assertEquals(schema.namespace, "urn:mylab")
        self.assertEquals(schema.prefixes['m'], "urn:mylab")
        self.assertTrue('xs' in schema.prefixes)

    def test_load_from_stream(self):
        schemafile = "mylab.xsd"
        schemapath = os.path.join(datadir, schemafile)
        with open(schemapath) as fd:
            schema.SchemaLoader.load_from_stream(fd, schemafile, schemapath)

        sch = models.Schema.get_by_name(schemafile)
        self.assertIsNotNone(sch)
        self.assertEquals(sch.name, schemafile)
        self.assertEquals(sch.location, schemapath)
        self.assertEquals(sch.namespace, "urn:mylab")
        self.assertEquals(sch.prefixes['m'], "urn:mylab")
        self.assertTrue('xs' in sch.prefixes)

    def test_load_from_file(self):
        schemafile = "mylab.xsd"
        schemapath = os.path.join(datadir, schemafile)
        schema.SchemaLoader.load_from_file(schemapath, schemafile)

        sch = models.Schema.get_by_name(schemafile)
        self.assertIsNotNone(sch)
        self.assertEquals(sch.name, schemafile)
        self.assertEquals(sch.location, schemapath)
        self.assertEquals(sch.namespace, "urn:mylab")
        self.assertEquals(sch.prefixes['m'], "urn:mylab")
        self.assertTrue('xs' in sch.prefixes)

    def test_load_2(self):
        self.test_load_simple()
        schemafile = "experiments.xsd"
        loader = create_loader(schemafile)
        loader.name = schemafile

        loader.load()

        schema = models.Schema.get_by_name(schemafile)
        self.assertIsNotNone(schema)
        self.assertEquals(schema.name, schemafile)
        self.assertEquals(schema.location, schemafile)
        self.assertEquals(schema.namespace, "urn:experiments")
        self.assertEquals(schema.prefixes['ex'], "urn:experiments")
        self.assertTrue('xs' in schema.prefixes)
        
    def test_import(self):
        schemafile = "experiments.xsd"
        loader = create_loader(schemafile)
        loader.name = schemafile
        loader.location = schemafile

        loader.load()

        schemafile = "microscopy.xsd"
        loader = create_loader(schemafile)
        loader.name = schemafile
        loader.location = schemafile

        #pdb.set_trace()
        loader.load()

        schema = models.Schema.get_by_name(schemafile)
        self.assertIsNotNone(schema)
        self.assertEquals(schema.name, schemafile)
        self.assertEquals(schema.location, schemafile)
        self.assertEquals(schema.namespace, "urn:microscopy")
        self.assertEquals(schema.prefixes['ex'], "urn:experiments")
        self.assertEquals(schema.prefixes['mi'], "urn:microscopy")
        self.assertTrue('xs' in schema.prefixes)
        self.assertEquals(len(schema.includes), 0)
        self.assertEquals(len(schema.imports), 1)

        importedname = schema.imports[0].split('::')[1]
        imported = models.Schema.get_by_name(importedname)
        self.assertIsNotNone(imported)
        self.assertEquals(imported.name, importedname)
        self.assertEquals(imported.name, "experiments.xsd")
        self.assertEquals(imported.namespace, "urn:experiments")
        
    def test_include(self):
        schemafile = "experiments.xsd"
        loader = create_loader(schemafile)
        loader.name = schemafile

        loader.load()

        schemafile = "microscopy-incl.xsd"
        loader = create_loader(schemafile)
        loader.name = schemafile

        # pdb.set_trace()
        loader.load()

        schema = models.Schema.get_by_name(schemafile)
        self.assertIsNotNone(schema)
        self.assertEquals(schema.name, schemafile)
        self.assertEquals(schema.location, schemafile)
        self.assertEquals(schema.namespace, "urn:experiments")
        self.assertEquals(schema.prefixes['ex'], "urn:experiments")
        self.assertTrue('mi' not in schema.prefixes)
        self.assertTrue('xs' in schema.prefixes)
        self.assertEquals(len(schema.includes), 1)
        self.assertEquals(len(schema.imports), 0)

        included = models.Schema.get_by_name(schema.includes[0].split('::')[1])
        self.assertIsNotNone(included)
        self.assertEquals(included.location, schema.includes[0].split('::')[0])
        self.assertEquals(included.namespace, "urn:experiments")

    def test_fmt_qname(self):
        schemafile = "mylab.xsd"
        loader = create_loader(schemafile)
        ns = "urn.labs"
        name = "Setup"
        self.assertEquals(loader._fmt_qname(ns, name), "{urn.labs}Setup")

    def test_split_qname(self):
        schemafile = "mylab.xsd"
        loader = create_loader(schemafile)
        ns = "urn.labs"
        name = "Setup"
        qname = loader._fmt_qname(ns, name)
        out = loader._split_qname(qname)
        self.assertEquals(out[0], ns)
        self.assertEquals(out[1], name)

    def test_resolve_qname(self):
        schemafile = "experiments.xsd"
        loader = create_loader(schemafile)
        loader.xml_validate()
        el = loader.tree.getroot()
        qname = loader._resolve_qname("ex:Goober", el, schema.XSD_NS)
        self.assertEquals(qname, "{urn:experiments}Goober")

        qname = loader._resolve_qname("Goober", el, schema.XSD_NS)
        self.assertEquals(qname, "{http://www.w3.org/2001/XMLSchema}Goober")

        with self.assertRaises(val.SchemaValidationError):
            qname = loader._resolve_qname("mi:Goober", el, schema.XSD_NS)
        
        

    def test_get_super_type(self):
        schemafile = "microscopy.xsd"
        loader = create_loader(schemafile)
        loader.xml_validate()
        # pdb.set_trace()
        cts = loader.tree.findall("//xs:complexType", {"xs": schema.XSD_NS})
        ct = filter(lambda t: t.get("name") == "ElectronMicroscope", cts)
        base = loader._get_super_type(ct[0])
        self.assertEquals(base, "{urn:experiments}Equipment")

    def test_find_type_in_schemadoc(self):
        loader = create_loader("experiments.xsd")
        loader.load()
        # pdb.set_trace()
        ansc = loader._find_type_in_schemadoc("{urn:experiments}Equipment",
                                              "experiments.xsd")
        self.assertEquals(ansc, [])
        
    def test_trace_anscestors_noparent(self):
        loader = create_loader("experiments.xsd")

        lu = loader._trace_anscestors( [('LabSetup', None)] )
        self.assertTrue( isinstance(lu, dict) )
        self.assertIn( 'LabSetup', lu )
        self.assertEquals( lu['LabSetup'], [] )
        
    def test_global_type_defined(self):
        loader = create_loader("experiments.xsd")
        loader.load()

        self.assertTrue(
            loader._global_type_defined("{urn:experiements.xsd}Equipment"))
        self.assertFalse(
            loader._global_type_defined("{urn:experiements.xsd}Goober"))
        

    def test_trace_anscestors(self):
        loader = create_loader("experiments.xsd")
        loader.load()
        loader = create_loader("microscopy.xsd")
        loader.resolve_imports()
        lu = loader._trace_anscestors([ ("VacuumPump",
                                         "{urn:experiments}Equipment") ])
        self.assertTrue("VacuumPump" in lu)
        self.assertEquals(lu["VacuumPump"], ["{urn:experiments}Equipment"])


def setUpMongo():
    return connect(host=os.environ['MONGO_TESTDB_URL'])

def tearDownMongo(mc):
    try:
        db = mc.get_default_database()
        mc.drop_database(db.name)
    except Exception, ex:
        pass

    
def create_loader(schemafile, name=None):
    with open(os.path.join(datadir, schemafile)) as fd:
        content = fd.read()
    if not name:
        name = schemafile    
    return schema.SchemaLoader(content, name=name, location=schemafile)

        
TESTS = "TestSchemaLoader TestSchemaLoaderDB".split()

def test_suite():
    suite = test.TestSuite()
    suite.addTests([test.makeSuite(TestSchemaLoader)])
    suite.addTests([test.makeSuite(TestSchemaLoaderDB)])
    return suite

if __name__ == '__main__':
    test.main()
