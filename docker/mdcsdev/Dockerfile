FROM mdcs_mdcsready
MAINTAINER Ray Plante <raymond.plante@nist.gov>

ENV INITBIN /usr/local/sbin
ENV INITETC /usr/local/etc

COPY deventry.sh $INITBIN
COPY superuser.inputs $INITETC
COPY setsupw.py $INITETC
COPY settings.py $INITETC
COPY mongod_test.conf $INITETC
RUN mkdir /tmp/test_mongo_db
RUN chmod a+x $INITBIN/deventry.sh

ENTRYPOINT ["/usr/local/sbin/deventry.sh"]

