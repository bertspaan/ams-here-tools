# Copyright (C) 2019-2020 HERE Global B.V. and its affiliate(s).
# All rights reserved.
#
# This software and other materials contain proprietary information
# controlled by HERE and are protected by applicable copyright legislation.
# Any use and utilization of this software and other materials and
# disclosure to any third parties is conditional upon having a separate
# agreement with HERE for the access, use, utilization or disclosure of this
# software. In the absence of such agreement, the use of the software is not
# allowed.

# This Dockerfile is used to build docker image for Python SDK.
# Documentation: https://developer.here.com/olp/documentation/sdk-python/dev_guide/topics/docker/home.html

# Base Image
FROM conda/miniconda3-centos7

USER root

ENV HOME /home/here

RUN adduser here -d $HOME && usermod -aG wheel here

RUN chown -R here $HOME

RUN chmod g+s $HOME

RUN chown -R here /usr/local

RUN yum -y install unzip

RUN yum update -y -q

#JAVA
RUN yum -y -q install wget java-1.8.0-openjdk-devel
#OpenSSH
RUN yum -y install openssh
#bind-utils
RUN yum -y install bind-utils

RUN echo "root:root" | chpasswd

WORKDIR $HOME

USER here

RUN mkdir $HOME/.here && chown -R here:here $HOME/.here

RUN mkdir $HOME/.m2 && chown -R here:here $HOME/.m2

#Copy settings and credentials files
COPY --chown=here:here credentials.properties $HOME/.here/credentials.properties
COPY --chown=here:here hls_credentials.properties $HOME/.here/hls_credentials.properties
COPY --chown=here:here settings.xml $HOME/.m2/settings.xml
#Add utility files
COPY --chown=here:here conda-env-files.zip $HOME/conda-env-files.zip
RUN unzip conda-env-files.zip
COPY --chown=here:here sdk_setup.py $HOME/sdk_setup.py
COPY --chown=here:here spark-conf-files.zip $HOME/spark-conf-files.zip

#Steps to install sdk
RUN conda update -n base -c defaults conda

RUN python sdk_setup.py -v

RUN type conda

RUN python sdk_setup.py -i

EXPOSE 8888
#--------------------------------#
#SPARKMAGIC
RUN source activate olp-sdk-for-python-1.5-env\
    && jupyter notebook --generate-config \
    && pip install --upgrade pip \
    && pip install --upgrade --ignore-installed setuptools \
    && pip install sparkmagic==0.12.7 ipyleaflet geomet \
    && jupyter nbextension enable --py widgetsnbextension \
    && jupyter nbextension enable --py --sys-prefix ipyleaflet \
    && jupyter-kernelspec install $(pip show sparkmagic | grep Location | cut -d" " -f2)/sparkmagic/kernels/sparkkernel --user \
    && jupyter-kernelspec install $(pip show sparkmagic | grep Location | cut -d" " -f2)/sparkmagic/kernels/pysparkkernel --user \
    && jupyter-kernelspec install $(pip show sparkmagic | grep Location | cut -d" " -f2)/sparkmagic/kernels/pyspark3kernel --user \
    && jupyter-kernelspec install $(pip show sparkmagic | grep Location | cut -d" " -f2)/sparkmagic/kernels/sparkrkernel --user \
    && jupyter serverextension enable --py sparkmagic \
    && sed -i -e 's/return self._pyspark_command(sql_context_variable_name)/return self._pyspark_command(sql_context_variable_name, False)/g' $(pip show sparkmagic | grep Location | cut -d" " -f2)/sparkmagic/livyclientlib/sqlquery.py \
    && rm -rf $(pip show sparkmagic | grep Location | cut -d" " -f2)/sparkmagic/livyclientlib/sqlquery.py-e \
    && mkdir -p ~/.sparkmagic \
    && chown -R here:here ~/.sparkmagic \
    && unzip spark-conf-files.zip \
    && cd spark-conf-files/ \
    && cp config.json ~/.sparkmagic/config.json \
    && sed -i -e "s|\${HOME}|$HOME|g" ~/.sparkmagic/config.json \
    && rm -rf ~/.sparkmagic/config.json-e

#--------------------------------#
#--------------------------------#
#HADOOP
ENV HADOOP_VERSION 2.7.3
ENV HADOOP_HOME /usr/local/hadoop
ENV HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop
ENV PATH $PATH:$HADOOP_HOME/bin

