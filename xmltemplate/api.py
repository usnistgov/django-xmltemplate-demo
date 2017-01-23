"""
This module processes calls to the web API for interacting with templates and 
the schemas they are based on.
"""
import json, logging

from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import authentication, permissions, status
from rest_framework.parsers import JSONParser, BaseParser
from rest_framework.renderers import JSONRenderer, BaseRenderer

from . import models
from .schema import (SchemaLoader, ValidationError, SchemaIngestError,
                     UnresolvedSchemaInclude)

logger = logging.getLogger(__name__)


def loadSchemaDoc(content, name, location=None, about=None,
                  make_current=False, check_digest=False, 
                  loc_finder=None, ns_finder=None):
    """
    load a schema document into the system

    This function returns a dictionary giving the status of the loading and 
    which includes 'ok' and 'message' keys; if 'ok' value is False, an error 
    has occurred, and the 'message' value gives an error message suitable 
    for the end user.

    In the case when this schema imports or includes another schema, it is 
    best when those other schemas are loaded first.  Otherwise, the loader
    will attempt to load it on the fly if it is referred to with a 
    schemaLocation that is a URL or loading will fail.  

    :param content  str:  the text content of the XML Schema document
    :param name     str:  the name to assign to the document
    :param location str:  the URL, file name, or file path to assign as the 
                          schema location for the document; this is used to 
                          connect it to other schemas that might include or 
                          import this one via a schemaLocation attribute.
    :param about    str:  a short explanation for loading this schema document.
                          If this is the first time the schema is loaded, it
                          will be taken as the schema description; otherwise,
                          it will be saved as the version comment.  
    :param make_current bool:  if True, mark this schema as current after 
                          loading
    :param check_digest bool:  if True, compare this schemas digest hash with
                          those already loaded with the given name.  If there
                          is a match, the schema will not be loaded; however,
                          if it in a deleted state, it will be undeleted, and
                          the location field will be updated if it is not None.
    :param loc_finder dict:  a dictionary mapping schemaLocation values to names
                          of schemas already in the system.  If this schema 
                          includes or imports, this dictionary will ensure the 
                          loader properly connects this schema to others already
                          loaded into the system.  (See notes above.)
    :param ns_finder dict:  a dictionary mapping namespace values to names
                          of schemas already in the system.  If this schema 
                          imports, this dictionary will ensure the 
                          loader properly connects this schema to others already
                          loaded into the system.  (See notes above.)
    :return dict:  a dictionary describing the success or failure of the load
                   attempt.  A boolean field 'ok' indicates whether the load 
                   was successful; see notes above for more details.
    """
    out = { "ok": True }
    isupdate = len(models.SchemaVersion.get_all_by_name(name, True)) > 0
    schema = None

    try:
        loader = SchemaLoader(content, name, location)
        if isupdate:
            loader.comment = about
        else:
            loader.description = about

        if loc_finder:
            for loc in loc_finder:
                loader.recognize_location(loc, loc_finder[loc])

        if ns_finder:
            for ns in ns_finder:
                loader.recognize_namespace(ns, ns_finder[ns])

        schema = None
        if check_digest:
            # we're comparing the digest to prevent reloading the same schema
            # because PUT, according to the rules of REST, needs to be indepodent
            sv = models.SchemaVersion.get_by_digest(loader.digest, name)
            if sv:
                # we've already loaded this; undelete it if necessary
                logger.info("posted schema is identical to existing schema; "+
                            "skipping.")
                schema = models.Schema(sv)

                if (location and schema.location != location) or \
                   (about and not schema.deleted and schema.comment != about):

                    if location and schema.location != location:
                        schema.schemaVersion.location = location
                    if about and not schema.deleted and schema.comment != about:
                        schema.schemaVersion.comment = about
                    schema.schemaVersion.save()

                if schema.deleted:
                    schema.undelete()
                    make_current = True
                    if about and schema.description != about:
                        schema._wrapped.description = about
                        schema._wrapped.save()

                out['message'] = \
                    'Schema, {0}, successfully updated'.format(schema.name)

        if not schema:
            if not loader.prepare():
                out['ok'] = False
                out['errors'] = [str(e) for e in loader.errors]
                unresolved = [e for e in loader.errors
                                if isinstance(e, UnresolvedSchemaInclude)]
                if len(unresolved) > 0:
                    # we have some unresolved includes/imports; provide hints
                    
                    out['message'] = \
                        "Failed to load or recognize one or more schema "+\
                        "documents needed for include/import (see hints)"
                    out['hints'] = [
                        "be sure these required schemas "+\
                        "are loaded first and to use the finder parameters as "+\
                        "needed."
                    ]
                    for e in unresolved:
                        if e.candidate:
                            needed = e.namespace or e.location
                            msg = "Possible matches to needed '{0}': {1}" \
                                .format(e.location, ', '.join(e.candidate))
                            msg += "; try using {0} parameter to pick right one"\
                                   .format( (e.namespace and 'ns_finder') or
                                            'loc_finder' )
                            out['hints'].append(msg)

                elif len(loader.errors) == 1:
                    out['message'] = str(loader.errors[0])
                else:
                    out['message'] = \
                        "Multiple issues found loading schema (e.g. {0})". \
                        format(loader.errors[0])
                return out

            schema = loader.load()
            out['message'] = \
                  "Schema document, {0}, successfully loaded".format(schema.name)

    except (ValidationError, SchemaIngestError), ex:
        out['ok'] = False
        out['message'] = "Validation Error: " + ex.message
        out['errors'] = [ ex.message ]

    if schema:
        if make_current:
            schema.make_current()
    
        out.update( SchemaDocVersion.summarize(schema) )
            
    return out
        
