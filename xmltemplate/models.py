"""
Models classes for data presisted in the MDCS MongoDB supporting XML-based
curation templates.
"""

from django_mongoengine import fields, Document
from django.db.models import Max

class SchemaCommon(Document):
    """
    Storage model for schema metadata that is common to all its versions.

    A schema, in this model, a document that has a both name and a namespace;
    There can exist several versions of the document, but only one can be 
    considered in use at a time.  This model captures metadata about the 
    schema that is considered common to all versions of the schema.

    The name serves as the primary key of the SchemaCommon record: it must be 
    unique.  It appears as a foreign key in the SchemaVersion records.

    :property name str:       an optional name for the schema; used for display
                              purposes; must be unique.
    :property namespace str:  the URI of the schema's target namespace.  If the
                              schema does not define a namespace, as 
                              pseudo-namespace should be assigned with the 
                              scheme, "nons"; must be unique.
    :property current int:    the version number of the schema that should be
                                 considered the current one.
    :property desc str:       a brief (displayable) description of the schema.  
    """
    name      = fields.StringField(unique=True)
    namespace = fields.StringField(blank=False)
    current   = fields.IntField(blank=False)
    desc      = fields.StringField(default="")

    @classmethod
    def get_by_name(self, name, allowdeleted=False):
        """
        Return the SchemaCommon record having the given name (which 
        must be unique).

        :param name str:           the user-given name for the schema to look up
        :param allowdeleted bool:  if true, include records where current <= 0
        """
        out = SchemaCommon.objects.filter(name=name)
        if not allowdeleted:
            out = out.filter(current__gt=0)
        if len(out) > 0:
            return out[0]
        return None

    @classmethod
    def get_all_by_namespace(self, namespace, allowdeleted=False):
        """
        Return the set of SchemaCommon records that having the given namespace.

        :param namespace str:      the namespace URL to look up
        :param allowdeleted bool:  if true, include records where current <= 0
        """
        out = SchemaCommon.objects.filter(namespace=namespace)
        if not allowdeleted:
            out = out.filter(current__gt=0)
        return out
        
    def get_current_version(self):
        """
        return the SchemaVersion record that corresponds to the current 
        instance of this schema.  None is returned if there is no version
        currently marked as current.
        """
        return SchemaVersion.get_by_version(self.name, self.current)
        
    @classmethod
    def get_namespaces(self):
        """
        return a list of all namespaces currently registered
        """
        out = set()
        for sc in SchemaCommon.objects.all():
            out.add(sc.namespace)
        return list(out)
    

    @classmethod
    def get_names(self):
        """
        return a list of all user-provided names currently registered
        """
        return map(lambda s: s.name, SchemaCommon.objects.all())

class RecordStatus(object):
    status_words = [ "deleted", "available", "current" ]
    DELETED = 0
    AVAILABLE = 1
    IS_CURRENT = 2
    def __init__(self, statusno):
        if not isinstance(statusno, int):
          raise TypeError("RecordStatus(): input not an integer")
        if statusno not in range(3):
          raise ValueError("RecordStatus(): status integer out of range [0:3]: "
                           + statusno)
        self.val = statusno

    @property
    def status(self):
        return self.status_words[statusno]
RECORD = RecordStatus
    
