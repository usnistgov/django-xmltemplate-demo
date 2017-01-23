# Running and Testing This Demo With Docker

This directory contains Dockerfiles for building containers with all
necessary dependencies for running and testing this demo.

## Building the Containers

The containers can be built using docker-compose (if you have that
installed); just type while in this directory:

```
  docker-compose -p mdcs up
```

This will build each of the four layered containers.  (It will also
run them; however, they will exit immediately, by default).

If you don't have docker-compose installed, you can build each
container individually and in turn using the usual "docker build"
command:

```
  docker build -t mdcs_pymongodev pymongodev
  docker build -t mdcs_mdcsready  mdcsready
  docker build -t mdcs_mdcsdev    mdcsdev
  docker build -t mdcs_test       test
```

## Running Unit Tests

Once you have the containers built (as instructed above), you can run
the unit tests via the `mdcs_test` container

```
docker run --rm --dns DNSSERVER -v $PWD/..:/mdcs mdcs_test testall
```

where DNSSERVER is a IP name or address for a DNS server that the
container should use.

(The `--dns` option is needed because there one unit test that
attempts to retrieve an XSD document from the internet.)

Alternatively, one can run the `mdcs_test` with an interactive shell
and execute the specific tests repeatedly:

```
docker run --rm -ti --dns DNSSERVER -v $PWD/..:/mdcs mdcs_test startdb bash
```

Then, inside the container's shell, one can run tests as needed, e.g.:

```
python xmltemplate/manage.py test xmltemplate
```
