# import mgi.settings as settings
# from django import test
import unittest as test
import os, pdb
from mongoengine import connect

from xmltemplate import models
#from mgi import settings

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
class TestSchemaModels(test.TestCase):

    # mc = None

    # @classmethod
    # def setUpClass(cls):
    #    mc = setUpMongo()
    #    tearDownMongo(mc)
    #    mc.close()

    def setUp(self):
        self.mc = setUpMongo()

    def tearDown(self):
        tearDownMongo(self.mc)
        self.mc.close()
        self.mc = None

    def test_load_schema(self):
        ns = "urn:experiments"
        #pdb.set_trace()
        schema = models.SchemaCommon(namespace=ns, name="goober", current=1)
                                      
        schema.save()
        schemaVer = models.SchemaVersion(name="goober", common=schema,
                                         location="goober.xsd",
                                         content="<schema />", digest="xxx")
        schemaVer.save()

        ver = models.SchemaVersion.objects.\
                     filter(deleted=False).filter(name="goober")
        self.assertEquals(len(ver), 1)
        ver = ver[0]
        self.assertEquals(ver.name, "goober")
        self.assertEquals(ver.common.name, ver.name)
        self.assertEquals(ver.common.namespace, ns)
        self.assertEquals(ver.common.current, ver.version)
        self.assertEquals(ver.common.name, "goober")
        self.assertEquals(ver.location, "goober.xsd")
        self.assertEquals(ver.content, "<schema />")
        self.assertEquals(ver.digest, "xxx")
        self.assertEquals(ver.includes, [])
        self.assertEquals(ver.imports, [])
        self.assertEquals(ver.prefixes, {})

    def test_load_template(self):
        ns = "urn:experiments"
        self.test_load_schema()
        ver = models.SchemaVersion.objects.\
                     filter(deleted=False).filter(name="goober")[0]
        
        tmpl = models.TemplateCommon(name="goobers", current=1,
                                      root="{urn:experiments}root")
        tmpl.save()
        tmplver = models.TemplateVersion(name=tmpl.name, common=tmpl,
                                         schema=ver, label="blah")
        tmplver.save()
                                         
        ver = models.TemplateVersion.objects.\
                     filter(deleted=False).filter(name="goobers")
        self.assertEquals(len(ver), 1)
        ver = ver[0]
        self.assertEquals(ver.name, "goobers")
        self.assertEquals(ver.common.name, ver.name)
        self.assertEquals(ver.common.current, ver.version)
        self.assertEquals(ver.common.root, "{urn:experiments}root")
        self.assertEquals(ver.schema.common.namespace, "urn:experiments")
        self.assertEquals(ver.label, "blah")

    def test_schema(self):
        ns = "urn:experiments"
        self.test_load_schema()
        ver = models.SchemaVersion.objects().filter(name="goober")[0]
        schema = models.Schema(ver)
        self.assertEquals(schema.namespace, ns)
        self.assertEquals(schema.name, "goober")
        self.assertEquals(schema.location, "goober.xsd")
        self.assertEquals(schema.content, "<schema />")
        self.assertEquals(schema.digest, "xxx")
        self.assertEquals(schema.includes, [])
        self.assertEquals(schema.imports, [])
        self.assertEquals(schema.prefixes, {})

    def test_find(self):
        ns = "urn:experiments"
        self.test_load_schema()
        found = models.Schema.find(namespace=ns, deleted=False, name="goober")
        self.assertEquals(len(found), 1)
        self.assertEquals(found[0].namespace, ns)
        self.assertEquals(found[0].name, "goober")
        
    def test_find_one(self):
        ns = "urn:experiments"
        self.test_load_schema()
        found = models.Schema._find_one(namespace=ns, deleted=False, name="goober")
        self.assertEquals(found.namespace, ns)
        self.assertEquals(found.name, "goober")
        
        found = models.Schema._find_one(namespace=ns, deleted=True)
        self.assertIsNone(found)

    def test_get_all_by_namespace(self):
        ns = "urn:experiments"
        self.test_load_schema()
        found = models.Schema.get_all_by_namespace(ns)
        self.assertEquals(len(found), 1)
        self.assertEquals(found[0].namespace, ns)
        
        found = models.Schema.get_all_by_namespace("goob")
        self.assertEquals(len(found), 0)
        
    def test_get_by_name(self):
        name = "goober"
        self.test_load_schema()
        found = models.Schema.get_by_name(name)
        self.assertIsNotNone(found)
        self.assertEquals(found.name, name)
        
        found = models.Schema.get_by_name(name, version=1)
        self.assertIsNotNone(found)
        self.assertEquals(found.name, name)
        
        found = models.Schema.get_by_name(name, version=2)
        self.assertIsNone(found)
        
        found = models.Schema.get_by_name("goob")
        self.assertIsNone(found)


