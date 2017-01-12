"""
a module for handling XML Schema-based validation.  A key purpose of this 
module is to draw the schemas used for validation from the database, including 
those pulled in via import/include directives.  It also is meant to encapsulate
the particular validating parser library being used, allowing for multiple 
implementations to be leveraged.   Currently, the default implementation is 
based on lxml.  
"""
import os, sys, abc
from cStringIO import StringIO
from abc import abstractmethod, ABCMeta
from lxml import etree
from collections import OrderedDict

from .models import Schema

XSD_NS = "http://www.w3.org/2001/XMLSchema"

class ValidationError(Exception):
    """
    An indication that the XML is invalid.
    """
    def __init__(self, message, errors=None, docname=None):
        super(ValidationError, self).__init__(message)
        self.document = docname
        if errors is None:
            errors = []
        self.errors = errors

    def addError(self, errmsg):
        """
        add a validation error to this exception
        """
        self.errors.append(errmsg)

class SchemaValidationError(ValidationError):
    """
    An indication that the XML Schema is invalid.
    """
    pass


class _SchemaResolver(etree.Resolver):
    """
    a schema resolver that can resolve import/include schema references
    to previously loaded schemas.

    This implementation with a limitation of lxml in that it will only 
    provide to resolve() the location (system-id) and never namespace 
    (public-id).  
    """
    def __init__(self, includes, imports):
        self.incls = includes.copy()
        self.imps = imports.copy()
        
    def resolve(self, location, namespace, context):
        schema = None
        if namespace is not None and namespace in self.imps:
            # This will never happen with lxml!
            schema = Schema.get_by_name( self.imps[namespace] )
        
        elif location:
            # our schema content will have been modified to insert/change
            # the location to indicate the schema name to be included/imported.
            # In this case, the location with start with "schemaname:", followed
            # by the name of the schema in the database
            if location.startswith(SchemaProvider.CACHE_SCHEME):
                content = SchemaProvider.get(location, self)
                if not content:
                    # should not happen; log a warning?
                    return None
                return self.resolve_string(content, context)

            elif location in self.incls:
                schema = Schema.get_by_name( self.incls[location] )

        if schema:
            return self.resolve_string(schema.content, context)

        return None
            
class SchemaProvider(object):
    """
    a class for providing schema documents to be used for validating.  

    Due to limitations in the lxml library for handling imports as well as 
    our inability to make unique sense of schemaLocation directives, we need
    to provide the validater with doctored versions of schemas:  schemaLocations
    in import and include elements are added/changed to provide a specially 
    formatted form of the schema name being requested.  When this doctored 
    version is parsed, the parser, through our custom resolver, can figure out 
    exactly which of the schemas cached in our database are being requests.  
    """

    CACHE_SCHEME = "schemaname:"

    def __init__(self, includes, imports):
        """
        create the provider.  This constructor is only used directly by the 
        SchemaLoader class, which must validate a schema before it is entered
        into the database.  
        """
        self.incls = includes
        self.imps  = imports
    
    def parse_schema(self, content):
        tree = etree.parse(StringIO(content))
        self.update_includes(tree)
        return tree

    def update_includes(self, tree):

        # short-circuit the docorting if there is nothing to substitute
        if len(self.incls) == 0 and len(self.imps) == 0:
            return 
        
        nsm = {"xs": XSD_NS }
        for imp in tree.getroot().findall("xs:import", nsm): 

            ns = imp.get('namespace')
            if ns is None or ns not in self.imps:
                continue
            schemaname = self.imps[ns]
            imp.set('schemaLocation', self.CACHE_SCHEME+schemaname)

        for incl in tree.getroot().findall("xs:include", nsm):
            loc = incl.get('schemaLocation')
            if not loc or loc not in self.incls:
                continue
            schemaname = self.incls[loc]
            incl.set('schemaLocation', self.CACHE_SCHEME+schemaname)


    def extend_resolver(self, resolver):
        """
        extend the including maps embedded in the given resolver to 
        add new include/import directives.  
        """
        for key in self.incls:
            if key not in resolver.incls:
                resolver.incls[key] = self.incls[key]
            if key not in resolver.imps:
                resolver.imps[key] = self.incls[key]
    
    def transform_schema(self, content):
        # short-circuit the docorting if there is nothing to substitute
        if len(self.incls) == 0 and len(self.imps) == 0:
            return content

        return etree.tostring(self.parse_schema(content))

    @classmethod
    def from_schema(cls, schema, resolver=None):

        if not schema:
            raise ValidationError("Schema with name, {0}, not found"
                                  .format(schemaname))
        includes = cls._strmap_to_dict(schema.includes)
        imports  = cls._strmap_to_dict(schema.imports)
        out = cls(includes, imports)

        if resolver:
            out.extend_resolver(resolver)

        return out

    @classmethod
    def _strmap_to_dict(cls, mapfs):
        return OrderedDict(map(lambda i: i.split('::'), mapfs))

    @classmethod
    def get(cls, schemaname, resolver=None):
        if schemaname.startswith(cls.CACHE_SCHEME):
            schemaname = schemaname[len(cls.CACHE_SCHEME):]
        schema = Schema.get_by_name(schemaname)
        if not schema:
            return None
        return cls.from_schema(schema, resolver).transform_schema(schema.content)

