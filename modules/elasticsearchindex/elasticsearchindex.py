"""Index backends for the search endpoint
"""

import logging
import json
from pyelasticsearch import ElasticSearch
from pyelasticsearch.exceptions import (Timeout, ConnectionError, ElasticHttpError, InvalidJsonResponseError, ElasticHttpNotFoundError)
from docker_registry import storage
from docker_registry.lib import config
from docker_registry.lib.index import Index
import urllib2

logger = logging.getLogger(__name__)

class Index (Index):
    """A backend for the search endpoint

    The backend can use .walk_storage to generate an initial index,
    ._handle_repository_* to stay up to date with registry changes,
    and .results to respond to queries.
    """
    def __init__(self):
        super(Index, self).__init__()

    def _walk_storage(self, store):
        pass

    def _handle_repository_created(self, sender, namespace, repository, value):
        pass

    def _handle_repository_updated(self, sender, namespace, repository, value):
        """
        Triggered after a docker push operation has completed via Signals

        @type  sender: List
        @param sender: Flask object with request details
        @type  namespace: String
        @param namespace: Docker namespace under which the image layers are stored
        @type  repository: String
        @param repository: Docker repository under which the image layers are stored
        @type  value: List
        @param value: List of Docker image layer JSON metadata objects
        """
        #Get the list of checksums for all the image layers which will be included in the parent layer
        checkSums = self.get_checksums(value)

        #Loop over the image layers in this repository and collect the metadata
        store = storage.load()
        documentList = []
        for item in value:

            #Load the image layer data from the data store
            data = store.get_content(store.image_json_path(item['id']))
            data = json.loads(data)

            #Generate the index document for this layer
            appUrl, document = self.create_index_document(data, checkSums, namespace, repository)
            documentList.append(document)

            #If this document has a maintainer URL then retrieve Github metadata
            if appUrl:
                jsonMetadata = self.get_app_metadata(appUrl)

                #Add the JSON metadata to the (single) zeroth parent layer document only
                for item in documentList:
                    if (item.get("isParent","") == "true"):
                        item['github_sha'] = jsonMetadata.get("sha", "")
                        item['github_url'] = jsonMetadata.get("url", "")
                        item['github_html_url'] = jsonMetadata.get("html_url", "")

        #Store the document list in the search index
        self.set_in_index(documentList)

    def _handle_repository_deleted(self, sender, namespace, repository):
        pass

    def results(self, search_term):
        pass

    def create_index_document(self, data, checkSums, namespace, repository):

        appUrl = ""
        document={}

        #Concatenate the <namespace>_<repository>_imageid to generate a unique primary key id
        document['id'] = namespace + "_" + repository + "_" + data['id']
        document['namespace'] = namespace
        document['repository'] = repository

        #If this is a parent container image layer then create a new field with all its child layers
        if (data.get('parent') == None):
            document['isParent'] = "true"
            document['imageLayers'] = checkSums
        else:
            document['isParent'] = "false"

        document['parent'] = data.get('parent',"")
        document['created'] = data.get('created',"")
        document['container'] = data.get('container',"")
        document['author'] = data.get('author',"")
        document['architecture'] = data.get('architecture',"")
        document['os'] = data.get('os',"")
        document['size'] = data.get('Size',"")
        document['comment'] = data.get('comment',"")
        document['hostname'] = data.get('container_config').get('Hostname',"")

        #Parse the cmd field JSON (if any) from the image layer. 
        #If the maintainer version matches the repository version then we have the correct version number for this image
        field = data.get('container_config').get('Cmd',"")
        appUrlCheck = self.get_app_url(field, repository)
        if appUrlCheck is not None:
            appUrl = appUrlCheck

        document['cmd'] = data.get('container_config').get('Cmd',"")
        document['domainName'] = data.get('container_config').get('Domainname',"")
        document['user'] = data.get('container_config').get('User',"")
        document['memory'] = data.get('container_config').get('Memory',"")
        document['memorySwap'] = data.get('container_config').get('MemorySwap',"")
        document['cpuShares'] = data.get('container_config').get('CpuShares',"")
        document['attachStdin'] = data.get('container_config').get('AttachStdin',"")
        document['attachStdout'] = data.get('container_config').get('AttachStdout',"")
        document['attachStderr'] = data.get('container_config').get('AttachStderr',"")
        document['portSpecs'] = data.get('container_config').get('PortSpecs',"")
        #document['exposedPorts'] = data.get('container_config').get('ExposedPorts',"")
        document['tty'] = data.get('container_config').get('Tty',"")
        document['openStdin'] = data.get('container_config').get('OpenStdin',"")
        document['stdinOnce'] = data.get('container_config').get('StdinOnce',"")
        document['dns'] = data.get('container_config').get('Dns',"")
        document['image'] = data.get('container_config').get('Image',"")
        document['volumes'] = data.get('container_config').get('Volumes',"")
        document['volumesFrom'] = data.get('container_config').get('VolumesFrom',"")
        document['workingDir'] = data.get('container_config').get('WorkingDir',"")
        document['entrypoint'] = data.get('container_config').get('Entrypoint',"")
        document['networkDisabled'] = data.get('container_config').get('NetworkDisabled',"")
        #document['onBuild'] = data.get('container_config').get('OnBuild',"")
        document['domainName'] = data.get('container_config').get('Domainname',"")
        document['dockerVersion'] = data.get('docker_version',"")

        return (appUrl, document)

    def get_checksums(self, list):
        """
        Extract the Github URL packaged inside the MAINTAINER
        command speficied in the Dockerfile for this image layer

        @type  list: List
        @param list: List of image layer objects
        @return:  List of checksums
        """
        checkSums = []
        for item in list:
            checkSums.append(item['id'])
        return checkSums

    def get_app_url(self, list, repository):
        """
        Extract the Github URL packaged inside the MAINTAINER
        command specified in the Dockerfile for this image layer

        @type  list: List
        @param list: List containing the command that generated this image layer
        @type  repository: String
        @param repository: The application version string
        @return:  The Github URL if found otherwise None
        """
        if list:
            maintainer = list[-1]
            searchString = '#(nop) MAINTAINER '
            if (maintainer.startswith(searchString)):
                try:
                    #jsonObject = json.loads(maintainer[18:])
                    #Parse the JSON object inside the maintainer directive and extract the URL
                    jsonObject = json.loads(maintainer.split(searchString,1)[1])
                    if (jsonObject.get("version", "") == repository):
                        appUrl = jsonObject.get("url", "")
                        return appUrl
                except ValueError:
                    logger.debug("Error getting the App URL string!")
                    return None
        else:
            return None

    def get_app_metadata(self, appUrl):
        """
        Extract the Github URL packaged inside the MAINTAINER
        command speficied in the Dockerfile for this image layer

        @type  appUrl: String
        @param appUrl: URL to fetch the application Github metadata from
        @return:  The Github URL if found otherwise None
        """
        try:
            req = urllib2.Request(appUrl, headers={'User-Agent': 'docker-registry'})
            return json.loads(urllib2.urlopen(req).read())
        except ValueError:
            logger.debug("Error parsing the Github response JSON!")
            return None

    def set_in_index(self, documentList):
        """
        Store the list of documents in the Elasticsearch index via HTTP APIs

        @type  documentList: List
        @param documentList: List of image layer JSON documents
        """
        #Get the Elasticsearch address from the config file
        cfg = config.load()

        #Store the document list in Elasticsearch
        es = ElasticSearch(cfg.search_options.get("address"))
        try:
            es.bulk_index(cfg.search_options.get("index"), cfg.search_options.get("type"), documentList, id_field='id')
        except InvalidJsonResponseError:
            logger.debug("InvalidJsonResponseError!")
        except Timeout:
            logger.debug("Timeout!")
        except ConnectionError:
            logger.debug("ConnectionError!")
        except ElasticHttpError:
            logger.debug("ElasticHttpError!")
        except InvalidJsonResponseError:
            logger.debug("InvalidJsonResponseError!")
        except ElasticHttpNotFoundError:
            logger.debug("ElasticHttpNotFoundError!")            