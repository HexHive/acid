#!/bin/bash
set -x
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
[[ ! -d "$SCRIPT_DIR/idapro-9.0" ]] && echo "idapro-9.0 not found in $SCRIPT_DIR" && exit 1 

tag=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 8 | head -n 1)
docker build -t registry.rcp.epfl.ch/binary-similarity/rcp-jtrans:latest -t registry.rcp.epfl.ch/binary-similarity/rcp-jtrans:$tag --build-arg LDAP_USERNAME=rfall --build-arg LDAP_UID=246723 --build-arg LDAP_GROUPNAME=rcp-runai-hexhive --build-arg LDAP_GID=83413 .
docker push registry.rcp.epfl.ch/binary-similarity/rcp-jtrans:latest
docker push registry.rcp.epfl.ch/binary-similarity/rcp-jtrans:$tag