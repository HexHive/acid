#####################################
# RCP CaaS requirement (Image)
#####################################
# The best practice is to use an image
# with GPU support pre-built by Nvidia.
# https://catalog.ngc.nvidia.com/orgs/nvidia/containers/

# For example, if you want to use an image with pytorch already installed
FROM --platform=linux/amd64 nvcr.io/nvidia/pytorch:24.10-py3

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

# # Copy your code inside the container
# RUN mkdir -p /home/${LDAP_USERNAME}
# COPY ./ /home/${LDAP_USERNAME}

RUN mkdir /home/${LDAP_USERNAME}/.idapro
COPY ida.reg /home/${LDAP_USERNAME}/.idapro/
# RUN mkdir /home/runai-home
# RUN mkdir /home/runai-home/.idapro
# COPY ida.reg /home/runai-home/.idapro/ida.reg
COPY idapro-9.0 /opt/idapro-9.0/

# Set your user as owner of the new copied files
RUN chown -R ${LDAP_USERNAME}:${LDAP_GROUPNAME} /home/${LDAP_USERNAME}

# Install required packages
RUN apt update && apt install python3-pip git wget -y

# Set the working directory in your user's home
RUN usermod -aG sudo ${LDAP_USERNAME}
WORKDIR /home/${LDAP_USERNAME}
USER ${LDAP_USERNAME}

RUN mkdir -p ~/miniconda3 && \ 
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh && \
    bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3 && \
    rm ~/miniconda3/miniconda.sh

# # setup jtrans environment for training
# RUN . ~/miniconda3/bin/activate && \
#     conda create -n jtrans python=3.8 pandas tqdm -y && \
#     conda activate jtrans && \
#     python -m pip install simpletransformers networkx pyelftools

COPY requirements.txt .
RUN pip install -r requirements.txt
# RUN python3 -m pip install pandas tqdm simpletransformers networkx pyelftools

#  setup processing environment for feature extraction
RUN . ~/miniconda3/bin/activate && \
    conda create -n processing python=3.9 tqdm -y && \
    conda activate processing && \
    python3 -m pip install pyelftools binaryai networkx

# clone jtrans and get code/models
RUN git clone --branch dfba2f5e5971c2b8497496f124448ee024b0aec7 https://github.com/vul337/jTrans.git
USER root
COPY finetune.py /home/${LDAP_USERNAME}/jTrans/finetune.py
COPY eval_save.py /home/${LDAP_USERNAME}/jTrans/eval_save.py
COPY fasteval.py /home/${LDAP_USERNAME}/jTrans/fasteval.py
COPY playdata.py /home/${LDAP_USERNAME}/jTrans/datautils/playdata.py  
COPY process.py /home/${LDAP_USERNAME}/jTrans/datautils/process.py  
COPY run.py /home/${LDAP_USERNAME}/jTrans/datautils/run.py
COPY droids.tar /home/${LDAP_USERNAME}/jTrans/droids.tar
COPY add_versions_to_log.py /home/${LDAP_USERNAME}/jTrans/add_versions_to_log.py
COPY reproduce.sh /home/${LDAP_USERNAME}/jTrans/reproduce.sh
COPY change_logs.sh /home/${LDAP_USERNAME}/jTrans/change_logs.sh
RUN chown -R ${LDAP_USERNAME}:${LDAP_GROUPNAME} /home/${LDAP_USERNAME}/jTrans

USER {LDAP_USERNAME}
# COPY root/binary_test/jtrans/code/dataset.zip /code/jtrans/dataset.zip
# RUN /opt/idapro-9.0/idapyswitch --force-path /home/rfall/miniconda3/envs/processing/lib/libpython3.9.so
WORKDIR /home/${LDAP_USERNAME}/jTrans
# WORKDIR /mnt/hexhive/jtrans/code/jTrans