class SchemaVersion(Document):
    """
    Storage model for a version of a schema.  

    :property name str:       the user-provided name for the schema document
    :property version seq:    a version number, where higher numbers represent
                              more recent versions.  
    :property common ref:   a reference to the schema's common information
                              record in the Schema collection.
    :property location str:   a location for the schema (as a URL or filename)
    :property content str:    the XML document defining the schema
    :property digest str:     the hash digest of the content value
    :property prefixes dict:  a mapping of prefixes to namespaces
    :property includes list:  a list of names for schemas that 
                              should be included as part of this one.  Each
                              value corresponds to a SchemaCommon record
                              with this name.
    :property imports list:   a list of names of schemas that 
                              should be imported into this one.  Each
                              value corresponds to a SchemaCommon record
                              with this name.
    :property status int:     integer indicating whether record is deleted (0),
                              current (2), or otherwise (1)
    :property comment str:    A brief (displayable) comment noting what is 
                              different about this version.
    """
    name      = fields.StringField(unique_with=['version'], required=True)
    version   = fields.IntField(unique_with=['name'], required=True)
    common    = fields.ReferenceField(SchemaCommon)
    location  = fields.StringField(blank=True)
    content   = fields.StringField(blank=False)
    digest    = fields.StringField(blank=False)
    prefixes  = fields.DictField(default={}, blank=True)
    includes  = fields.ListField(fields.StringField(), default=[], blank=True)
    imports   = fields.ListField(fields.StringField(), default=[], blank=True)
    status    = fields.IntField(blank=False, default=1)
    comment   = fields.StringField(default="")

    @classmethod
    def get_all_by_name(cls, name, include_deleted=False):
        """
        return a list of SchemaVersion records that have given name

        :param name str:  the name of the schema to match
        :param include_deleted bool:  if False, return only records that 
                          have not been marked as deleted.
        """
        vers = SchemaVersion.objects.filter(name=name)
        if not include_deleted:
            vers = vers.filter(status__ne=RECORD.DELETED)
        return vers

    @classmethod
    def get_by_version(cls, name, version, include_deleted=False):
        """
        return the SchemaVersion record with a given name and version.

        :param name    str:   the name of the schema to match
        :param version int:   the version of the schema to select
        :param include_deleted bool:  if False, return only records that 
                          have not been marked as deleted.
        
        """
        vers = cls.get_all_by_name(name, include_deleted).filter(version=version)
        if len(vers) > 0:
            return vers[0]
        return None

    @classmethod
    def get_all_current(self):
        """
        return all SchemaVersion records that are currently set as current
        """
        return SchemaVersion.objects.filter(status=RECORD.IS_CURRENT)

    @classmethod
    def next_version_for(self, name):
        try: 
            return max(map(lambda v: v.version,
                           SchemaVersion.objects.filter(name=name))) + 1
        except ValueError, ex:
            # none found with this name
            return 1
        

