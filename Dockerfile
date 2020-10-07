FROM python:3-alpine

#RUN python -mpip install artifactory-cleanup && rm -rf ~/.cache

ADD . /app
WORKDIR /app
RUN python setup.py install
ENTRYPOINT [ "artifactory-cleanup" ]
CMD [ "--help" ]
