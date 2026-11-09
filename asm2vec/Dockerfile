#####################################
# RCP CaaS requirement (Image)
#####################################
# The best practice is to use an image
# with GPU support pre-built by Nvidia.
# https://catalog.ngc.nvidia.com/orgs/nvidia/containers/

# For example, if you want to use an image with pytorch already installed
# FROM --platform=linux/amd64 nvcr.io/nvidia/pytorch:24.10-py3
FROM ubuntu:focal
#####################################
# RCP CaaS requirement (Storage)
#####################################
# Create your user inside the container.
# This block is needed to correctly map
# your EPFL user id inside the container.
# Without this mapping, you are not able
# to access files from the external storage.
ARG LDAP_USERNAME
ARG LDAP_UID
ARG LDAP_GROUPNAME
ARG LDAP_GID
RUN groupadd ${LDAP_GROUPNAME} --gid ${LDAP_GID}
RUN useradd -m -s /bin/bash -g ${LDAP_GROUPNAME} -u ${LDAP_UID} ${LDAP_USERNAME}
#####################################

RUN mkdir /home/${LDAP_USERNAME}/.idapro
COPY ida.reg /home/${LDAP_USERNAME}/.idapro/
COPY idapro-9.0 /opt/idapro-9.0/
ENV IDA_PATH=/opt/idapro-9.0/idat64

# Set your user as owner of the new copied files
RUN chown -R ${LDAP_USERNAME}:${LDAP_GROUPNAME} /home/${LDAP_USERNAME}

# Install required packages
RUN apt update && apt install python3-pip git wget python3-venv parallel -y 

RUN usermod -aG sudo ${LDAP_USERNAME}
WORKDIR /home/${LDAP_USERNAME}

# dependencies
COPY requirements.txt /home/${LDAP_USERNAME}/requirements.txt
RUN pip install -r /home/${LDAP_USERNAME}/requirements.txt
RUN apt-get install -y curl python2 && curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py && \
	python2 get-pip.py && \
	pip2 install capstone==3.0.4
RUN pip3 install click
RUN python3 -m pip install capstone
# gensim
COPY asm2vec.patch /home/${LDAP_USERNAME}/asm2vec.patch
RUN git clone https://github.com/RaRe-Technologies/gensim/ && \
	( cd gensim ; git checkout e889fa3d45a406cabbc7e180fa9a8ee3f76ac6f0 ; patch -s -p0 < ../asm2vec.patch )  && \
	pip3 install gensim/

# function extraction and acfg_disasm
COPY prep_ida.sh /home/${LDAP_USERNAME}/prep_ida.sh
COPY extract_functions_ida.py /home/${LDAP_USERNAME}/extract_functions_ida.py
COPY cli_acfg_disasm.py /home/${LDAP_USERNAME}/cli_acfg_disasm.py
COPY IDA_acfg_disasm.py /home/${LDAP_USERNAME}/IDA_acfg_disasm.py
COPY extract_function.sh /home/${LDAP_USERNAME}/extract_function.sh
COPY extract_droids.sh /home/${LDAP_USERNAME}/extract_droids.sh
COPY preprocess_droids.sh /home/${LDAP_USERNAME}/preprocess_droids.sh
COPY create_acfg.sh /home/${LDAP_USERNAME}/create_acfg.sh
COPY create_acfg_droids.sh /home/${LDAP_USERNAME}/create_acfg_droids.sh

# asm2vec
COPY i2v_preprocessing.py /home/${LDAP_USERNAME}/i2v_preprocessing.py
COPY i2v.py /home/${LDAP_USERNAME}/i2v.py
COPY reproduce.sh /home/${LDAP_USERNAME}/reproduce.sh

RUN chown -R ${LDAP_USERNAME}:${LDAP_GROUPNAME} /home/${LDAP_USERNAME}/

USER ${LDAP_USERNAME}

WORKDIR /home/${LDAP_USERNAME}
