# import mgi.settings as settings
# from django import test
import unittest as test
import os, pdb
from mongoengine import connect

if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'xmltemplate.settings'
from xmltemplate import models
from xmltemplate import api

datadir = os.path.join(os.path.dirname(__file__), "data")

class TestLoadSchemaDoc(test.TestCase):

    def setUp(self):
        self.mc = setUpMongo()

    def tearDown(self):
        tearDownMongo(self.mc)
        self.mc.close()
        self.mc = None

    def get_file_content(self, filename):
        filepath = os.path.join(datadir, filename)
        with open(filepath) as fd:
            return fd.read()

    def test_addsimple(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        summ = api.loadSchemaDoc(content, "mylab", filename)

        self.assertTrue(summ['ok'])
        self.assertIn('success', summ['message'])
        self.assertEquals(summ['name'], "mylab")
        self.assertEquals(summ['location'], filename)
        self.assertEquals(summ['version'], 1)
        self.assertEquals(summ['description'], '')
        self.assertEquals(summ['version_comment'], 'initial version')
        self.assertTrue(summ['is_current'])
        self.assertFalse(summ['is_deleted'])

        schema = models.Schema.get_by_name('mylab')
        self.assertEquals(summ['name'], schema.name)
        self.assertEquals(summ['location'], schema.location)
        self.assertEquals(summ['version'], schema.version)
        self.assertEquals(summ['description'], schema.description)
        self.assertEquals(summ['version_comment'], schema.comment)
        self.assertEquals(summ['is_current'], schema.iscurrent)
        self.assertEquals(summ['is_deleted'], schema.deleted)
        
    def test_makecurrent(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        # pdb.set_trace()
        summ = api.loadSchemaDoc(content, "mylab", filename)
        summ = api.loadSchemaDoc(content, "mylab", filename)
        self.assertEquals(summ['version'], 2)
        self.assertFalse(summ['is_current'])
        self.assertEquals(summ['version_comment'], '')

        schema = models.Schema.get_by_name('mylab')
        self.assertEquals(schema.version, 1)

        summ = api.loadSchemaDoc(content, "mylab", filename, make_current=True)
        self.assertEquals(summ['version'], 3)
        self.assertTrue(summ['is_current'])
        self.assertEquals(summ['version_comment'], '')

        schema = models.Schema.get_by_name('mylab')
        self.assertEquals(schema.version, 3)

    def test_metadata(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        summ = api.loadSchemaDoc(content, "mylab", filename, "for your lab")
        self.assertTrue(summ['ok'])
        self.assertIn('success', summ['message'])
        self.assertEquals(summ['name'], "mylab")
        self.assertEquals(summ['location'], filename)
        self.assertEquals(summ['version'], 1)
        self.assertEquals(summ['description'], 'for your lab')
        self.assertEquals(summ['version_comment'], 'initial version')
        self.assertTrue(summ['is_current'])
        self.assertFalse(summ['is_deleted'])

        summ = api.loadSchemaDoc(content, "mylab", filename, about="added stuff")
        self.assertEquals(summ['version'], 2)
        self.assertEquals(summ['description'], 'for your lab')
        self.assertEquals(summ['version_comment'], 'added stuff')

        summ = api.loadSchemaDoc(content, "mylab", filename, "added more stuff")
        self.assertEquals(summ['version'], 3)
        self.assertEquals(summ['description'], 'for your lab')
        self.assertEquals(summ['version_comment'], 'added more stuff')

    def test_checkdigest(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        def count_versions(name):
            return len(models.SchemaVersion.objects.filter(name=name))

        # confirm normal loading with check_digest=True
        self.assertEquals(count_versions("mylab"), 0)
        summ = api.loadSchemaDoc(content, "mylab", filename, check_digest=True)
        self.assertEquals(count_versions("mylab"), 1)
        self.assertTrue(summ['is_current'])

        # see that we are reloading the same schema again
        summ = api.loadSchemaDoc(content, "mylab", filename, check_digest=True)
        self.assertEquals(count_versions("mylab"), 1)
        self.assertTrue(summ['is_current'])

        # confirm that reloading a deleted schem undeletes it
        schema = models.Schema.get_by_name("mylab")
        self.assertEquals(schema.version, 1)
        schema.delete()
        self.assertTrue(schema.deleted)

        summ = api.loadSchemaDoc(content, "mylab", filename, check_digest=True)
        self.assertEquals(summ['version'], 1)
        self.assertEquals(schema.version, 1)
        self.assertFalse(summ['is_deleted'])
        self.assertTrue(summ['is_current'])
        schema = models.Schema.get_by_name("mylab")
        self.assertEquals(schema.version, 1)
        self.assertFalse(schema.deleted)

        # test updating metadata
        self.assertEquals(schema.location, filename)
        self.assertEquals(schema.comment, 'initial version')
        summ = api.loadSchemaDoc(content, "mylab", "goober.xsd", about="yeah!",
                                 check_digest=True)
        self.assertEquals(summ['location'], "goober.xsd")
        self.assertEquals(summ['version_comment'], 'yeah!')
        schema = models.Schema.get_by_name("mylab")
        self.assertEquals(schema.location, "goober.xsd")
        self.assertEquals(schema.comment, 'yeah!')

    def test_badschema(self):
        filename = "badxsd.xsd"
        content = self.get_file_content(filename)
        summ = api.loadSchemaDoc(content, "mylab", filename)
        self.assertFalse(summ['ok'])
        self.assertIn('Validation Error: ', summ['message'])
        self.assertIn('errors', summ)

    def test_confused_include(self):
        filename = "microscopy-incl.xsd"
        content = self.get_file_content(filename)
        summ = api.loadSchemaDoc(content, "micro", filename)
        self.assertFalse(summ['ok'])
        self.assertIn('Failed to load', summ['message'])
        complaint = [e for e in summ['errors'] if 'experiments.xsd' in e]
        self.assertGreater(len(complaint), 0)

        # now let's create two differnt schemas the same location & namespace...
        filename = 'experiments.xsd'
        content = self.get_file_content(filename)
        summ = api.loadSchemaDoc(content, "experiments", filename)
        summ = api.loadSchemaDoc(content, "mylab", filename)

        schema = models.Schema.get_by_name("experiments")
        scs = models.SchemaCommon.get_all_by_namespace(schema.namespace)
        self.assertEqual(len(scs), 2)

        # ...and now require an include
        filename = "microscopy-incl.xsd"
        content = self.get_file_content(filename)
        summ = api.loadSchemaDoc(content, "micro", filename)
        self.assertFalse(summ['ok'])
        self.assertIn('Failed to load', summ['message'])
        complaint = [e for e in summ['errors'] if 'experiments.xsd' in e]
        self.assertGreater(len(complaint), 0)
        self.assertIn('hints', summ)

        # now remedy the situation using loc_finder
        use = { "experiments.xsd": "experiments" }
        #pdb.set_trace()
        summ = api.loadSchemaDoc(content, "micro", filename, loc_finder=use)
        self.assertTrue(summ['ok'])
        
    def test_confused_import(self):
        filename = "microscopy.xsd"
        content = self.get_file_content(filename)
        summ = api.loadSchemaDoc(content, "micro", filename)
        self.assertFalse(summ['ok'])
        self.assertIn('Failed to load', summ['message'])
        complaint = [e for e in summ['errors'] if 'urn:experiments' in e]
        self.assertGreater(len(complaint), 0)

        # now let's create two differnt schemas the same location & namespace...
        filename = 'experiments.xsd'
        content = self.get_file_content(filename)
        summ = api.loadSchemaDoc(content, "experiments", filename)
        summ = api.loadSchemaDoc(content, "mylab", filename)

        schema = models.Schema.get_by_name("experiments")
        scs = models.SchemaCommon.get_all_by_namespace(schema.namespace)
        self.assertEqual(len(scs), 2)

        # ...and now require an include
        filename = "microscopy.xsd"
        content = self.get_file_content(filename)
        summ = api.loadSchemaDoc(content, "micro", filename)
        self.assertFalse(summ['ok'])
        self.assertIn('Failed to load', summ['message'])
        complaint = [e for e in summ['errors'] if 'experiments.xsd' in e]
        self.assertGreater(len(complaint), 0)
        self.assertIn('hints', summ)

        # now remedy the situation using loc_finder
        use = { "urn:experiments": "experiments" }
        #pdb.set_trace()
        summ = api.loadSchemaDoc(content, "micro", filename, ns_finder=use)
        self.assertTrue(summ['ok'])

class TestAllSchemaDocs(test.TestCase):

    def setUp(self):
        self.mc = setUpMongo()

    def tearDown(self):
        tearDownMongo(self.mc)
        self.mc.close()
        self.mc = None

    def get_file_content(self, filename):
        filepath = os.path.join(datadir, filename)
        with open(filepath) as fd:
            return fd.read()

    def test_summarize(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        api.loadSchemaDoc(content, "mylab", filename)

        schema = models.Schema.get_by_name('mylab')
        summ = api.AllSchemaDocs.summarize(schema)
        # self.assertTrue(summ['ok'])
        self.assertEqual(summ['name'], schema.name)
        self.assertEqual(summ['namespace'], schema.namespace)
        self.assertEqual(summ['version'], schema.version)
        self.assertEqual(summ['location'], schema.location)
        self.assertEqual(summ['description'], schema.description)
        self.assertEqual(summ['version_comment'], schema.comment)

    def test_list(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        api.loadSchemaDoc(content, "mylab", filename)

        filename = "experiments.xsd"
        content = self.get_file_content(filename)
        api.loadSchemaDoc(content, "experiments", filename)

        summ = api.AllSchemaDocs.list()
        self.assertEqual(len(summ), 2)
        self.assertTrue(isinstance(summ[0], dict))
        self.assertIn('experiments', [s['name'] for s in summ])
        self.assertIn('mylab', [s['name'] for s in summ])
        self.assertIn('experiments.xsd', [s['location'] for s in summ])
        self.assertIn('mylab.xsd', [s['location'] for s in summ])

        summ = api.AllSchemaDocs.list('names')
        self.assertEqual(len(summ), 2)
        self.assertIn('experiments', summ)
        self.assertIn('mylab', summ)

        summ = api.AllSchemaDocs.list('full')
        self.assertEqual(len(summ), 2)
        self.assertTrue(isinstance(summ[0], dict))
        self.assertIn('experiments', [s['name'] for s in summ])
        self.assertIn('mylab', [s['name'] for s in summ])
        self.assertIn('experiments.xsd', [s['location'] for s in summ])
        self.assertIn('mylab.xsd', [s['location'] for s in summ])
        self.assertIn('content', summ[0])
        self.assertGreater(len(summ[0]['content']), 0)

        summ = api.AllSchemaDocs.list('content')
        self.assertEqual(len(summ), 2)
        self.assertIn('<?xml', summ[0])
        self.assertIn('<?xml', summ[1])

    def test_add(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        summ = api.AllSchemaDocs.add(content, "mylab", filename)

        self.assertTrue(summ['ok'])
        self.assertIn('success', summ['message'])
        self.assertEquals(summ['name'], "mylab")
        self.assertEquals(summ['location'], filename)
        self.assertEquals(summ['version'], 1)
        self.assertEquals(summ['description'], '')
        self.assertEquals(summ['version_comment'], 'initial version')
        self.assertTrue(summ['is_current'])
        self.assertFalse(summ['is_deleted'])
        
    def test_add_withlocfinder(self):
        # now let's create two differnt schemas the same location & namespace...
        filename = 'experiments.xsd'
        content = self.get_file_content(filename)
        summ = api.AllSchemaDocs.add(content, "experiments", filename)
        summ = api.AllSchemaDocs.add(content, "mylab", filename)

        schema = models.Schema.get_by_name("experiments")
        scs = models.SchemaCommon.get_all_by_namespace(schema.namespace)
        self.assertEqual(len(scs), 2)
        
        # add with loc_finder
        filename = "microscopy-incl.xsd"
        content = self.get_file_content(filename)
        use = { "experiments.xsd": "experiments" }
        summ = api.AllSchemaDocs.add(content, "micro", filename, loc_finder=use)
        self.assertTrue(summ['ok'])
        
    def test_add_withnsfinder(self):
        # now let's create two differnt schemas the same location & namespace...
        filename = 'experiments.xsd'
        content = self.get_file_content(filename)
        summ = api.AllSchemaDocs.add(content, "experiments", filename)
        summ = api.AllSchemaDocs.add(content, "mylab", filename)

        schema = models.Schema.get_by_name("experiments")
        scs = models.SchemaCommon.get_all_by_namespace(schema.namespace)
        self.assertEqual(len(scs), 2)
        
        # add with ns_finder
        filename = "microscopy.xsd"
        content = self.get_file_content(filename)
        use = { "urn:experiments": "experiments" }
        summ = api.AllSchemaDocs.add(content, "micro", filename, ns_finder=use)
        self.assertTrue(summ['ok'])

class TestSchemaDoc(test.TestCase):
    
    def setUp(self):
        self.mc = setUpMongo()

    def tearDown(self):
        tearDownMongo(self.mc)
        self.mc.close()
        self.mc = None

    def get_file_content(self, filename):
        filepath = os.path.join(datadir, filename)
        with open(filepath) as fd:
            return fd.read()

    def test_versions(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        api.loadSchemaDoc(content, "mylab", filename)
        schema = models.Schema.get_by_name('mylab')

        self.assertEquals(api.SchemaDoc.versions(schema), [1])

        # add 2 more versions
        api.loadSchemaDoc(content, "mylab", filename)
        api.loadSchemaDoc(content, "mylab", filename)
        self.assertEquals(api.SchemaDoc.versions(schema), [1, 2, 3])

        schema = models.Schema.get_by_name('mylab', 3)
        schema.make_current()
        self.assertEquals(api.SchemaDoc.versions(schema), [1, 2, 3])
        
        schema = models.Schema.get_by_name('mylab', 2)
        schema.delete()
        self.assertEquals(api.SchemaDoc.versions(schema), [1, 3])
        

    def test_summarize(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        api.loadSchemaDoc(content, "mylab", filename)

        schema = models.Schema.get_by_name('mylab')
        summ = api.SchemaDoc.summarize(schema)
        # self.assertTrue(summ['ok'])
        self.assertEqual(summ['name'], schema.name)
        self.assertEqual(summ['namespace'], schema.namespace)
        self.assertEqual(summ['current_version'], schema.current)
        self.assertEqual(summ['location'], schema.location)
        self.assertEqual(summ['description'], schema.description)
        self.assertEqual(summ['version_comment'], schema.comment)
        self.assertEqual(summ['versions_available'], [schema.current])

        # add 2 more versions...
        api.loadSchemaDoc(content, "mylab", filename)
        api.loadSchemaDoc(content, "mylab", filename)

        # ...delete one of them...
        schema = models.Schema.get_by_name('mylab', 2)
        schema.delete()

        schema = models.Schema.get_by_name('mylab')
        summ = api.SchemaDoc.summarize(schema)
        summ['versions_available'].sort()
        self.assertEqual(summ['name'], schema.name)
        self.assertEqual(summ['namespace'], schema.namespace)
        self.assertEqual(summ['current_version'], schema.current)
        self.assertEqual(summ['location'], schema.location)
        self.assertEqual(summ['description'], schema.description)
        self.assertEqual(summ['version_comment'], schema.comment)
        self.assertEqual(summ['versions_available'], [1, 3])
        
    def test_add(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        summ = api.SchemaDoc.add(content, "mylab", filename, "for your lab")

        self.assertTrue(summ['ok'])
        self.assertIn('success', summ['message'])
        self.assertEquals(summ['name'], "mylab")
        self.assertEquals(summ['location'], filename)
        self.assertEquals(summ['version'], 1)
        self.assertEquals(summ['description'], 'for your lab')
        self.assertEquals(summ['version_comment'], 'initial version')
        self.assertTrue(summ['is_current'])
        self.assertFalse(summ['is_deleted'])

        # try "PUT"ing again
        summ = api.SchemaDoc.add(content, "mylab", filename, "same version")
        self.assertTrue(summ['ok'])
        self.assertIn('success', summ['message'])
        self.assertIn('update', summ['message'])
        self.assertEquals(summ['name'], "mylab")
        self.assertEquals(summ['location'], filename)
        self.assertEquals(summ['version'], 1)
        self.assertEquals(summ['description'], 'for your lab')
        self.assertEquals(summ['version_comment'], 'same version')
        self.assertTrue(summ['is_current'])
        self.assertFalse(summ['is_deleted'])

        filename = "experiments.xsd"
        content = self.get_file_content(filename)
        summ = api.SchemaDoc.add(content, "mylab", filename, "different version")
        self.assertTrue(summ['ok'])
        self.assertIn('success', summ['message'])
        self.assertEquals(summ['name'], "mylab")
        self.assertEquals(summ['location'], filename)
        self.assertEquals(summ['version'], 2)
        self.assertEquals(summ['description'], 'for your lab')
        self.assertEquals(summ['version_comment'], 'different version')
        self.assertFalse(summ['is_current'])
        self.assertFalse(summ['is_deleted'])

        summ = api.SchemaDoc.add(content, "mylab", filename, make_current=True)
        self.assertTrue(summ['ok'])
        self.assertIn('success', summ['message'])
        self.assertIn('update', summ['message'])
        self.assertEquals(summ['name'], "mylab")
        self.assertEquals(summ['location'], filename)
        self.assertEquals(summ['version'], 2)
        self.assertEquals(summ['description'], 'for your lab')
        self.assertEquals(summ['version_comment'], 'different version')
        self.assertTrue(summ['is_current'])
        self.assertFalse(summ['is_deleted'])

    def test_add_withlocfinder(self):
        # now let's create two differnt schemas the same location & namespace...
        filename = 'experiments.xsd'
        content = self.get_file_content(filename)
        summ = api.SchemaDoc.add(content, "experiments", filename)
        summ = api.SchemaDoc.add(content, "mylab", filename)

        schema = models.Schema.get_by_name("experiments")
        scs = models.SchemaCommon.get_all_by_namespace(schema.namespace)
        self.assertEqual(len(scs), 2)
        
        # add with loc_finder
        filename = "microscopy-incl.xsd"
        content = self.get_file_content(filename)
        use = { "experiments.xsd": "experiments" }
        summ = api.SchemaDoc.add(content, "micro", filename, loc_finder=use)
        self.assertTrue(summ['ok'])
        
    def test_add_withnsfinder(self):
        # now let's create two differnt schemas the same location & namespace...
        filename = 'experiments.xsd'
        content = self.get_file_content(filename)
        summ = api.SchemaDoc.add(content, "experiments", filename)
        summ = api.SchemaDoc.add(content, "mylab", filename)

        schema = models.Schema.get_by_name("experiments")
        scs = models.SchemaCommon.get_all_by_namespace(schema.namespace)
        self.assertEqual(len(scs), 2)
        
        # add with ns_finder
        filename = "microscopy.xsd"
        content = self.get_file_content(filename)
        use = { "urn:experiments": "experiments" }
        summ = api.SchemaDoc.add(content, "micro", filename, ns_finder=use)
        self.assertTrue(summ['ok'])

    def test_get_view(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        summ = api.SchemaDoc.add(content, "mylab", filename, "for your lab")

        self.assertEquals(api.SchemaDoc.get_view("mylab", "versions"), [1])
        
        summ = api.SchemaDoc.get_view("mylab", "summary")
        self.assertEqual(summ['name'], "mylab")
        self.assertEqual(summ['current_version'], 1)
        self.assertEqual(summ['location'], filename)
        self.assertEqual(summ['description'], "for your lab")
        self.assertEqual(summ['version_comment'], "initial version")
        self.assertEqual(summ['versions_available'], [1])
        
        summ = api.SchemaDoc.get_view("mylab")
        self.assertEqual(summ['name'], "mylab")
        self.assertEqual(summ['current_version'], 1)
        self.assertEqual(summ['location'], filename)
        self.assertEqual(summ['description'], "for your lab")
        self.assertEqual(summ['version_comment'], "initial version")
        self.assertEqual(summ['versions_available'], [1])
        self.assertIn('content', summ)
        self.assertIn('<?xml', summ['content'])
        
        content = api.SchemaDoc.get_view("mylab", 'xml')
        self.assertIn('<?xml', content)
        content = api.SchemaDoc.get_view("mylab", 'xsd')
        self.assertIn('<?xml', content)
        
    def test_set_desc(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        summ = api.SchemaDoc.add(content, "mylab", filename, "for your lab")

        summ = api.SchemaDoc.set_description("mylab", "for my lab")
        self.assertEqual(summ['name'], "mylab")
        self.assertEqual(summ['description'], "for my lab")
        schema = models.Schema.get_by_name("mylab")
        self.assertEqual(schema.desc, "for my lab")
        
class TestSchemaDocVersion(test.TestCase):

    def setUp(self):
        self.mc = setUpMongo()

    def tearDown(self):
        tearDownMongo(self.mc)
        self.mc.close()
        self.mc = None

    def get_file_content(self, filename):
        filepath = os.path.join(datadir, filename)
        with open(filepath) as fd:
            return fd.read()

    def test_summarize(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        api.loadSchemaDoc(content, "mylab", filename)

        schema = models.Schema.get_by_name('mylab')
        summ = api.SchemaDocVersion.summarize(schema)
        # self.assertTrue(summ['ok'])
        self.assertEqual(summ['name'], schema.name)
        self.assertEqual(summ['namespace'], schema.namespace)
        self.assertEqual(summ['version'], schema.version)
        self.assertEqual(summ['location'], schema.location)
        self.assertEqual(summ['description'], schema.description)
        self.assertEqual(summ['version_comment'], schema.comment)
        self.assertEqual(summ['is_current'], schema.iscurrent)
        self.assertEqual(summ['is_deleted'], schema.deleted)

    def test_get_view(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        summ = api.SchemaDoc.add(content, "mylab", filename, "for your lab")

        summ = api.SchemaDocVersion.get_view("mylab", 1, "summary")
        self.assertEqual(summ['name'], "mylab")
        self.assertEqual(summ['location'], filename)
        self.assertEqual(summ['description'], "for your lab")
        self.assertEqual(summ['version'], 1)
        self.assertEqual(summ['version_comment'], "initial version")
        
        summ = api.SchemaDocVersion.get_view("mylab", 1)
        self.assertEqual(summ['name'], "mylab")
        self.assertEqual(summ['location'], filename)
        self.assertEqual(summ['description'], "for your lab")
        self.assertEqual(summ['version'], 1)
        self.assertEqual(summ['version_comment'], "initial version")
        self.assertIn('content', summ)
        self.assertIn('<?xml', summ['content'])
        
        content = api.SchemaDocVersion.get_view("mylab", 1, 'xml')
        self.assertIn('<?xml', content)
        content = api.SchemaDocVersion.get_view("mylab", 1, 'xsd')
        self.assertIn('<?xml', content)
        
        summ = api.loadSchemaDoc(content, "mylab", filename, "next version")
        summ = api.SchemaDocVersion.get_view("mylab", 1, "summary")
        self.assertEqual(summ['version'], 1)
        self.assertEqual(summ['version_comment'], "initial version")
        summ = api.SchemaDocVersion.get_view("mylab", 2, "summary")
        self.assertEqual(summ['version'], 2)
        self.assertEqual(summ['version_comment'], "next version")

    def test_make_current(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        summ = api.SchemaDoc.add(content, "mylab", filename, "for your lab")
        self.assertEqual(summ['version'], 1)
        self.assertTrue(summ['is_current'])

        filename = "experiments.xsd"
        content = self.get_file_content(filename)
        summ = api.SchemaDoc.add(content, "mylab", filename, "update")
        self.assertEqual(summ['version'], 2)
        self.assertFalse(summ['is_current'])

        schema = models.Schema.get_by_name("mylab")
        self.assertEqual(schema.current, 1)
        summ = api.SchemaDocVersion.make_current("mylab", 2)
        schema = models.Schema.get_by_name("mylab")
        self.assertEqual(schema.current, 2)

    def test_delete(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        summ = api.SchemaDoc.add(content, "mylab", filename, "for your lab")
        self.assertEqual(summ['version'], 1)
        self.assertTrue(summ['is_current'])

        filename = "experiments.xsd"
        content = self.get_file_content(filename)
        summ = api.SchemaDoc.add(content, "mylab", filename, "update",
                                 make_current=True)
        self.assertEqual(summ['version'], 2)
        self.assertTrue(summ['is_current'])

        summ = api.SchemaDocVersion.delete_version("mylab", 2)
        self.assertTrue(summ['is_deleted'])

        self.assertEquals(api.SchemaDoc.get_view("mylab", 'versions'), [1])
        summ = api.SchemaDocVersion.get_view("mylab", 1, "summary")
        self.assertFalse(summ['is_deleted'])
        self.assertTrue(summ['is_current'])

        summ = api.SchemaDocVersion.undelete("mylab", 2)
        self.assertFalse(summ['is_deleted'])

        summ = api.SchemaDocVersion.get_view("mylab", 2, "summary")
        self.assertEqual(summ['version'], 2)
        self.assertFalse(summ['is_deleted'])
        self.assertFalse(summ['is_current'])

    def test_set_meta(self):
        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        summ = api.SchemaDoc.add(content, "mylab", filename, "for your lab")
        self.assertEqual(summ['location'], filename)
        self.assertEqual(summ['version_comment'], "initial version")

        summ = api.SchemaDocVersion.set_meta("mylab", 1, "boo", "outer space")
        self.assertEqual(summ['location'], 'outer space')
        self.assertEqual(summ['version_comment'], "boo")
        summ = api.SchemaDocVersion.get_view("mylab", 1, "summary")
        self.assertEqual(summ['location'], 'outer space')
        self.assertEqual(summ['version_comment'], "boo")

        
class TestSettings(test.TestCase):

    def test_testing(self):
        from xmltemplate import settings
        self.assertEquals(settings.django_testing, "True")
        self.assertTrue(settings.UNIT_TESTING)
        self.assertNotEquals(settings.LOGGING['handlers'], {})
        self.assertEquals(settings.LOGGING['loggers'], {})


def setUpMongo():
    return connect(host=os.environ['MONGO_TESTDB_URL'])

def tearDownMongo(mc):
    try:
        db = mc.get_default_database()
        mc.drop_database(db.name)
    except Exception, ex:
        pass

    
TESTS = "TestLoadSchemaDco TestAllSchemaDocs TestSchemaDoc TestSchemaDocVersion TestSettings".split()

def test_suite():
    suite = test.TestSuite()
    suite.addTests([test.makeSuite(TestLoadSchemaDco)])
    return suite

if __name__ == '__main__':
    test.main()
