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

"""
This script is used to update sparkmagic config files with the provided OLP SDK jars version.
This script takes as argument -v/--version which implies the version of OLP SDK to be upgraded to.
Command to execute this script: python config_file_updater.py -v <version_to_upgrade_to>
Command for help: python config_file_updater.py -h
"""

import json
import lxml
from lxml import etree
from io import StringIO, BytesIO
import requests
from pathlib import Path
import argparse
import sys
import zipfile
import shutil

# Accept and parse version argument.
parser = argparse.ArgumentParser(description='Config file Updater')
required_named = parser.add_argument_group('required named arguments')
required_named.add_argument('-v', '--version', required=True, help='Version of OLP SDK to be upgraded to')
args = parser.parse_args()
print(f'Version {args.version}')

# Read m2 settings.xml file to fetch olp repository details.
try:
    with open(Path.home() / ".m2" / "settings.xml", 'r') as f:
        contents = f.read()
except IOError:
    print(Path.home() / ".m2" / "settings.xml file not accessible.")
    sys.exit(1)

tree = etree.parse(StringIO(contents))

for elem in tree.getroot().getiterator():
    elem.tag = etree.QName(elem).localname

etree.cleanup_namespaces(tree.getroot())

username = tree.find('servers').find("server").find("username").text

password = tree.find('servers').find("server").find("password").text

repo_url = tree.find('profiles').find("profile").find("repositories").find("repository").find("url").text

is_zip_file = False

# Read config.json file and save a copy as original_config.json.
if Path('config.json').is_file():
    with open('config.json', 'r') as f:
        configfile = json.load(f)
    
    with open('original_config.json', 'w') as outfile:
        json.dump(configfile, outfile, indent=2)
        print('Creating backup of config.json as original_config.json')
elif Path('spark-conf-files.zip').is_file():
    with zipfile.ZipFile('spark-conf-files.zip', 'r') as zip_ref:
        zip_ref.extractall()
    with open(Path("spark-conf-files") / Path("config.json"), 'r') as f:
        configfile = json.load(f)
    is_zip_file = True
else:
    print('Either config.json or spark-conf-files.zip file are expected in the current directory')
    sys.exit(1)

jars_list = configfile['session_configs']['conf']['spark.jars.packages']

# Dictionary of jars and corresponding matching key to be used to find the version.
dict_jars_match_key = {}
dict_jars_match_key['com.here.olp.util:mapquad'] = 'mapquad.version'
dict_jars_match_key['com.here.platform.location:location-compilation-core_2.11'] = 'location-compilation-core.version'
dict_jars_match_key['com.here.platform.location:location-core_2.11'] = 'location-core.version'
dict_jars_match_key['com.here.platform.location:location-inmemory_2.11'] = 'location-inmemory.version'
dict_jars_match_key['com.here.platform.location:location-integration-here-commons_2.11'] = 'location-integration-here-commons.version'
dict_jars_match_key['com.here.platform.location:location-integration-optimized-map_2.11'] = 'location-integration-optimized-map.version'
dict_jars_match_key['com.here.platform.location:location-data-loader-standalone_2.11'] = 'location-data-loader-standalone.version'
dict_jars_match_key['com.here.platform.location:location-spark_2.11'] = 'location-spark.version'
dict_jars_match_key['com.here.platform.location:location-compilation-here-map-content_2.11'] = 'location-compilation-here-map-content.version'
dict_jars_match_key['com.here.schema.sdii:sdii_archive_v1_java'] = 'sdii_archive-schema.version'
dict_jars_match_key['com.here.sdii:sdii_message_v3_java'] = 'sdii-schema.version'
dict_jars_match_key['com.here.sdii:sdii_message_list_v3_java'] = 'sdii-schema.version'
dict_jars_match_key['com.here.schema.rib:lane-attributes_v2_scala'] = 'rib-schema.version'
dict_jars_match_key['com.here.schema.rib:road-traffic-pattern-attributes_v2_scala'] = 'rib-schema.version'
dict_jars_match_key['com.here.schema.rib:advanced-navigation-attributes_v2_scala'] = 'rib-schema.version'
dict_jars_match_key['com.here.schema.rib:cartography_v2_scala'] = 'rib-schema.version'
dict_jars_match_key['com.here.schema.rib:adas-attributes_v2_scala'] = 'rib-schema.version'