class _XSDParser(BaseParser):
    """
    a parser for handling 'application/xml' content-type
    """
    media_type = 'application/xml'

    def parse(self, stream, media_type=None, parser_context=None):
        return stream.read()

class _XSDRenderer(BaseRenderer):
    """
    a renderer for sending a raw XML-XSD file
    """
    media_type = 'application/xml'
    format = '.xsd'
    charset = 'utf-8'

    def render(self, data, media_type=None, renderer_context=None):
        return data.encode(self.charSet)
    

class AllSchemaDocs(APIView):
    """
    an interface to all schema documents currently in the system.  
    """
    parser_classes = (JSONParser, _XSDParser,)

    @classmethod
    def summarize(cls, schema):
        """
        give a summary of a schema in the form of a dictionary of metadata

        :param schema  Schema:  the schema to summarize
        :return dict:  summary data the given schema 
        """
        return {
            'name': schema.name, 'namespace': schema.namespace,
            'current_version': schema.current,
            'version': schema.version, 'location': schema.location,
            'description': schema.desc, 'version_comment': schema.comment
        }

    @classmethod
    def list(cls, view=None):
        """
        list information about all schema documents currently in the system.
        Deleted schemas are not included.

        :param view str:  a label that indicates the particular data to return
                          for each schema document in the listing.
                           'summary' -- the basic information about the schema
                                        as a dictionary, including name, 
                                        namespace, location, current_version,
                                        versions_available, and description.
                           'names'   -- a list containing the unique schema
                                        document names
                           'content' --the raw XSD document
                           'full'    -- same as summary plus a content field 
                                        containing the document.
        """
        out = []
        schemas = models.Schema.get_all_current()
        for schema in schemas:
            if view == 'names':
                out.append(schema.name)
            elif view == 'full':
                data = cls.summarize(schema)
                data['content'] = schema.content
                out.append( data )
            elif view == 'content':
                out.append( schema.content )
            else:
                data = cls.summarize(schema)
                out.append( data )
        return out
            
    @classmethod
    def add(cls, content, name, location=None, description=None,
            loc_finder=None, ns_finder=None):
        """
        add a schema document and give it a particular name.  

        This method uses loadSchemDoc() to do the loading; see its documentation
        for more details on behavior and the output.

        :param content  str:  the text content of the XML Schema document
        :param name     str:  the name to assign to the document
        :param location str:  the URL, file name, or file path to assign as the 
                              schema location for the document; this is used to 
                              connect it to other schemas that might include or 
                              import this one via a schemaLocation attribute.
        :param loc_finder dict:  a dictionary mapping schemaLocation values to 
                              names of schemas already in the system.  If this 
                              schema includes or imports, this dictionary will 
                              ensure the loader properly connects this schema to 
                              others already loaded into the system.  (See notes 
                              above.)
        :param ns_finder dict:  a dictionary mapping namespace values to names
                              of schemas already in the system.  If this schema 
                              imports, this dictionary will ensure the 
                              loader properly connects this schema to others 
                              already loaded into the system.  (See notes above.)
        :return dict:  a dictionary describing the success or failure of the load
                       attempt suitable to return to the user.  
        """
        return loadSchemaDoc(content, name, location, description,
                             loc_finder=loc_finder, ns_finder=ns_finder)
                             

    def get(self, request, format=None):
        """
        handle a GET request to the SchemaDocs web service endpoint.  This 
        returns a listing of currently loaded schema documents by name
        """
        view = request.GET.get('view', 'summary')
        return Response( self.list(view) )

    def post(self, request):
        """
        handle a POST request to the SchemaDocs web service endpoint.  This
        will add an uploaded schema document to the database.
        """
        out = { 'ok', True }
        
        if isinstance(request.DATA, (str, unicode)):
            # raw XML:  the XSD file contents
            data = {
                'content': request.DATA,
                'name': request.GET.get('name'),
                'location': request.GET.get('location'),
                'description': request.GET.get('description')
            }
        elif isinstance(request.DATA, dict):
            # JSON input
            data = request.DATA
        else:
            # Ooops
            out = {
                'ok': False,
                'message': "Unexpected data format ("+type(request.DATA)+")"
            }
            return Response(out, status=status.HTTP_400_BAD_REQUEST)

        missing = [p for p in "content name".split() if p not in data]
        if len(missing) > 0:
            out = {
                "ok": False, "status": status.HTTP_400_BAD_REQUEST,
                "message": "Missing parameters: " + ", ".join(missing)
            }
        elif models.SchemaCommon.get_by_name(data['name']):
            out = {
                "ok": False, "status": status.HTTP_409_CONFLICT,
                "message": "Resource named '{0}' already exists"
                           .format(data['name'])
            }
        else:
            out = self.add( data['content'], data['name'], data.get('location'),
                            data['description'],
                            ns_finder=data.get('ns_finder', {}),
                            loc_finder=data.get('loc_finder', {}) )

        if not out['ok']:
            code = out.get('status', status.HTTP_400_BAD_REQUEST)
            return Response( out, status=code )

        return Response( out )