class BaseValidator(object):
    """
    a class for validating both schemas and instance documents.  This class is 
    intended to encapsulate the particular parser used.  

    To validate a schema, it is sufficient to instantiate this class around the
    schema document; resolution of the includes and imports will happen 
    transparently.  

    To validate an instance, pass the XML instance document to validate.  
    """
    __metaclass__ = ABCMeta

    @classmethod
    def from_schema_name(cls, schemaname):
        """
        create a validator for a named schema in the databbase
        """
        schema = Schema.get_by_name(schemaname)
        if not schema:
            raise ValidationError("schema not found: " + schemaname)

        return cls(schema.content, schema.includes, schema.imports)

    @abstractmethod
    def validate(self, inst_content):
        """
        validate that the given instance document is compliant with the 
        configured XML Schema
        """
        return True

    @abstractmethod
    def parse(self, inst_content):
        """
        return a XML-parsed version of the given XML document, raising an 
        exception if it is not well-formed.  
        """
        raise NotImplementedError("BaseValidator.parse()")

class lxmlValidator(BaseValidator):
    """
    a class for validating both schemas and instance documents.  This class is 
    intended to encapsulate the particular parser used.  

    To validate a schema, it is sufficient to instantiate this class around the
    schema document; resolution of the includes and imports will happen 
    transparently.  

    To validate an instance, pass the XML instance document to validate.  
    """

    def __init__(self, schema_content, includes=None, imports=None):
        """
        construct a validator from a given schema

        :param schema_content str: the XML schema document as a string
        :param includes dict:      a dictionary in which each item represents 
                                      an include directive from the given schema
                                      and maps a schema location URL
                                      to a name of a schema already loaded into
                                      the database.
        :param imports  dict:      a dictionary in which each item represents 
                                      an import directive from the given schema
                                      and maps a schema location URL
                                      to a name of a schema already loaded into
                                      the database.
        """
        if includes is None:
            includes = {}
        if imports is None:
            imports = {}

        xp = etree.XMLParser()  # (any options needed?)
        xp.resolvers.add(_SchemaResolver(includes, imports))
        try:
            tree = etree.parse(StringIO(schema_content), parser=xp)
        except etree.XMLSyntaxError, ex:
            raise ValidationError("XML Schema document is not well-formed: " +
                                  ex.message, [ex.message])

        sp = SchemaProvider(includes, imports)
        sp.update_includes(tree)
        
        try:
            self._valid8r = etree.XMLSchema(tree)
        except etree.XMLSchemaError, ex:
            raise SchemaValidationError("XML Schema compliance error: " +
                                        ex.message, [ex.message])

    def validate(self, inst_content):
        """
        validate that the given instance document is compliant with the 
        configured XML Schema
        """
        doc = etree.parse(StringIO(inst_content))
        return self._valid8r.validate(doc)

    @classmethod
    def parse(cls, xmlstr):
        """
        return a XML-parsed version of the given XML document, raising an 
        exception if it is not well-formed.  
        """
        try:
            return etree.parse(StringIO(xmlstr))
        except etree.XMLSyntaxError, ex:
            raise ValidationError("XML is not well-formed: "+ex.message,
                                  [ex.message])

Validator = lxmlValidator