RUN curl -sL --retry 3 -o /tmp/hadoop-$HADOOP_VERSION.tar.gz \
  "http://archive.apache.org/dist/hadoop/common/hadoop-$HADOOP_VERSION/hadoop-$HADOOP_VERSION.tar.gz" \
  &&  tar -xzf /tmp/hadoop-$HADOOP_VERSION.tar.gz -C /usr/local/ \
  &&  mv /usr/local/hadoop-2.7.3/ /usr/local/hadoop/ \
  && rm -rf /tmp/hadoop-$HADOOP_VERSION.tar.gz \
  && chown -R here:here $HADOOP_HOME

#--------------------------------#
# SPARK
ENV SPARK_VERSION 2.4.0
ENV SPARK_PACKAGE spark-${SPARK_VERSION}-bin-hadoop2.7
ENV SPARK_HOME /usr/local/spark
ENV PATH $PATH:${SPARK_HOME}/bin

RUN curl -sL --retry 3 -o /tmp/$SPARK_PACKAGE \
  "http://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/${SPARK_PACKAGE}.tgz" \
  &&  tar -xf /tmp/$SPARK_PACKAGE -C /usr/local/ \
  && cd /usr/local/ \
  &&  mv /usr/local/$SPARK_PACKAGE/ /usr/local/spark/ \
  && rm -rf /tmp/$SPARK_PACKAGE \
  && chown -R here:here $SPARK_HOME

RUN rm -f $SPARK_HOME/jars/protobuf-java-*.jar

RUN curl -o "/tmp/scala-java8-compat_2.11-0.8.0.jar" \
    "https://repo1.maven.org/maven2/org/scala-lang/modules/scala-java8-compat_2.11/0.8.0/scala-java8-compat_2.11-0.8.0.jar" \
    &&  cp "/tmp/scala-java8-compat_2.11-0.8.0.jar" "/usr/local/spark/jars/"

RUN curl -o "/tmp/json4s-native_2.11-3.5.3.jar" \
    "https://repo1.maven.org/maven2/org/json4s/json4s-native_2.11/3.5.3/json4s-native_2.11-3.5.3.jar" \
    &&  cp "/tmp/json4s-native_2.11-3.5.3.jar" "/usr/local/spark/jars/"

RUN curl -o "/tmp/protobuf-java-3.10.0.jar" \
    "https://repo1.maven.org/maven2/com/google/protobuf/protobuf-java/3.10.0/protobuf-java-3.10.0.jar" \
    &&  cp "/tmp/protobuf-java-3.10.0.jar" "/usr/local/spark/jars/"

RUN conda env list

ENV PYSPARK_PYTHON /usr/local/envs/olp-sdk-for-python-1.5-env/bin/python3
ENV PYSPARK3_PYTHON /usr/local/envs/olp-sdk-for-python-1.5-env/bin/python3

EXPOSE 8998
#--------------------------------#
#LIVY
ENV LIVY_VERSION 0.5.0-incubating
ENV LIVY_BUILD_VERSION livy-$LIVY_VERSION-bin

RUN curl -L --retry 3 -o /tmp/$LIVY_BUILD_VERSION.zip https://www-us.apache.org/dist/incubator/livy/$LIVY_VERSION/$LIVY_BUILD_VERSION.zip \
    && unzip -q /tmp/$LIVY_BUILD_VERSION.zip -d ~/ \
    && mv ~/$LIVY_BUILD_VERSION ~/livy \
    && mkdir -p ~/livy/logs \
    && rm -rf /tmp/$LIVY_BUILD_VERSION.zip \
    && chown -R here:here $HOME/livy

EXPOSE 8998

RUN echo "livy.rsc.server.connect.timeout: 600s" > ~/livy/conf/livy-client.conf \
   && cp ~/livy/conf/log4j.properties.template ~/livy/conf/log4j.properties

#RUN mkdir $HOME/.local
RUN chown -R here:here $HOME/.local
RUN chown -R here:here $HOME/.jupyter

RUN source activate olp-sdk-for-python-1.5-env && emr-init

#Install hmctools
COPY --chown=here:here hmcpkg.zip $HOME/hmcpkg.zip
RUN unzip hmcpkg.zip \
    && source activate olp-sdk-for-python-1.5-env \
    && cd hmcpkg \
    && pip install PyGeodesy \
    && pip install -e .

RUN echo "root:root"

# Create entrypoint shell file
RUN echo "cd olp-sdk-for-python-1.5 && ~/livy/bin/livy-server start && source activate olp-sdk-for-python-1.5-env && jupyter notebook --NotebookApp.token='' --NotebookApp.iopub_data_rate_limit=1000000000 --ip=0.0.0.0 --port=8080" > entrypoint.sh

CMD ["/bin/bash", "entrypoint.sh"]