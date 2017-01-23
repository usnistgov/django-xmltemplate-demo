# import mgi.settings as settings
# from django import test
import unittest as test
import os, pdb, json
from django.test import Client
from mongoengine import connect

if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'xmltemplate.settings'
from xmltemplate import models
from xmltemplate import api

datadir = os.path.join(os.path.dirname(__file__), "data")

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

    def test_get(self):
        client = Client()
        res = client.get('/schemas/')
        self.assertEqual(res.status_code, 200)
        
        self.assertEqual(res.content, '[]')
        data = json.loads(res.content)
        self.assertEqual(len(data), 0)

        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        summ = api.loadSchemaDoc(content, "mylab", filename)

        res = client.get('/schemas/')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'mylab')
        self.assertEqual(data[0]['current_version'], 1)

        res = client.get('/schemas/', {'view': 'names'})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], 'mylab')

    def test_post(self):
        client = Client()
        res = client.get('/schemas/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content, '[]')

        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        data = json.dumps({'location': filename, 'name': "mylab",
                           'description': "4R lab", 'content': content})
        res = client.post('/schemas/', content_type='application/json',
                          data=data)
        data = json.loads(res.content)
        self.assertTrue(data['ok'])
        self.assertEqual(data['name'], 'mylab')
        self.assertEqual(data['location'], filename)
        self.assertEqual(data['description'], '4R lab')
        self.assertEqual(data['version'], 1)
        
        #pdb.set_trace()
        res = client.post('/schemas/?name=lab&description=4Rlab' +
                          '&location=mylab.xsd', content_type='application/xml',
                          data=content)
        data = json.loads(res.content)
        self.assertTrue(data['ok'])
        self.assertEqual(data['name'], 'lab')
        self.assertEqual(data['location'], filename)
        self.assertEqual(data['description'], '4Rlab')
        self.assertEqual(data['version'], 1)

        res = client.get('/schemas/', {'view': 'names'})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(len(data), 2)
        self.assertIn('mylab', data)
        self.assertIn('lab', data)
        
    def test_missing_name(self):
        client = Client()
        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        data = json.dumps({'location': filename, 
                           'description': "4R lab", 'content': content})
        res = client.post('/schemas/', content_type='application/json',
                          data=data)
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.content)
        self.assertFalse(data['ok'])
        self.assertIn("Missing", data['message'])
        self.assertIn("name", data['message'])
        
    def test_missing_content(self):
        client = Client()
        data = json.dumps({'name': "mylab", 'description': "4R lab"})
        res = client.post('/schemas/', content_type='application/json',
                          data=data)
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.content)
        self.assertFalse(data['ok'])
        self.assertIn("Missing", data['message'])
        self.assertIn("content", data['message'])
        
        data = json.dumps({'name': "mylab",
                           'description': "4R lab", 'content': ''})
        res = client.post('/schemas/', content_type='application/json',
                          data=data)
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.content)
        self.assertFalse(data['ok'])
        self.assertIn("content", data['message'])
        
    def test_repost(self):
        client = Client()

        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        data = json.dumps({'location': filename, 'name': "mylab",
                           'description': "4R lab", 'content': content})
        res = client.post('/schemas/', content_type='application/json',
                          data=data)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])
                          
        res = client.post('/schemas/', content_type='application/json',
                          data=data)
        rdata = json.loads(res.content)
        self.assertFalse(rdata['ok'])
        self.assertEqual(res.status_code, 409)
        
    def test_badxml(self):
        client = Client()

        filename = "badform.xsd"
        content = self.get_file_content(filename)
        data = json.dumps({'location': filename, 'name': "mylab",
                           'description': "4R lab", 'content': content})
        res = client.post('/schemas/', content_type='application/json',
                          data=data)
        rdata = json.loads(res.content)

    def test_badmethod(self):
        client = Client()
        res = client.get('/schemas/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content, '[]')

        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        data = json.dumps({'location': filename, 'name': "mylab",
                           'description': "4R lab", 'content': content})
        res = client.put('/schemas/', content_type='application/json',
                          data=data)
        self.assertEqual(res.status_code, 405)

        res = client.patch('/schemas/', content_type='application/json',
                          data=data)
        self.assertEqual(res.status_code, 405)

        res = client.delete('/schemas/')
        self.assertEqual(res.status_code, 405)



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

    def test_get(self):
        client = Client()
        res = client.get('/schemas/mylab')
        self.assertEqual(res.status_code, 404)
        
        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        summ = api.loadSchemaDoc(content, "mylab", filename)

        res = client.get('/schemas/mylab')
        self.assertEqual(res.status_code, 200)

        data = json.loads(res.content)
        self.assertEqual(data['name'], 'mylab')
        self.assertEqual(data['current_version'], 1)

        res = client.get('/schemas/mylab', {'view': 'versions'})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], 1)

    def test_put(self):
        client = Client()
        res = client.get('/schemas/mylab')
        self.assertEqual(res.status_code, 404)
        
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        data = json.dumps({'location': filename, 
                           'about': "4R lab", 'content': content})
        res = client.put('/schemas/mylab', content_type='application/json',
                         data=data)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])
        self.assertEqual(rdata['name'], 'mylab')
        self.assertEqual(rdata['location'], filename)
        self.assertEqual(rdata['description'], '4R lab')
        self.assertEqual(rdata['version'], 1)
        self.assertTrue(rdata['is_current'])
        
        res = client.put('/schemas/exp?about=4Rlab&location=mylab.xsd',
                         content_type='application/xml', data=content)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])
        self.assertEqual(rdata['name'], 'exp')
        self.assertEqual(rdata['location'], filename)
        self.assertEqual(rdata['description'], '4Rlab')
        self.assertEqual(rdata['version'], 1)
        self.assertTrue(rdata['is_current'])
        
        filename = "experiments.xsd"
        content = self.get_file_content(filename)
        res = client.put('/schemas/exp?about=next&location=exp.xsd',
                         content_type='application/xml', data=content)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])
        self.assertEqual(rdata['name'], 'exp')
        self.assertEqual(rdata['location'], "exp.xsd")
        self.assertEqual(rdata['description'], '4Rlab')
        self.assertEqual(rdata['version_comment'], 'next')
        self.assertEqual(rdata['version'], 2)
        self.assertTrue(rdata['is_current'])
        
    def test_post(self):
        client = Client()
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        data = json.dumps({'location': filename, 
                           'about': "4R lab", 'content': content})
        res = client.put('/schemas/mylab', content_type='application/json',
                         data=data)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])
        self.assertEqual(rdata['name'], 'mylab')
        self.assertEqual(rdata['location'], filename)
        self.assertEqual(rdata['description'], '4R lab')
        self.assertEqual(rdata['version'], 1)
        self.assertTrue(rdata['is_current'])
        
        filename = "experiments.xsd"
        content = self.get_file_content(filename)
        res = client.post('/schemas/mylab?about=next&location=mylab.xsd',
                         content_type='application/xml', data=content)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])
        self.assertEqual(rdata['name'], 'mylab')
        self.assertEqual(rdata['location'], "mylab.xsd")
        self.assertEqual(rdata['description'], '4R lab')
        self.assertEqual(rdata['version_comment'], 'next')
        self.assertEqual(rdata['version'], 2)
        self.assertFalse(rdata['is_current'])

    def test_patch(self):
        client = Client()
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        data = json.dumps({'location': filename, 
                           'about': "4R lab", 'content': content})
        res = client.put('/schemas/mylab', content_type='application/json',
                         data=data)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])
        self.assertEqual(rdata['description'], '4R lab')

        res = client.patch('/schemas/mylab', content_type='application/json',
                           data=json.dumps({'description': "for your lab"}))
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])
        self.assertEqual(rdata['description'], 'for your lab')

        res = client.patch('/schemas/mylab?description=4Rlab')
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])
        self.assertEqual(rdata['description'], '4Rlab')

    def test_badmethod(self):
        client = Client()
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        data = json.dumps({'location': filename, 
                           'about': "4R lab", 'content': content})
        res = client.put('/schemas/mylab', content_type='application/json',
                         data=data)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])

        res = client.delete('/schemas/mylab')
        self.assertEqual(res.status_code, 405)

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

    def test_get(self):
        client = Client()
        res = client.get('/schemas/mylab/1')
        self.assertEqual(res.status_code, 404)
        
        filename = "mylab.xsd"
        content = self.get_file_content(filename)
        summ = api.loadSchemaDoc(content, "mylab", filename)

        res = client.get('/schemas/mylab/1')
        self.assertEqual(res.status_code, 200)

        data = json.loads(res.content)
        self.assertEqual(data['name'], 'mylab')
        self.assertEqual(data['version'], 1)
        self.assertEqual(data['location'], filename)
        self.assertIn('content', data)
        self.assertIn('<?xml', data['content'])

        res = client.get('/schemas/mylab/1', {'view': 'summary'})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.content)
        self.assertEqual(data['name'], 'mylab')
        self.assertEqual(data['version'], 1)
        self.assertEqual(data['location'], filename)
        self.assertNotIn('content', data)

        res = client.get('/schemas/mylab/1', {'view': 'xml'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('<?xml', res.content)
        self.assertEqual(res['CONTENT-TYPE'], 'application/xml')
        res = client.get('/schemas/mylab/1', {'view': 'xsd'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['CONTENT-TYPE'], 'application/xml')
        self.assertIn('<?xml', res.content)
        
    def test_delete(self):
        client = Client()
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        data = json.dumps({'location': filename, 
                           'about': "4R lab", 'content': content})
        res = client.put('/schemas/mylab', content_type='application/json',
                         data=data)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])
        self.assertEqual(rdata['name'], 'mylab')
        self.assertEqual(rdata['location'], filename)
        self.assertEqual(rdata['description'], '4R lab')
        self.assertEqual(rdata['version'], 1)
        self.assertTrue(rdata['is_current'])
        
        res = client.delete('/schemas/mylab/1')
        self.assertEqual(res.status_code, 200)
        res = client.get('/schemas/mylab?view=versions')
        self.assertEqual(res.status_code, 404)

        res = client.put('/schemas/mylab', content_type='application/json',
                         data=data)
        res = client.get('/schemas/mylab?view=versions')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content, "[1]")

        #pdb.set_trace()
        filename = "experiments.xsd"
        content = self.get_file_content(filename)
        res = client.post('/schemas/mylab', content_type='application/xml',
                          data=content)
        self.assertEqual(res.status_code, 200)
        res = client.get('/schemas/mylab/2')
        self.assertEqual(res.status_code, 200)
        rdata = json.loads(res.content)
        self.assertFalse(rdata['is_current'])
        self.assertFalse(rdata['is_deleted'])
        res = client.get('/schemas/mylab/3')
        self.assertEqual(res.status_code, 404)

        res = client.delete('/schemas/mylab/2')
        self.assertEqual(res.status_code, 200)
        res = client.get('/schemas/mylab?view=versions')
        self.assertEquals(res.content, '[1]')

        res = client.get('/schemas/mylab/2')
        self.assertEqual(res.status_code, 200)
        rdata = json.loads(res.content)
        self.assertFalse(rdata['is_current'])
        self.assertTrue(rdata['is_deleted'])

        res = client.patch('/schemas/mylab/2', data=json.dumps({'undelete': 1}),
                           content_type='application/json')
        self.assertEqual(res.status_code, 200)
        res = client.get('/schemas/mylab/2')
        self.assertEqual(res.status_code, 200)
        rdata = json.loads(res.content)
        self.assertFalse(rdata['is_current'])
        self.assertFalse(rdata['is_deleted'])

    def test_patch_current(self):
        client = Client()
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        data = json.dumps({'location': filename, 
                           'about': "4R lab", 'content': content})
        res = client.put('/schemas/mylab', content_type='application/json',
                         data=data)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])
        self.assertEqual(rdata['name'], 'mylab')
        self.assertEqual(rdata['location'], filename)
        self.assertEqual(rdata['description'], '4R lab')
        self.assertEqual(rdata['version'], 1)
        self.assertTrue(rdata['is_current'])
        
        filename = "experiments.xsd"
        content = self.get_file_content(filename)
        res = client.post('/schemas/mylab', content_type='application/xml',
                          data=content)
        self.assertEqual(res.status_code, 200)
        res = client.get('/schemas/mylab/2')
        self.assertEqual(res.status_code, 200)
        rdata = json.loads(res.content)
        self.assertFalse(rdata['is_current'])
        self.assertFalse(rdata['is_deleted'])

        res = client.patch('/schemas/mylab/2', content_type='application/json',
                           data=json.dumps({'current': 1}))
        self.assertEqual(res.status_code, 200)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['is_current'])
        self.assertFalse(rdata['is_deleted'])
        res = client.get('/schemas/mylab/2')
        self.assertEqual(res.status_code, 200)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['is_current'])
        self.assertFalse(rdata['is_deleted'])
        res = client.get('/schemas/mylab/1')
        self.assertEqual(res.status_code, 200)
        rdata = json.loads(res.content)
        self.assertFalse(rdata['is_current'])
        self.assertFalse(rdata['is_deleted'])

    def test_patch_meta(self):
        client = Client()
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        data = json.dumps({'location': filename, 
                           'about': "4R lab", 'content': content})
        res = client.put('/schemas/mylab', content_type='application/json',
                         data=data)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])
        self.assertEqual(rdata['name'], 'mylab')
        self.assertEqual(rdata['location'], filename)
        self.assertEqual(rdata['version_comment'], 'initial version')
        self.assertEqual(rdata['version'], 1)
        self.assertTrue(rdata['is_current'])

        res = client.patch('/schemas/mylab/1', content_type='application/json',
                           data=json.dumps({'comment': 'first',
                                            'location': 'here'}))
        self.assertEqual(res.status_code, 200)
        rdata = json.loads(res.content)
        self.assertEqual(rdata['location'], 'here')
        self.assertEqual(rdata['version_comment'], 'first')
        self.assertTrue(rdata['is_current'])
        self.assertFalse(rdata['is_deleted'])
        res = client.get('/schemas/mylab/1')
        self.assertEqual(res.status_code, 200)
        rdata = json.loads(res.content)
        self.assertEqual(rdata['location'], 'here')
        self.assertEqual(rdata['version_comment'], 'first')
        
    def test_badmethod(self):
        client = Client()
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        data = json.dumps({'location': filename, 
                           'about': "4R lab", 'content': content})
        res = client.put('/schemas/mylab', content_type='application/json',
                         data=data)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])

        filename = "experiments.xsd"
        content = self.get_file_content(filename)
        data = json.dumps({'location': filename, 'name': "mylab",
                           'description': "4R lab", 'content': content})
        res = client.post('/schemas/mylab/1', content_type='application/json',
                          data=data)
        self.assertEqual(res.status_code, 405)

