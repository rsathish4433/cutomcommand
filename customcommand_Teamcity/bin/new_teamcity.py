import splunk.Intersplunk
import urllib
import requests
import sys
import time
import shutil
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as xml

import logging
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

APP_NAME = "customcommand_Teamcity"
SCRIPT_NAME = "teamcity"

def setup_splunk_logger(level, app, script):
    """
    setup_logger - set up logger for controller
    :param level:
    :param app:
    :param script:
    :return:
    """
    logger = logging.getLogger('splunk.%s-%s' % (app, script))
    logger.propagate = False
    logger.setLevel(level)
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        make_splunkhome_path(['var', 'log', 'splunk', 'customcommand_Teamcity.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter("%(asctime)s   method:teamcity   %(levelname)-s\t : %(lineno)d - %(message)s  ")
    splunk_log_handler.setFormatter(formatter)
    logger.addHandler(splunk_log_handler)
    return logger

log_level = "DEBUG"
logger = setup_splunk_logger(log_level, APP_NAME, SCRIPT_NAME)
newresults = []
common_path = 'httpAuth/app/rest'

def form_xml_content(conf_id, url_id):
    """
    <build personal="true" branchName="logicBuildBranch">
        <buildType id="buildConfID"/>
        <agent id="3"/>
        <comment>
            <text>
                build triggering comment
            </text>
        </comment>
        <properties>
            <property name="env.myEnv" value="bbb"/>
        </properties>
    </build>
    """
    build = xml.Element('build')
    buildType = xml.SubElement(build, 'buildType')
    # agent = xml.SubElement(build, 'agent')
    # comment = xml.SubElement(build, 'comment')
    # text = xml.SubElement(comment, 'text')
    # properties = xml.SubElement(build, 'properties')
    # property = xml.SubElement(properties, 'property')
    # build.set('personal', 'true')
    # build.set('branchName', 'logicBuildBranch')
    # static configure buildConfID here
    buildType.set('id', url_id)
    # agent.set('id', '3')
    # text.text = "build triggering comment"
    # property.set("name", "env.myEnv")
    # property.set("value", conf_id)
    my_xml_data = xml.tostring(build)
    return my_xml_data

def teamcity_run_build_remote(base_url=None, user=None, passwd=None, conf_id=None, url_id=None ):
    """
    :param base_url:
    :param user:
    :param passwd:
    :param conf_id:
    :param url_id:
    :return:
    """
    xml_response = None

    xml_data = form_xml_content(conf_id, url_id)

    # trigger build
    url = '{}/{}/buildQueue'.format(base_url, common_path)
    try:
        logger.debug("Starting a build with xml_data={}, POST url={}".format(xml_data, url))
        response = requests.post(url, auth=HTTPBasicAuth(user, passwd),
                                 data=xml_data,
                                 headers={"Content-Type": "application/xml"})
        xml_response = xml.fromstring(response.content)
        del response
    except requests.exceptions.RequestException:
        logger.debug('HTTP Request {} failed'.format(url))
        return 'HTTP Request {} failed'.format(url)

    # get build id
    build_id = xml_response.attrib['id']
    logger.debug("build_id={}".format(build_id))

    url += '/id:{}'.format(build_id)
    state = None
    status = None
    build_number = None
    # monitor build state

    try:
        logger.debug("Getting build status, build_id={}, POST url={}".format(build_id, url))
        response = requests.get(url, auth=HTTPBasicAuth(user, passwd), headers={"Content-Type": "application/xml"})
        xml_response = xml.fromstring(response.content)
        del response
        build_number = xml_response.attrib['number']
        state = xml_response.attrib['state']
        return build_number
    except requests.exceptions.RequestException:
        logger.debug('HTTP Request {} failed'.format(url))
        return 'HTTP Request {} failed'.format(url)


base_url = None
user = None
passwd = None
common_path = 'httpAuth/app/rest'

newresults = []

results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()

try:
    keywords, argvals = splunk.Intersplunk.getKeywordsAndOptions()
    logger.debug('Argument passed %s' % argvals["id"])

    id = argvals["id"]
    conf_id = argvals["conf_id"]
    for result in results:
        tmp_result = result
        if conf_id in result.keys() and id in result.keys():
           logger.info("conf id:{}".format(result[conf_id]))
           logger.info("id:{}".format(result[id]))
           tmp_result["build_number"] = teamcity_run_build_remote(base_url=base_url, user=user,
                                                                  passwd=passwd,
                                                                  conf_id=result[conf_id],
                                                                  url_id = result[id])
        else:
           tmp_result["build_number"] = "conf id not found"

        newresults.append(tmp_result)

except Exception as e:
    logger.error(e)

splunk.Intersplunk.outputResults(newresults)