class Schema(object):
    """
    A representation of a version of a Schema.  

    This is a convenience wrapper around a SchemaVersion instance.  Its 
    properies are the same as SchemaVersion (except common) but also adds 
    the schema's namespace and the number of the current version.

    This class only supports schemas that are already loaded into 
    the database.  That is, one should use the the class methods, e.g. 
    get_by_name(), to select a desired, existing schema.  It does not 
    create new Schema instances (use SchemaLoader for that).  
    """
    _ver_props = ("name version location content digest prefixes "+
                  "includes imports status comment").split()
    _comm_props = "namespace current desc"

    def __init__(self, schemaVersion):
        """
        wrap a SchemaVersion instance
        """
        self._wrapped = schemaVersion

    def __getattribute__(self, name):
        if name == 'description':  name = "desc"
        if name in Schema._ver_props:
            return getattr(self._wrapped, name)
        elif name in Schema._comm_props:
            return getattr(self._wrapped.common, name)
        else:
            return object.__getattribute__(self, name)

    @property
    def schemaVersion(self):
        return self._wrapped

    @property
    def deleted(self):
        return self.status == RECORD.DELETED

    @property
    def iscurrent(self):
        return self.status == RECORD.IS_CURRENT

    @property
    def schemaCommon(self):
        return self._wrapped.common

    def make_current(self):
        """
        make this version the current one.  If this version is marked deleted,
        a RuntimeError is raised.
        """
        if self.current != self.version:
            if self.deleted:
                raise RuntimeError("Not allowed to make deleted schema current")
            self._wrapped.status = RECORD.IS_CURRENT
            self._wrapped.common.current = self.version
            self._wrapped.save()

            oldcurr = Schema.get_by_name(self.name)
            try:
                self._wrapped.common.save()
            except:
                # log inconsistent state
                raise
            finally:
                if oldcurr:
                    oldcurr._wrapped.status = RECORD.AVAILABLE
                    oldcurr._wrapped.save()

    def delete(self):
        """
        delete this version of the schema
        """
        if self.status == RECORD.IS_CURRENT:
            # make a different version current
            available = SchemaVersion.objects.filter(name=self.name) \
                                             .filter(status=RECORD.AVAILABLE) 

            # find the latest undeleted version 
            maxverno = 0
            maxver = None
            for sv in available:
                if sv.version > maxverno:
                    maxverno = self.version
                    maxver = sv
            if maxver:
                # log that we're changing the current version
                Schema(maxver).make_current()
            else:
                # log that we're deleting the only current version
                pass

        self._wrapped.status = RECORD.DELETED
        self._wrapped.save()

    def undelete(self):
        """
        undelete this version of the schema, making it available to be made
        current.
        """
        if self.status == RECORD.DELETED:
            self._wrapped.status = RECORD.AVAILABLE
            self._wrapped.save()

    def find_including_schema_names(self):
        """
        return the names of the schemas that include this schema, either 
        directly or indirectly.
        """
        includers = []
        _find_includers(self.name, includers)
        return includers

    def find_importing_schema_names(self):
        """
        return the names of the schemas that include this schema, either 
        directly or indirectly.
        """
        importers = []
        _find_importers(self.name, importers)
        return importers

    @classmethod
    def find(cls, **kwds):
        """
        return an array of Schema objects that match the given keywords.

        :param namespace  str:  the namespace URI to match
        :param version    int:  the version number to match
        :param name       str:  the user-given schema name to match
        :param location   str:  the recorded schema location to match
        :param digest     str:  the schema content digest to match
        :param deleted   bool:  whether the schema is marked as deleted
        :param current   bool:  if true, select only schemas marked as current
        """
        versions = SchemaVersion.objects.all()
        for keywd in kwds:
            if keywd in cls._ver_props or keywd in ['deleted', 'current']:
                if keywd == 'deleted':
                    op = (not kwds['deleted'] and "__ne") or ""
                    use = { 'status'+op: RECORD.DELETED }
                elif keywd == 'current':
                    op = (not kwds['current'] and "__ne") or ""
                    use = { 'status'+op: RECORD.IS_CURRENT }
                else:
                    use = { keywd: kwds[keywd] }
                versions = versions.filter(**use)
        ided = []
        for ver in versions:
            if 'name' in kwds and ver.common.name != kwds['name']:
                continue
            if 'namespace' in kwds and ver.common.namespace != kwds['namespace']:
                continue
            if 'current' in kwds:
                iscurrent = ver.common.current == ver.version
                if kwds['current'] != iscurrent:
                    continue
            ided.append(ver)

        out = []
        for ver in ided:
            out.append(Schema(ver))

        return out

    @classmethod
    def _find_one(cls, **kwds):
        found = cls.find(**kwds)
        if len(found) > 0:
            return found[0]
        return None

    @classmethod
    def get_all_by_namespace(cls, namespace, allowdeleted=False):
        """
        return a list of all the Schemas with the given namespace.  

        :param namespace str:  the namespace to match
        :param allowdeleted bool:  if False, only return a Schema marked as 
                               undeleted
        """
        scs = SchemaCommon.get_all_by_namespace(namespace, allowdeleted)
        if not scs:
            return []

        out = []
        for sc in scs:
            sv = SchemaVersion.get_by_version(sc.name, sc.current)
            if not sv or (not allowdeleted and sv.status == RECORD.DELETED):
                continue
            out.append( Schema(sv) )

        return out
                
    @classmethod
    def get_by_name(cls, name, version=None, allowdeleted=False):
        """
        return the Schema with the given user-provided name

        :param name    str:    the namespace to match
        :param version int:    the version to get; if None, the current is 
                                 returned
        :param allowdeleted bool:  if False, only return a Schema marked as 
                               undeleted 
        """
        cs = SchemaCommon.get_by_name(name)
        if not cs:
            return None

        vers = SchemaVersion.objects.filter(name=cs.name)
        
        if cs.current <= 0:
            if not allowdeleted:
                return None
            vers = vers.aggregate(Max('version'))
        else:
            if version is None:
                version = cs.current
            vers = vers.filter(version=version) 

        if not allowdeleted:
            vers = vers.filter(status__ne=RECORD.DELETED)
        if len(vers) == 0:
            return None
        return Schema(vers[0])

    @classmethod
    def get_namespaces(self):
        return SchemaCommon.get_namespaces()
    
    @classmethod
    def get_names(self):
        return SchemaCommon.get_names()

def _find_includers(name, found):
    # add to found the names of schemas that include the named schema
    # :param name   str:  the unique name of the schema to find includers for
    # :param found list:  a list of schema names that should be considered to
    #                      to be already found
    assert isinstance(found, list)

    svs = SchemaVersion.get_all_current().filter(includes=name)
    for sv in svs:
        if sv.name in found:
            continue
        found.append(sv.name)
        _find_includers(sv.name, found)

