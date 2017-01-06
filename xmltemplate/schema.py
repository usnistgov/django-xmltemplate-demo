"""
a module that handles the business logic for loading schemas, elements, 
types, and templates
"""
import types, os, hashlib
from urlparse import urlparse
from io import BytesIO
from cStringIO import StringIO

import requests
from lxml import etree

from .models import *

XSD_NS = "http://www.w3.org/2001/XMLSchema"

class SchemaIngestError(Exception):
    """
    An indication that an XML Schema could not be ingested due to some problem
    """
    pass

class FixableErrorsRemain(SchemaIngestError):
    """
    An exception indicating that a user-fixable error condition exists which 
    has not yet been addressed but must be.  

    This would get raised if the errors occur while trying to ingest a schema
    via the API which must be an atomic commit.  The GUI interface can give the 
    user a chance to fix the issues before committing the ingest.  
    """
    def __init__(self, error_list):
        """
        wrap a list of problems represented by exceptions
        :param error_list list:  a list of exceptions describing the errors
        """
        if not hasattr(error_list, '__iter__'):
            error_list = [ error_list ]
        for e in error_list:
            self._ensure_is_exception(e)
            
        self.errors = list(error_list)
        super(FixableErrorsRemain, self).__init__(
            "Errors due to missing schemas prevent loading this schema")

    def _ensure_is_exception(self, error):
        if not hasattr(error, 'message'):
            raise ValueError(
               "Error using FixableErrorsRemain: input item not an Exception: " +
               str(type(error)))
        
    def add_error(self, error):
        self._ensure_is_exception(error)
        self.errors.append(error)
        

class UnresolvedSchemaInclude(SchemaIngestError):
    """
    An indication that an XML Schema could not be ingested because some include
    directives could be not be resolved to schema documents.

    Because the user may have uploaded schemas into the application, the 
    include/import statements location may be ambiguous.  Candidate schemas
    that have already been uploaded and which may possible be a match to the 
    required one can be added to this exception to present as suggests to the 
    user.  
    """
    def __init__(self, location, namespace=None, candidates=None):
        """
        create the error.  If a namespace is provided, it is assumed that 
        this error refers to an import statement.

        :param location  str:   the stated location for the required schema
        :parem namespace str:   the required schema's namespace.  Only set 
                                  this if this error originates from an 
                                  import statement.
        """
        self.location  = location
        self.namespace = namespace
        if candidates is None:
            candidates = []
        self.candidate = candidates

        msg = "Unable to retrive schema in {0} statement from {1}" \
              .format( (self.namespace is None and "include") or "import" )
        super(UnresolvableSchemaInclude, self).__init__(msg)

    def add_possible_match(self, schemaname):
        """
        add the name of a loaded schema document that may be a match to the 
        schema that should be loaded.  
        """
        self.candidate.append( schemaname )

class IncompleteDefinition(SchemaIngestError):
    """
    An base class for incomplete type and element errors
    """
    pass

class IncompleteType(IncompleteDefinition):
    """
    An error indicating that a type cannot be loaded or instantiated because
    one of its ancestor types cannot be found.

    :param thetype    str:        the name of the type that was being loaded
    :param ancestors  list(str):  an ordered list of the QNames of the types 
                                    that thetype is derived from.  The last 
                                    one represents the one whose definition 
                                    cannot be found.  
    """
    def __init__(self, thetype, ancestors=None):
        self.lineage = [ thetype ]
        if not hasattr(ancestors, '__iter__'):
            ancestors = [ ancestors ]
        self.lineage.extend(ancestors)

        msg = "Unable to load type '{0}' because type is incomplete: can't " + \
              "find definition for '{1}'"
        msg = msg.format(self.lineage[0], self.lineage[1])
        super(IncompleteType, self).__init__(msg)

class IncompleteElement(IncompleteDefinition):
    """
    an error indicating that the definition of the type for an element 
    cannot be found.
    """
    def __init__(self, elname, tpname):
        self.elname = elname
        self.tpname = tpname
        msg = "Unable to load element '{0}' because its type '{1}' cannot be " +\
              "found"
        msg = msg.format(self.elname, self.tpname)
        super(IncompleteElement, self).__init__(msg)
        

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

