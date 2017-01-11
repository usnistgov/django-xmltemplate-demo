FROM rayplante/mdcsdev
MAINTAINER Ray Plante <raymond.plante@nist.gov>

ENV PYTHONPATH /mdcs
ENV MONGO_TESTDB_URL mongodb://localhost/xmltemplate

RUN mkdir -p /tmp/mongodb/db
RUN mkdir -p /tmp/mongodb/logs

COPY testentry.sh $INITBIN
RUN chmod a+x $INITBIN/testentry.sh

ENTRYPOINT ["/usr/local/sbin/testentry.sh"]
CMD ["null", "bash"]