class TestSchemaComponents(test.TestCase):

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

    def test_list_elements(self):
        client = Client()
        filename = "mylab.xsd"
        content = self.get_file_content(filename)

        data = json.dumps({'location': filename, 
                           'about': "4R lab", 'content': content})
        res = client.put('/schemas/mylab', content_type='application/json',
                         data=data)
        rdata = json.loads(res.content)
        self.assertTrue(rdata['ok'])

        res = client.get('/schemas/mylab/elements')
        self.assertEqual(res.status_code, 200)
        rdata = json.loads(res.content)
        self.assertEqual(len(rdata), 1)
        self.assertEqual(rdata, ['MyLab'])
                
        res = client.get('/schemas/mylab/1/elements')
        self.assertEqual(res.status_code, 200)
        rdata = json.loads(res.content)
        self.assertEqual(len(rdata), 1)
        self.assertEqual(rdata, ['MyLab'])
                
        res = client.get('/schemas/mylab/2/elements')
        self.assertEqual(res.status_code, 404)

def setUpMongo():
    return connect(host=os.environ['MONGO_TESTDB_URL'])

def tearDownMongo(mc):
    try:
        db = mc.get_default_database()
        mc.drop_database(db.name)
    except Exception, ex:
        pass

    
TESTS = "TestAllSchemaDocs".split()

def test_suite():
    suite = test.TestSuite()
    suite.addTests([test.makeSuite(TestLoadSchemaDco)])
    return suite

if __name__ == '__main__':
    test.main()