def _find_importers(name, found):
    # add to found the names of schemas that include the named schema
    # :param name   str:  the unique name of the schema to find includers for
    # :param found list:  a list of schema names that should be considered to
    #                      to be already found
    assert isinstance(found, list)

    svs = SchemaVersion.get_all_current().filter(imports=name)
    for sv in svs:
        if sv.name in found:
            continue
        found.append(sv.name)
        _find_importers(sv.name, found)

    
class GlobalElementAnnots(Document):
    """
    Storage model for annotations on a global element.  The purpose of this 
    model separate from GlobalElement is so that these annotations can be 
    shared across the different versions of the element (from the different
    versions of the schema); in other words, when a new version of a schema
    is loaded, you don't loose all your annotations.

    :property name       str: the local name for the element
    :property namespace  str: the namespace URI of the schema within which the 
                              element is defined
    :property tag       list: a list of strings representing subject tags
    :property hide   boolean: True if this element should be normally hidden
                              when offering root elements for templates.
    """
    name      = fields.StringField(unique_with=["namespace"])
    namespace = fields.StringField()
    tag       = fields.ListField(fields.StringField(), default=[], blank=True)
    hide      = fields.BooleanField(default=False)


class GlobalElement(Document):
    """
    Storage model for a globally defined element within a schema document.  
    Such an element can be used as the root element of a document.

    :property name       str: the local name for the element
    :property namespace  str: the namespace URI of the schema within which the 
                              element is defined
    :property schemaname str: the unique name given to the schema document where 
                              the element is defined
    :property version    int: the version of the schema document that this 
                              element is defined in
    :property schema     ref: a reference to the SchemaVersion record where 
                              this version of the element is defined
    :property annots     ref: a reference to the GlobalElementAnnots that 
                              contains user annotations.  
    """
    name      = fields.StringField(unique_with=["namespace",
                                                "schemaname", "version"])
    namespace = fields.StringField()
    schemaname= fields.StringField()
    version   = fields.IntField()
    schema    = fields.ReferenceField(SchemaVersion)
    annots    = fields.ReferenceField(GlobalElementAnnots)

    @classmethod
    def get_all_elements(cls):
        """
        return all of the global elements from all the representative 
        namespaces that aren't marked as hidden.  

        :return dict:  a dictionary that has namespaces as keys and 
                       GlobalElement records as values.
        """
        currents = {}
        scs = SchemaCommon.objects.filter(current__gt=0)
        for sc in scs:
            sv = SchemaVersion.get_by_version(sc.name, sc.current)
            if sv:
                currents[sc.name] = sc.current

        elsbyns = {}
        for name in currents:
            glels = GlobalElement.objects.filter(schemaname=name)        \
                                         .filter(version=currents[name]) 
            for el in glels:
                if el.annots.hide:
                    continue
                if el.namespace not in elsbyns:
                    elsbyns[el.namespace] = []
                elsbyns.append(el)

        return elsbysnd

class GlobalTypeAnnots(Document):
    """
    Storage model for annotations on a global element.  The purpose of this 
    model separate from GlobalType is so that these annotations can be 
    shared across the different versions of the type (from the different
    versions of the schema); in other words, when a new version of a schema
    is loaded, you don't loose all your annotations.

    :property name       str: the local name for the element
    :property namespace  str: the namespace URI of the schema within which the 
                              element is defined
    :property tag       list: a list of strings representing subject tags
    :property hide   boolean: True if this element should be normally hidden
                              when offering root elements for templates.
    """
    name = fields.StringField()
    namespace = fields.StringField()
    tag = fields.ListField(fields.StringField(), default=[], blank=True)
    hide = fields.BooleanField(default=False)