@test.skipIf(not os.environ.get('MONGO_TESTDB_URL'),
             "test mongodb not available")
class TestTemplateModels(test.TestCase):

    mc = None

    def setUp(self):
        self.mc = setUpMongo()

    def tearDown(self):
        tearDownMongo(self.mc)
        self.mc.close()
        self.mc = None

    def test_load_template(self):
        nm = "experiments"
        ns = "urn:experiments"
        #pdb.set_trace()
        schema = models.SchemaCommon(namespace=ns, name="goober", current=1)
                                      
        schema.save()
        schemaVer = models.SchemaVersion(name="goober", common=schema,
                                         location="goober.xsd",
                                         content="<schema />", digest="xxx")
        schemaVer.save()
        
        #pdb.set_trace()
        tmpl = models.TemplateCommon(name=nm, root="{urn:experiments}lab",
                                     current=1)
                                      
        tmpl.save()
        tmplVer = models.TemplateVersion(name=nm, common=tmpl,schema=schemaVer,
                                         label="Title")
        tmplVer.save()

        ver = models.TemplateVersion.objects.\
                     filter(deleted=False).filter(name=nm)
        self.assertEquals(len(ver), 1)
        ver = ver[0]
        self.assertEquals(ver.name, nm)
        self.assertEquals(ver.common.name, ver.name)
        self.assertEquals(ver.common.current, ver.version)
        self.assertEquals(ver.common.root, "{urn:experiments}lab")
        self.assertEquals(ver.schema.common.namespace, "urn:experiments")
        self.assertEquals(ver.schema.location, "goober.xsd")
        self.assertEquals(ver.schema.content, "<schema />")
        self.assertEquals(ver.schema.digest, "xxx")
        self.assertEquals(ver.label, "Title")

    def test_template(self):
        ns = "urn:experiments"
        nm = "experiments"
        self.test_load_template()
        ver = models.TemplateVersion.objects().filter(name=nm)[0]
        tmpl = models.Template(ver)

        self.assertEquals(tmpl.name, nm)
        self.assertEquals(tmpl.current, ver.version)
        self.assertEquals(tmpl.root, "{urn:experiments}lab")
        self.assertEquals(tmpl.schema.common.namespace, "urn:experiments")
        self.assertEquals(tmpl.schema.location, "goober.xsd")
        self.assertEquals(tmpl.schema.content, "<schema />")
        self.assertEquals(tmpl.schema.digest, "xxx")
        self.assertEquals(tmpl.label, "Title")

    def test_find(self):
        ns = "urn:experiments"
        nm = "experiments"
        self.test_load_template()
        found = models.Template.find(name=nm, deleted=False, label="Title")
        self.assertEquals(len(found), 1)
        self.assertEquals(found[0].name, nm)
        self.assertEquals(found[0].label, "Title")
        
    def test_find_one(self):
        nm = "experiments"
        self.test_load_template()
        found = models.Template._find_one(name=nm, deleted=False, label="Title")
        self.assertEquals(found.name, nm)
        self.assertEquals(found.label, "Title")
        
        found = models.Schema._find_one(name=nm, deleted=True)
        self.assertIsNone(found)

    def test_get_by_name(self):
        name = "experiments"
        self.test_load_template()
        found = models.Template.get_by_name(name)
        self.assertIsNotNone(found)
        self.assertEquals(found.name, name)
        
        found = models.Template.get_by_name(name, version=1)
        self.assertIsNotNone(found)
        self.assertEquals(found.name, name)
        
        found = models.Template.get_by_name(name, version=2)
        self.assertIsNone(found)
        
        found = models.Template.get_by_name("goob")
        self.assertIsNone(found)

if __name__ == '__main__':
    test.main()