class SchemaLoader(object):
    """
    a class that prepares a schema for ingestion and executes ingestion.  

    Loading a schema is broken into a preparation stage and a commit stage
    which are executed in turn by the load() function.  
    In the preparation stage, the schema is validated and all information 
    that will go into the database is extracted.  The commit stage loads 
    the information into the database.  All errors associated with the 
    schema content are caught in the preparation stage.  

    Some errors arise if the schema invokes other schemas via include or 
    import which haven't been uploaded yet.  All such errors are collected 
    together and stored in the `errors` property.  They will also cause 
    the load() function to throw a FixableErrorsRemain exception; this contains
    a list of individual errors occuring as a result of a missing schema. 

    As part of the preparation, this class will extract the names and derivation
    lineages of all global elements and type in the schema.  
    """

    def __init__(self, schema_content, name, location=None):
        """
        initialize the loader

        :param schema_content str: the XML-encoded schema document as a string
        :param name str:           the name to assign to the schema.
        """
        if not name:
            raise ValueError("SchemaLoader: missing name")
        if not isinstance(schema_content, types.StringTypes):
            raise TypeError("SchemaLoader: schema_content not a string: " +
                             str(schema_content))
        if schema_content == '':
          raise ValidationError("SchemaLoader: schema_content has no content: " +
                                str(schema_content))

        self.content = schema_content
        self.name = name
        self.namespace = None
        self.location = location
        self.tree = None
        self.prefixes = {}
        self.includes = []   # values are Schema names
        self.imports = []    # values are Schema names
        self.global_types = {}
        self.global_elems = {}
        self.errors = []

        self._calchash = _calc_hash_on_string
        self._hash = None

    @property
    def digest(self):
        """
        return the hash digest of the schema content, calculating if needed.
        """
        if not self._hash:
            self._hash = self._calchash(self.content)
        return self._hash

    def prepare(self):
        """
        read the schema, validate it, and read it to prepare for ingestion.

        :return bool:  true if the schema is ready for loading; false if some
                       fixable errors occurred
        :raises ValidationError:  if there is a validation error that has 
                                  occured while validating the schema or any
                                  of its includes or imports.
        :raises SchemaIngestError:  if a fatal error occured while extracting 
                                  needed information from the schema.
        """
        # trigger the digest calculation
        self.digest
            
        # parse the schema and make sure it's valid
        self.validate()

        # find and check the namespace
        self.check_namespace()

        # extract all the top-level prefix definitions
        self.extract_prefixes()

        # handle includes and imports
        self.errors = []
        self.errors.extend( self.resolve_includes() )
        self.errors.extend( self.resolve_imports() )

        # get the names of all global elements and types.  For each type, it 
        # will figure out its ancestors.
        self.errors.extend( self.get_global_defs() )

    def beprepared(self):
        """
        read the schema, validate it, and read it to definitively prepare it
        for ingestion.  This is more severe than prepare() as it will raise
        a SchemaIngestError exception all issues encountered, including fixable 
        ones.  
        """
        self.prepare()

        if not self.name:
            raise SchemaIngestError("schema document requires a name")

        if len(self.errors) > 0:
            raise FixableErrorsRemain(self.errors)

    def load(self):
        """
        load the schema into the system.  This will raise an exception (via 
        beprepared()) if anything goes wrong.
        """
        self.beprepared()

        sc = SchemaCommon.get_by_name(name=self.name) 
        if not sc:
            sc = SchemaCommon(namespace=self.namespace, name=self.name,
                               current=0)
            sc.save()

        sv = SchemaVersion(name=self.name, common=sc, content=self.content, 
                           digest=self.digest, prefixes=self.prefixes, 
                           imports=self.imports, includes=self.includes,
                           location=self.location)
        sv.save()
        if sc.current <= 0:
            sc.current = sv.version
            sc.save()

        for tp in self.global_types:
            gta = GlobalTypeAnnots(name=tp, namespace=self.namespace)
            gta.save()
            gt = GlobalType(name=tp, namespace=self.namespace,
                            schemaname=sc.name, version=sv.version,
                            schema=sv, anscestors=self.global_types[tp],
                            annots=gta)
            gt.save()

        for el in self.global_elems:
            gea = GlobalElementAnnots(name=el, namespace=self.namespace)
            gea.save()
            ge = GlobalElement(name=el, namespace=self.namespace,
                               schemaname=sc.name, version=sv.version,
                               schema=sv, annots=gea)
            ge.save()
                                     
            
                            
    def get_validation_errors(self):
        """
        return an array of the validation errors found in the schema
        """
        errors = []
        try:
            self.validate()
        except ValidationError, ex:
            errors.extend(ex.errors)
        return errors

    def validate(self):
        """
        raise a ValidationError if the document is not valid XML Schema.
        As a side effect, this will set the tree property to the parsed
        version of the schema.  
        """
        self.tree = _xml_parse(self.content)
        _compliant_xml_schema(self.tree)

    def _get_super_type(self, el):
        # find the xs:extension or xs:restrictin element and extract the
        # supertype from the base attribute
        
        nsm = {"xs": XSD_NS }
        base = None
        
        subel = el.find(".//xs:extension", namespaces=nsm)
        if subel is None:
            subel = el.find(".//xs:restriction", namespaces=nsm)
        if subel is not None:
            base = self._resolve_qname( subel.get('base'), subel )

        return base

    def _fmt_qname(self, ns, lname):
        return "{{{0}}}{1}".format(ns,lname)

    def _resolve_qname(self, qname, el, defns=None):
        # convert PREFIX:LNAME to {NS}LNAME
        
        ns = defns
        lname = qname
        if ':' in qname:
            pref, lname = qname.split(':', 1)
            ns = el.nsmap.get(pref)
            if ns is None:
                raise SchemaValidationError("Undefined prefix, used in qname: "+
                                            qname)
        if ns:
            qname = self._fmt_qname(ns, lname)

        return qname

    def _split_qname(self, qname):
        if '}' in qname and qname.startswith('{'):
            return qname.lstrip('{').split('}', 1)
        elif ':' in qname:
            return qname.split(':', 1)
        return ('', qname)

    def _trace_anscestors(self, gllist):
        # gllist:  format: [ (TYPE-NAME, PARENT-QNAME) ]

        def _name_in(name, gllist):
            return name in map(lambda g: g[0], gllist)
        def _first_item_in(name, gllist):
            matches = filter(lambda g: g[0] == name, gllist)
            return ((len(matches) > 0) and matches[0]) or None
        def _circularly_derived(isso):
            if isso:
                msg = "Circular derivation detected: " + parent + \
                      "derives from itself."
                raise SchemaValidationError(msg)

        out = {}
        for tp in gllist:
            if tp[0] in out:
                raise SchemaValidationError("Multiple definitions found for "+
                                            "global type, " + tp[0])
            
            ansc = []
            out[tp[0]] = ansc
            parent = tp[1]
            if parent:
                ansc.append( tp[1] )

            while parent:
                parentns, parentln = self._split_qname(parent)
                includes = None

                if parentns == XSD_NS:
                    # parent is a built-in type; don't go any further
                    parent = None

                elif parentns == self.namespace:
                    # parent is in the same namespace
                    
                    if parentln in out:
                        # parent was defined in this document and we've already
                        # traced its anscestors
                        ansc.extend( out[parentln] )
                        parent = None
                    
                    elif _name_in(parentln, gllist):
                        # parent was defined in this document but we have yet
                        # traced its anscestors
                        _circularly_derived_if(gllist[parentns] in ansc)
                        ansc.append( gllist[parentns] )
                        parent = gllist[parentns]

                    else:
                        # we need search through the included & imported schemas:
                        includes = self.includes + self.imports

                else:
                    includes = self.imports

                if parent:
                    # still haven't found parent
                    if includes:
                        found = None
                        for include in includes:
                            found = self._find_type_in_schemadoc(parent, include)
                            if found:
                                _circularly_derived_if(found[0] in ansc)
                                ansc.extend( found )
                            if found is not None:
                                # None means not found, keep searching includes;
                                # an empty array means found but no more
                                # anscestors
                                parent = None

                if parent:
                    # includes didn't pan out; give up!
                    ansc.append( "__missing__" )
                    parent = None

        return out

    def _find_type_in_schemadoc(self, tpqname, schemaname):
        # This looks for a GlobalType record for a given type QName in the
        # named schema doc and returns its list of anscestors
        
        ns, lname = self._split_qname(tpqname)

        # get schema info from the database
        schema = Schema.get_by_name(schemaname)

        found = GlobalType.objects.filter(schemaname=schema.name) \
                                  .filter(version=schema.version) \
                                  .filter(namespace=ns)           \
                                  .filter(name=lname)
        if len(found) > 0:
            # (there should only be one)
            return found[0].anscestors

        # look through this schema's includes and imports
        for include in (schema.includes + schema.imports):
            found = _find_type_in_schemadoc(tpqname, include)
            if found is not None:
                return found
        return None
        

    def get_global_defs(self):
        """
        extract the names of all global elements and types.
        """
        if not self.tree:
            self.validate()

        def _name_in(name, gllist):
            return name in map(lambda g: g[0], gllist)
        def _first_item_in(name, gllist):
            matches = filter(lambda g: g[0] == name, gllist)
            return ((len(matches) > 0) and matches[0]) or None

        gltps = []
        glels = []
        incomplete = []

        # first collect the global element and type names, extracting typing
        # info
        for el in self.tree.getroot().iterchildren():

            if el.tag == self._fmt_qname(XSD_NS, "element"):
                # Global element
                tp = el.get("type")
                if tp:
                    tp = self._resolve_qname(tp, el, self.namespace)
                glels.append( (el.get("name"),  tp) )
                
            elif el.tag == self._fmt_qname(XSD_NS, "complexType") or \
                 el.tag == self._fmt_qname(XSD_NS, "simpleType"):
                # Global type
                name = el.get('name')
                if not name:
                    line = ""
                    if el.sourceline:
                        line = " at line "+str(el.sourceline)
                    raise SchemaValidationError("Empty or missing name for "+
                                                "global type definition"+line)
                
                parent = self._get_super_type(el) 
                if parent == self._resolve_qname(name, el, self.namespace):
                    raise SchemaValidationError("Global type '"+name+"' derives"+
                                                " from itself!")
                gltps.append( (name, parent) )

        # build the type ancestry lines
        gltps = self._trace_anscestors( gltps )
        self.global_types = dict(
                   filter(lambda t: len(t[1]) == 0 or t[1][-1] != "__missing__",
                          gltps.iteritems()) )
        incomplete.extend( map(lambda t,a: IncompleteType(t, a),
                   filter(lambda t: len(t[1]) > 0 and t[1][-1] == "__missing__",
                          gltps.iteritems())) )

        # Now make sure our global elements are all defined
        self.global_elems = {}
        for elem, tp in glels:
            if elem in self.global_elems:
                raise SchemaValidationError("Multiple definitions found for "+
                                            "global element, " + tp[0])
            elif self._global_type_defined(tp):
                self.global_elems[elem] = tp
            else:
                incomplete.append( IncompleteElement(elem, tp) )

        return incomplete

    def _global_type_defined(self, tpqname):
        ns, ln = self._split_qname(tpqname)
        if ln in self.global_types:
            return True
        matches = GlobalType.objects.filter(namespace=ns).filter(name=ln)
        matches = filter(lambda t: t.version == t.schema.common.current and
                                   not t.schema.deleted, matches)
        return len(matches) > 0

    def check_namespace(self):
        """
        check the schema's namespace.  If the loader was set with a namespace 
        value (which should be the case when loading a new version of a 
        previously loaded schema), it will check that the schema's 
        targetNamespace matches this value; otherwise an exception is thrown.
        If the namespace value was not previously set, it will be set to that
        of the targetNamespace.
        """
        if not self.tree:
            self.validate()
            
        root = self.tree.getroot()
        self.namespace = root.get("targetNamespace")
        if self.namespace is None:
            self.namespace = ""

    def resolve_includes(self):
        """
        examine any include statements and attempt to match them to previously
        loaded schemas.  Otherwise, attempt to load the schemas from their 
        stated location.   Include locations that cannot be resolved are 
        returned as list of UnresolvedSchemaInclude instances.  Each one
        can include a list of possibly matching schema that have already been
        loaded.
        """
        unresolved = []
        if not self.namespace:
            self.check_namespace()
        
        # find any include statements
        nsm = {"xs": XSD_NS }
        for incl in self.tree.getroot().findall("xs:include", nsm):
            
            loc = incl.get('schemaLocation')
            if not loc:
                raise SchemaValidationError("include statement is missing "+
                                            "a schemaLocation: "+incl.tostring())

            # is the location a URL; if so, we can try to load if necessary
            urlloc = urlparse(loc)
            if not urlloc.scheme:
                urlloc = None

            # See if this included schema appears to have been loaded already
            # Look templates in the same namespace and location (or from
            # the no-name namespace).
            matches = Schema.find(location=loc, namespace=self.namespace) + \
                      Schema.find(location=loc, namespace="")
            if len(matches) == 1:
                # we are confident that we have loaded this already
                self.includes.append(matches[0].name)

            elif urlloc:
                # let's load the schema from it's url 
                try:
                    # pull the content and check its hash
                    inclcontent = _retrieve_url_content(loc)
                except Exception, ex:
                    raise SchemaIngestError(
                        "Unable to retrieve schema at URL={0}: {1}".
                        format(urlloc, str(ex)))
                                            
                inclhash = self._calc_hash(inclcontent)

                try:
                    # do we recognize the hash?
                    vers = Schema.find(namespace=self.namespace, digest=inclhash)
                    if len(vers) > 0:
                        self.includes.append(vers[0].name)
                    else:
                        # no, so load it
                        inclschema = SchemaLoader(inclcontent, urlloc,
                                                  location=urlloc)
                        self.includes.append(inclschema.load().name)
                except ValidationError, ex:
                    raise SchemaIngestError(
                        "Included schema at {0} has a validation issues: {1}".
                        format(urlloc, str(ex.errors)))
                    
            else:
                # we only have guesses:
                matches = map(lambda s: s.name, matches)
                error = UnresolvedSchemaInclude(loc, candidates=matches)
                unresolved.append( error )

        return unresolved

    def resolve_imports(self):
        """
        examine any import statements and attempt to match them to previously
        loaded schemas.  Otherwise, attempt to load the schemas from their 
        stated location.   Import namespaces that cannot be resolved are 
        returned as a dict that maps namespaces to stated locations (which will
        be none if not schemaLocation was provided.
        """
        unresolved = []
        if not self.tree:
            self.validate()
        
        # find any include statements
        nsm = {"xs": XSD_NS }
        for incl in self.tree.getroot().findall("xs:import", nsm):

            ns = incl.get('namespace', "")
            loc = incl.get('schemaLocation')
            if not loc and not ns:
                # this is actually legal, according to the spec (though not
                # helpful)
                continue

            # See if we've already loaded it
            matches = Schema.find(namespace=ns, location=loc, current=True)
            if len(matches) == 1:
                self.imports.append(matches[0].name)
                continue

            # Try to load it.
            urlloc = urlparse(loc)
            if not urlloc.scheme:
                matches = map(lambda m: m.name, matches)
                unresolved.append( UnresolvedSchemaInclude(loc, ns, matches) )
            else:
                try:
                    impcontent = _retrieve_url_content(loc)
                except Exception, ex:
                    raise SchemaIngestError(
                        "Failed to retrieve imported schema ({0}) from {1}: {2}".
                        format(ns, loc, str(ex)))

                try:
                    impschema = SchemaLoader(impcontent, name=loc, location=loc)
                    self.imports.append(impschema.load().name)
                except ValidationError, ex:
                    raise ValidationError(
                        "Included schema at {0} has a validation issues: {1}".
                        format(urlloc, str(ex.errors)))
                except FixableErrorsRemain, ex:
                    unresolved.extend( ex.errors )

        return unresolved

    def extract_prefixes(self):
        """
        collect namespace prefix definitions in the schema

        implementation note:  this currently only looks for definitions in the 
        root element.  This should be replaced with a more fully-compliant 
        approach.
        """
        # parse the schema if necessary
        if not self.tree:
            self.validate()

        root = self.tree.getroot()
        self.prefixes.update(root.nsmap)
        for attrib in root.attrib:
            if attrib.startswith("xmlns:"):
                self.prefixes[attrib.split(':', 1)[1]] = root.attrib[attrib]



            

               
def _retrieve_url_content(url):
    if url.startswith("file:"):
        urlp = urlparse(url)
        with open(urlp.path) as fd:
            return fd.read()
    else:
        r = requests.get(url)
        r.raise_for_status()
        return r.text
        

def _xml_parse(xmlstr):
    try:
        return etree.parse(BytesIO(xmlstr))
    except etree.XMLSyntaxError, ex:
        raise ValidationError("XML is not well-formed: "+ex.message,
                              [ex.message])

def _compliant_xml_schema(parsedxml):
    try:
        s = etree.XMLSchema(parsedxml)
    except etree.XMLSchemaError, ex:
        raise SchemaValidationError("XML Schema compliance error: "+ex.message,
                                    [ex.message])

def _calc_hash_on_string(datastr):
    return hashlib.md5(datastr).hexdigest()

    