class GlobalType(Document):
    """
    Storage model for a globally defined type within a schema.  

    :property name str:       the local name for the type
    :property namespace str:  the namespace URI of the schema where the type
                              is defined
    :property schemaname str: the unique name given to the schema document where 
                              the type is defined
    :property version    int: the version of the schema document that this 
                              type is defined in
    :property schema     ref: a reference to the SchemaVersion record where 
                              this version of the type is defined
    :property anscestors list:  an ordered list of the anscestor types of this
                              type.  The first type is the immediate super-type.
                              Each type name is in "{NS}NAME" format.
    :property annots     ref: a reference to the GlobalElementAnnots that 
                              contains user annotations.  
    """
    name      = fields.StringField()
    namespace = fields.StringField()
    schemaname= fields.StringField()
    version   = fields.IntField()
    schema    = fields.ReferenceField(SchemaVersion)
    anscestors= fields.ListField(fields.StringField(), default=[], blank=True)
    annots    = fields.ReferenceField(GlobalTypeAnnots)

    @classmethod
    def get_all_types(cls):
        """
        return all of the global types from all the representative 
        namespaces that aren't marked as hidden.  

        :return dict:  a dictionary that has namespaces as keys and 
                       GlobalType records as values.
        """
        currents = {}
        scs = SchemaCommon.objects.filter(current__gt=0)
        for sc in scs:
            sv = SchemaVersion.get_by_version(sc.name, sc.current)
            if sv:
                currents[sc.name] = sc.current

        tpsbyns = {}
        for name in currents:
            gltps = GlobalType.objects.filter(schemaname=name)        \
                                      .filter(version=currents[name]) 
            for tp in glels:
                if tp.annots.hide:
                    continue
                if tp.namespace not in tpsbyns:
                    tpsbyns[tp.namespace] = []
                elsbyns.append(tp)

        return elsbysnd



class TypeRenderSpec(Document):
    """
    Storage model that specifies how to render the form for a particular 
    XML type.  

    :property byelem dict:    a mapping of elements and attribute names to 
                              NodeRenderSpec references for the type's contents;
                              any elements not reference will have specs 
                              generated dynamically.
    :property rendmod str:    The class that should be used to render this type; 
                              if provided, it will be instantiated passing the 
                              config data, a label, and the byelem dictionary.  
    :property config dict:    a mapping of arbitrary string fields to data
                              values that should be used to configure the module
                              (ignored if module is not set).  
    """
    byelem = fields.DictField(default=dict)
    rendmod = fields.StringField()
    config = fields.DictField(default=dict)

class NodeRenderSpec(Document):
    """
    Storage model that specifying how to render an XML element or node which
    combines a label with a TypeRenderSpec

    :property label str:      the label to associate with the rendering of the 
                              type.
    :property spec  ref:      the TypeRenderSpec to use for rendering the node's
                              type; if not set, this will be generated 
                              dynamically.
    """
    label = fields.StringField()
    spec  = fields.ReferenceField(TypeRenderSpec)


class TemplateCommon(Document):
    """
    Storage model for a document curation template.  This captures 

    :property name str:       a unique name
    :property current int:    the version number of the schema that should be
                                 considered the current one.
    :property root str:       a namespace-qualified element name (in the form
                                 "{NAMESPACE}ELNAME") for the root element of
                                 conforming instance documents.
    :property desc str:       a brief (displayable) description of the template.
    """
    name    = fields.StringField(unique=True)
    current = fields.IntField(blank=False)
    root    = fields.StringField(blank=False)
    desc    = fields.StringField(default="")

    @classmethod
    def get_by_name(self, name, allowdeleted=False):
        """
        Return the TemplateCommon record having the given name (which 
        must be unique).

        :param name str:           the user-given name for the schema to look up
        :param allowdeleted bool:  if true, include records where current <= 0
        """
        out = TemplateCommon.objects.filter(name=name)
        if not allowdeleted:
            out = out.filter(current__gt=0)
        if len(out) > 0:
            return out[0]

    def get_current_version(self):
        """
        return the TemplateVersion record that corresponds to the current 
        instance of this schema.  None is returned if there is no version
        currently marked as current.
        """
        return TemplateVersion.get_by_version(self.name, self.current)
        
    @classmethod
    def get_names(self):
        """
        return a list of all user-provided names currently registered
        """
        return map(lambda s: s.name, SchemaCommon.objects.all())

        
