FROM mdcs_pymongodev
MAINTAINER Ray Plante <raymond.plante@nist.gov>

RUN apt-get install -y net-tools redis-server libxml2-dev libxslt1-dev \
                       wget zlib1g-dev git unzip
RUN easy_install --upgrade pip
RUN pip install Django==1.8.14                          \
                mongoengine==0.10.6                     \
                djangorestframework==2.3.13             \
                django-oauth-toolkit==0.8.0             \
                django-rest-framework-mongoengine==1.3  \
                django-rest-swagger==0.1.14             \
                xlrd==0.9.3      xmltodict==0.10.2      \
                lxml==3.6        python-dateutil==2.2   \
                requests==2.6.0  sickle==0.5            \
                redis==2.10.5    celery==3.1.23         \
                django-password-policies==0.4.1         \
                psutil==4.3.0

RUN (cd tmp && wget -O django-mongoengine-master.zip \
         https://github.com/MongoEngine/django-mongoengine/archive/master.zip &&\
    unzip -q django-mongoengine-master.zip  && cd django-mongoengine-master &&  \
    python setup.py install)
                
ENV INITBIN /usr/local/sbin
ENV INITETC /usr/local/etc

COPY mongod.conf /etc/mongod.conf
COPY create_admin.js create_mgiuser.js $INITETC/
COPY mongo_init_users.sh mongod_ctl.sh initstartentry.sh $INITBIN/
RUN chmod a+x $INITBIN/*
RUN mkdir -p /dev/db

VOLUME /mdcs

ENTRYPOINT ["/usr/local/sbin/initstartentry.sh"]
