#!/bin/bash
echo "Extracting functions from $1 $2"
$IDA_PATH -A -S"extract_functions_ida.py" -L"extract_log.txt" -Oextract_functions:$2/selected/ $1