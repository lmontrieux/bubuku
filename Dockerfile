FROM registry.opensource.zalan.do/stups/python:3.5.1-23
MAINTAINER Team Aruha, team-aruha@zalando.de

ENV KAFKA_VERSION="0.9.0.1" SCALA_VERSION="2.11" JOLOKIA_VERSION="1.3.3"
ENV KAFKA_DIR="/opt/kafka"

RUN apt-get update && apt-get install wget openjdk-8-jre -y --force-yes && apt-get clean
ADD download_kafka.sh /tmp/download_kafka.sh

RUN sh /tmp/download_kafka.sh ${SCALA_VERSION} ${KAFKA_VERSION} ${KAFKA_DIR}

ADD server.properties ${KAFKA_DIR}/config/

RUN wget -O /tmp/jolokia-jvm-agent.jar http://search.maven.org/remotecontent?filepath=org/jolokia/jolokia-jvm/$JOLOKIA_VERSION/jolokia-jvm-$JOLOKIA_VERSION-agent.jar

ENV KAFKA_OPTS="-server -Dlog4j.configuration=file:${KAFKA_DIR}/config/log4j.properties -XX:+UseGCLogFileRotation -XX:NumberOfGCLogFiles=10 -XX:GCLogFileSize=32M -javaagent:/tmp/jolokia-jvm-agent.jar=host=0.0.0.0"
ENV KAFKA_JMX_OPTS="-Dcom.sun.management.jmxremote=true -Dcom.sun.management.jmxremote.authenticate=false -Dcom.sun.management.jmxremote.ssl=false"

RUN mkdir -p $KAFKA_DIR/logs/

ENV KAFKA_SETTINGS="${KAFKA_DIR}/config/server.properties"
ADD server.properties ${KAFKA_SETTINGS}
ADD log4j.properties ${KAFKA_DIR}/config/

RUN mkdir /bubuku/
WORKDIR /bubuku/
ADD ./ /bubuku/
RUN pip3 install --no-cache-dir -r requirements.txt

CMD python3 setup.py develop && bubuku