url = "".join([repo_url, "/com/here/platform/sdk-batch-bom/", args.version, "/sdk-batch-bom-", args.version,".pom"])
sdk_batch_pom = requests.get(url, auth=(username, password))
if(sdk_batch_pom.status_code != 200):
    print('Error: Please enter valid version')
    sys.exit(1)

sdk_batch_pom_tree = etree.parse(BytesIO(sdk_batch_pom.content))

for elem in sdk_batch_pom_tree.getroot().getiterator():
    elem.tag = etree.QName(elem).localname

etree.cleanup_namespaces(sdk_batch_pom_tree.getroot())

properties = sdk_batch_pom_tree.find('properties').getchildren()

dict_jar_version = dict()
for elem in properties:
    dict_jar_version[elem.tag] = elem.text

final_jars_list = list()
for jarname, version_finder in dict_jars_match_key.items():
    if version_finder in dict_jar_version:
        final_jars_list.append(jarname + ":" + dict_jar_version.get(version_finder))

metadata_jars_dict = {}

# Dictionary of jars and corresponding matching metadata url to be used to fetch the version.
metadata_jars_dict['com.here.platform.data.client:spark-support_2.11'] = repo_url + '/com/here/platform/data/client/spark-support_2.11/maven-metadata.xml'
metadata_jars_dict['com.here.platform.data.client:data-client_2.11'] = repo_url + '/com/here/platform/data/client/data-client_2.11/maven-metadata.xml'
metadata_jars_dict['com.here.platform.data.client:client-core_2.11'] = repo_url + '/com/here/platform/data/client/client-core_2.11/maven-metadata.xml'
metadata_jars_dict['com.here.platform.data.client:hrn_2.11'] = repo_url + '/com/here/platform/data/client/hrn_2.11/maven-metadata.xml'
metadata_jars_dict['com.here.platform.data.client:data-engine_2.11'] = repo_url + '/com/here/platform/data/client/data-engine_2.11/maven-metadata.xml'
metadata_jars_dict['com.here.platform.data.client:blobstore-client_2.11'] = repo_url + '/com/here/platform/data/client/blobstore-client_2.11/maven-metadata.xml'
metadata_jars_dict['com.here.account:here-oauth-client'] = repo_url + '/com/here/account/here-oauth-client/maven-metadata.xml'
metadata_jars_dict['com.here.platform.analytics:spark-ds-connector-deps_2.11'] = repo_url + '/com/here/platform/analytics/spark-ds-connector-deps_2.11/maven-metadata.xml'
metadata_jars_dict['com.here.platform.analytics:spark-ds-connector_2.11'] = repo_url + '/com/here/platform/analytics/spark-ds-connector_2.11/maven-metadata.xml'

for jarname, url in metadata_jars_dict.items():
    metadata_response = requests.get(url, auth=(username, password))
    metadata_response_tree = etree.parse(BytesIO(metadata_response.content))
    final_jars_list.append(jarname + ":" + metadata_response_tree.getroot().find("version").text)

final_jars_list.extend(['com.typesafe.akka:akka-actor_2.11:2.5.11', 'com.beachape:enumeratum_2.11:1.5.13', 'com.github.ben-manes.caffeine:caffeine:2.6.2', 'com.github.cb372:scalacache-caffeine_2.11:0.24.3', 'com.github.cb372:scalacache-core_2.11:0.24.3', 'com.github.os72:protoc-jar:3.6.0', 'com.google.protobuf:protobuf-java:3.6.1', 'com.iheart:ficus_2.11:1.4.3', 'com.typesafe:config:1.3.3', 'org.apache.logging.log4j:log4j-api-scala_2.11:11.0', 'org.typelevel:cats-core_2.11:1.4.0', 'org.typelevel:cats-kernel_2.11:1.4.0', 'org.apache.logging.log4j:log4j-api:2.8.2', 'com.here.platform.location:location-examples-utils_2.11:0.4.115'])

configfile['session_configs']['conf']['spark.jars.packages'] = ','.join(final_jars_list)

# Save the final jars list in the config.json file.
if is_zip_file:
    with open(Path("spark-conf-files") / Path("config.json"), 'w') as outfile:
        json.dump(configfile, outfile, indent=2)
    shutil.make_archive('spark-conf-files', 'zip', base_dir='spark-conf-files')
    shutil.rmtree("spark-conf-files")
    print('Updated zipfile created successfully: spark-conf-files.zip')
else:
    with open("config.json", 'w') as outfile:
        json.dump(configfile, outfile, indent=2)
        print('Updated file created successfully: config.json')