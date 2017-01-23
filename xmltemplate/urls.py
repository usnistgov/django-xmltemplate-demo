from django.conf.urls import include, url
from django.contrib import admin
from xmltemplate import api

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^schemas/$', api.AllSchemaDocs.as_view()),
    url(r'^schemas/(?P<name>[^/]+)/?$', api.SchemaDoc.as_view()),
    url(r'^schemas/(?P<name>[^/]+)/(?P<version>\d+)/?$',
        api.SchemaDocVersion.as_view()),
    url(r'^schemas/(?P<schemaname>[^/]+)/elements/?$', api.list_elements_in),
    url(r'^schemas/(?P<schemaname>[^/]+)/(?P<version>\d+)/elements/?$',
        api.list_elements_in)
]