class SchemaDoc(APIView):
    """
    an interface to a named schema document.  This class 
    responds to the /schemas/<name> endpoint, supporting the 
    following methods:

    :method GET:     returns a view of the current version of the schema.
                     It accepts the query parameter, view, which controls 
                     how much information is returned (see get_view()).  
    :method POST:    creates a new version of the schema without making it 
                     current (see post()).
    :method PUT:     creates a new version of the schema and makes it the 
                     current version (see put()).
    :method PATCH:   allows editing the schema document metadata 
                     (see patch()).
    """

    parser_classes = (JSONParser, _XSDParser,)

    @classmethod
    def summarize(cls, schema):
        """
        give a summary of a schema in the form of a dictionary of metadata

        :param schema   Schema:  the schema to summarize
        """
        out = {
            'name': schema.name, 'namespace': schema.namespace,
            'current_version': schema.current, 'location': schema.location,
            'description': schema.desc, 'version_comment': schema.comment
        }
        out['versions_available'] = cls.versions(schema)
        return out

    @classmethod
    def versions(cls, schema):
        """
        return a list of the version numbers for versions available of the 
        given Schema.
        """
        if not schema:
            return []
        return [sv.version
                for sv in models.SchemaVersion.get_all_by_name(schema.name)]

    @classmethod
    def get_view(cls, name, view='full'):
        """
        return a view of the schema

        :param name str:   the name of the schema document
        :param view str:   a label indicating the form and content ofthe view 
                              of the schema, including:
                           'summary' -- the basic information about the schema
                                        as a dictionary, including name, 
                                        namespace, location, current_version,
                                        versions_available, and description.
                           'versions'-- a list containing the versions available 
                                        for the given 
                           'xml' or 'xsd'--the raw XSD document
                           'full'    -- same as summary plus a content field 
                                        containing the document.
        """
        schema = models.Schema.get_by_name(name)
        if not schema:
            return None

        if view == 'summary':
            return cls.summarize(schema)

        elif view == 'versions':
            return cls.versions(schema)

        elif view == 'xml' or view == 'xsd':
            return schema.content

        else:
            out = cls.summarize(schema)
            out['content'] = schema.content
            return out

    @classmethod
    def add(cls, content, name, location=None, about=None,
            make_current=False, loc_finder=None, ns_finder=None):
        """
        add a new version of the schema with the given name.

        This method uses loadSchemDoc() to do the loading; see its documentation
        for more details on behavior and the output.

        :param content  str:  the text content of the XML Schema document
        :param name     str:  the name to assign to the document
        :param location str:  the URL, file name, or file path to assign as the 
                              schema location for the document; this is used to 
                              connect it to other schemas that might include or 
                              import this one via a schemaLocation attribute.
        :param about    str:  a short explanation for loading this schema 
                              document.  If this is the first time the schema is 
                              loaded, it will be taken as the schema description;
                              otherwise, it will be saved as the version comment.
        :param make_current bool:  if True, mark this schema as current after 
                              loading
        :param loc_finder dict:  a dictionary mapping schemaLocation values to 
                              names of schemas already in the system.  If this 
                              schema includes or imports, this dictionary will 
                              ensure the loader properly connects this schema to 
                              others already loaded into the system.  (See notes 
                              above.)
        :param ns_finder dict:  a dictionary mapping namespace values to names
                              of schemas already in the system.  If this schema 
                              imports, this dictionary will ensure the 
                              loader properly connects this schema to others 
                              already loaded into the system.  (See notes above.)
        :return dict:  a dictionary describing the success or failure of the load
                       attempt suitable to return to the user.  
        """
        return loadSchemaDoc(content, name, location, about,
                             make_current=make_current,
                             check_digest=True, loc_finder=loc_finder,
                             ns_finder=ns_finder)

    @classmethod
    def set_description(cls, name, desc):
        """
        Set the version comment to a given value.
        """
        sc = models.SchemaCommon.get_by_name(name, False)
        if not sc:
            return None
        sc.desc = desc
        sc.save()
        return cls.summarize( models.Schema.get_by_name(name) )

    def get(self, request, name, format=None):
        """
        handle a GET request to the SchemaDocs web service endpoint.  This 
        returns a listing of currently loaded schema documents by name
        """
        view = request.GET.get('view', 'full')

        out = self.get_view(name, view)
        if not out:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        
        if isinstance(out, (str, unicode)):
            return Response( out, content_type='application/xml' )
        return Response( out )

    def _put_post(self, request, name, make_current=False, format=None):
        ns_finder = {}
        loc_finder = {}
        
        if isinstance(request.DATA, (str, unicode)):
            # raw XML:  the XSD file contents
            content = request.DATA
            location = request.GET.get('location')
            desc = request.GET.get('about')
        elif isinstance(request.DATA, dict):
            # JSON input
            content = request.DATA['content']
            location = request.DATA.get('location')
            desc = request.DATA.get('about')
            ns_finder = request.DATA.get('ns_finder', {})
            loc_finder = request.DATA.get('loc_finder', {})
        else:
            # Ooops
            out = {
                'ok': False,
                'message': "Unexpected data format ("+type(request.DATA)+")"
            }
            return Response(out, status=status.HTTP_400_BAD_REQUEST)

        out = self.add(content, name, location, desc, make_current,
                       loc_finder=loc_finder, ns_finder=ns_finder)
        if not out['ok']:
            return Response(out, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(out)

    def put(self, request, name, format=None):
        """
        add a new version of the schema and make it current.
        """
        return self._put_post(request, name, True, format)
        
    def post(self, request, name, format=None):
        """
        add a new version of the schema (without making it current)
        """
        return self._put_post(request, name, False, format)
        
    def patch(self, request, name, format=None):
        """
        handle a PATCH request which is used to update the attributes of the 
        version instance.  
        """
        out = None

        if request.DATA and isinstance(request.DATA, dict):
            data = request.DATA
        else:
            data = request.GET
            
        if not data.get('description'):
            out = {'ok': False, 'status': status.HTTP_400_BAD_REQUEST,
                   'message': 'Missing parameter: description'}
        else:
            out = self.set_description(name, data.get('description'))
            if out and 'ok' not in out:
                out['ok'] = True

        if not out:
            out = {'ok': False, 'status': status.HTTP_404_NOT_FOUND, 
                   'message': "Schema name not found: " + name}

        if not out['ok']:
            return Response( out, status=out['status'] )    

        return Response( out )
    
class SchemaDocVersion(APIView):
    """
    an interface to a version of a named schema document.  This class 
    responds to the /schemas/<name>/<version> endpoint, supporting the 
    following methods:

    :method GET:     returns a view of the schema with the given version.
                     It accepts the query parameter, view, which controls 
                     how much information is returned (see get_view()).  
    :method DELETE:  marks the given version as deleted and returns a JSON
                     summary of the deleted version.
    :method PATCH:   allows editing the schema document version metadata 
                     (see patch()).
    """

    parser_classes = (JSONParser,)
    renderer_classes = (JSONRenderer, _XSDRenderer,)

    @classmethod
    def summarize(cls, schema):
        """
        give a summary of a schema in the form of a dictionary of metadata

        :param schema   Schema:  the schema to summarize
        """
        if not schema:
            return None
        
        out = {
            'name': schema.name, 'namespace': schema.namespace,
            'version': schema.version, 'location': schema.location,
            'description': schema.description, 'version_comment': schema.comment,
            'is_current': schema.iscurrent, 'is_deleted': schema.deleted
        }
        return out

    @classmethod
    def get_view(cls, name, version, view='full'):
        """
        return a view of the schema

        :param name str:    the name of the schema document
        :param verison str: the name of the schema document
        :param view str:    a label indicating the form and content ofthe view 
                               of the schema, including:
                            'summary' -- the basic information about the schema
                                         as a dictionary, including name, 
                                         namespace, location, version,
                                         description, and comment.
                            'xml' or 'xsd'--the raw XSD document
                            'full'    -- same as summary plus a content field 
                                         containing the document.
        """
        schema = models.Schema.get_by_name(name, version, True)
        if not schema:
            return None

        if view == 'summary':
            return cls.summarize(schema)

        elif view == 'xml' or view == 'xsd':
            return schema.content

        else:
            out = cls.summarize(schema)
            out['content'] = schema.content
            return out

    @classmethod
    def make_current(cls, name, version):
        """
        make this version the current one
        """
        schema = models.Schema.get_by_name(name, version)
        if schema:
            schema.make_current()

        return cls.summarize(schema)
        
    @classmethod
    def delete_version(cls, name, version):
        """
        make this version the current one
        """
        schema = models.Schema.get_by_name(name, version)
        if schema:
            schema.delete()

        return cls.summarize(schema)
        
    @classmethod
    def undelete(cls, name, version):
        """
        make this version the current one
        """
        schema = models.Schema.get_by_name(name, version, True)
        if schema:
            schema.undelete()
            return cls.summarize(schema)

        return {
            'ok': False,
            'message': "Schema document named '{0}', version '{1}' not found"
                       .format(name, version)
        }

    @classmethod
    def set_meta(cls, name, version, comment=None, location=None):
        """
        Set the version comment to a given value.
        """
        schema = models.Schema.get_by_name(name, version, False)
        if not schema:
            return None

        if comment or location:
            sv = schema.schemaVersion

            if comment:
                sv.comment = comment
            if location:
                sv.location = location    
            sv.save()

        return cls.summarize( schema )


    def get(self, request, name, version, format=None):
        """
        handle a GET request to the SchemaDocs web service endpoint.  This 
        returns a listing of currently loaded schema documents by name
        """
        view = request.GET.get('view', 'full')
        try:
            version = int(version)
        except ValueError, ex:
            out = {
                'ok': False,
                'message': 'schema not found: {0}/{1}'.format(name, version)
            }
            return Response(out, status=status.HTTP_404_NOT_FOUND)

        out = self.get_view(name, version, view)
        if not out:
            out = {
                'ok': False,
                'message': 'schema not found: {0}/{1}'.format(name, version)
            }
            return Response(out, status=status.HTTP_404_NOT_FOUND)

        if isinstance(out, (str, unicode)):
            return Response( out, content_type='application/xml' )

        return Response( out )

    def delete(self, request, name, version, format=None):
        """
        handle a DELETE request to the SchemaDocs web service endpoint. 
        """
        try:
            version = int(version)
        except ValueError, ex:
            out = {
                'ok': False,
                'message': 'schema not found: {0}/{1}'.format(name, version)
            }
            return Response(out, status=status.HTTP_404_NOT_FOUND)

        out = self.delete_version(name, version)
        if not out:
            out = {
                'ok': False,
                'message': 'schema not found: {0}/{1}'.format(name, version)
            }
            return Response(out, status=status.HTTP_404_NOT_FOUND)

        return Response( out )

    def patch(self, request, name, version, format=None):
        """
        handle a PATCH request which is used to update the attributes of the 
        version instance.  
        """
        out = None
        try:
            version = int(version)
        except ValueError, ex:
            out = {
                'ok': False,
                'message': 'schema not found: {0}/{1}'.format(name, version)
            }
            return Response(out, status=status.HTTP_404_NOT_FOUND)

        if request.DATA and isinstance(request.DATA, dict):
            data = request.DATA
        else:
            data = request.GET
            
        if data.get('undelete'):
            out = self.undelete(name, version)

            if not out:
                out = {
                    'ok': False,
                    'message': 'schema not found: {0}/{1}'.format(name, version)
                }
                return Response(out, status=status.HTTP_404_NOT_FOUND)

        if data.get('current'):
            out = self.make_current(name, version)

        if data.get('comment') or data.get('location'):
            out = self.set_meta(name, version, data.get('comment'),
                                data.get('location'))

        return Response( out )
    
@api_view(['GET'])
def list_elements_in(request, schemaname, version=None):
    """
    return a list of global elements available from a given schema document
    """
    schema = models.Schema.get_by_name(schemaname, version)
    if not schema:
        return Response([], status=status.HTTP_404_NOT_FOUND)

    elements = models.GlobalElement.objects.filter(schemaname=schemaname) \
                                           .filter(version=schema.version)
    out = [e.name for e in elements]
    return Response(out)