class TemplateVersion(Document):
    """
    Storage model for storing different versions of a template.

    :property name str:       the template name being versioned
    :property version seq:    the version for this template
    :property common ref:   a reference to the common information record 
                                in the Template collection
    :property label str:      the label to give to the root element
    :property spec  ref:      the TypeRenderSpec object to use to render the 
                              root element; if not set, this will be generated 
                              dynamically.
    :property comment str:    A brief (displayable) comment noting what is 
                              different about this version.
    """
    name    = fields.StringField(blank=False)
    version = fields.SequenceField(blank=False)
    common  = fields.ReferenceField(TemplateCommon, blank=False)
    schema  = fields.ReferenceField(SchemaVersion, blank=False)
    extschemas = fields.ListField(SchemaVersion, blank=True, default=[])
    label   = fields.StringField()
    spec    = fields.ReferenceField(TypeRenderSpec, blank=True)
    deleted = fields.BooleanField(blank=False, default=False)
    comment = fields.StringField(default="")

    @classmethod
    def get_all_by_name(cls, name, include_deleted=False):
        """
        return a list of TemplateVersion records that have given name

        :param name str:  the name of the template to match
        :param include_deleted bool:  if False, return only records that 
                          have not been marked as deleted.
        """
        vers = TemplateVersion.objects.filter(name=name)
        if not include_deleted:
            vers = vers.filter(deleted=False)
        return vers

    @classmethod
    def get_by_version(cls, name, version, include_deleted=False):
        """
        return the TemplateVersion record with a given name and version.

        :param name    str:   the name of the schema to match
        :param version int:   the version of the schema to select
        :param include_deleted bool:  if False, return only records that 
                          have not been marked as deleted.
        
        """
        vers = cls.get_all_by_name(name, include_deleted).filter(version=version)
        if len(vers) > 0:
            return vers[0]
        return None

    

class Template(object):
    """
    A representation of version of a Template.  

    This is a convenience wrapper around a TemplateVersion instance.  Its 
    properies are the same as TemplateVersion (except common) but also adds 
    the root property, representing the root element of the template.

    This class is only supported for templates that are already loaded into 
    the database.  The class methods can be used for selecting desired templates.
    """

    _data_dir = "name version schema label spec deleted".split()

    def __init__(self, templateVersion):
        """
        wrap a TemplateVersion instance
        """
        self._wrapped = templateVersion

    def __getattribute__(self, name):
        if name in Template._data_dir:
            return getattr(self._wrapped, name)
        else:
            return object.__getattribute__(self, name)

    @property
    def root(self):
        return self._wrapped.common.root

    @property
    def current(self):
        return self._wrapped.common.current

    @classmethod
    def find(cls, **kwds):
        """
        return an array of Template objects that match the given keywords.

        :param name      str:  the user-given template name to match
        :param version   int:  the version number to match
        :param common  str:  
        :param schema    str:  the recorded template location to match
        :param label     str:  the template content digest to match
        :param spec     bool:  whether the template is marked as deleted
        :param deleted  bool:  if true, select only templates marked as current
        """
        versions = TemplateVersion.objects
        for keywd in kwds:
            if keywd in cls._data_dir:
                use = { keywd: kwds[keywd] }
                versions = versions.filter(**use)
        ided = []
        for ver in versions:
            if 'root' in kwds and ver.common.root != kwds['root']:
                continue
            if 'current' in kwds:
                iscurrent = ver.common.current == ver.version
                if kwds['current'] != iscurrent:
                    continue
            ided.append(ver)

        out = []
        for ver in ided:
            out.append(Template(ver))

        return out

    @classmethod
    def _find_one(cls, **kwds):
        found = cls.find(**kwds)
        if len(found) > 0:
            return found[0]
        return None

    @classmethod
    def get_by_name(cls, name, version=None, allowdeleted=False):
        """
        return the Template with the given namespace

        :param name    str:    the name to match
        :param version int:    the version to get; if None, the current is 
                                 returned
        :param allowdeleted bool:  if False, only return a Template marked as 
                               undeleted
        """
        tc = TemplateCommon.get_by_name(name)
        if not tc:
            return None

        vers = TemplateVersion.objects.filter(name=tc.name)
        
        if tc.current <= 0:
            if not allowdeleted:
                return None
            vers = vers.aggregate(Max('version'))
        else:
            if version is None:
                version = tc.current
            vers = vers.filter(version=version) 

        if not allowdeleted:
            vers = vers.filter(deleted=False)
        if len(vers) == 0:
            return None
        return Template(vers[0])

    @classmethod
    def get_names(self):
        return TemplateCommon.get_names()
    
