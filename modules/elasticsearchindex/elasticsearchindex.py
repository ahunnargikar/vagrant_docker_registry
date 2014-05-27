"""Index backends for the search endpoint
"""

import logging
import json
from pyelasticsearch import ElasticSearch
from docker_registry import storage
from docker_registry.lib import config
from docker_registry.lib.index import Index

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
        """Iterate through repositories in storage

        This helper is useful for building an initial database for
        your search index.  Yields dictionaries:

          {'name': name, 'description': description}
        """
        try:
            namespace_paths = list(
                store.list_directory(path=store.repositories))
        except OSError:
            namespace_paths = []
        for namespace_path in namespace_paths:
            namespace = namespace_path.rsplit('/', 1)[-1]
            try:
                repository_paths = list(
                    store.list_directory(path=namespace_path))
            except OSError:
                repository_paths = []
            for path in repository_paths:
                repository = path.rsplit('/', 1)[-1]
                name = '{0}/{1}'.format(namespace, repository)
                description = None  # TODO(wking): store descriptions
                yield({'name': name, 'description': description})

    def _handle_repository_created(self, sender, namespace, repository, value):
        pass

    def _handle_repository_updated(self, sender, namespace, repository, value):

        #Get the list of checksums
        checkSums = []
        for item in value:
            checkSums.append(item['id'])

        #Loop over the image layers in this repository and collect the metadata in a single list which will be bulk-updated in Elasticsearch
        store = storage.load()
        documentList = []
        for item in value:

            #Load the image layer data from the data store
            data = store.get_content(store.image_json_path(item['id']))
            document={}
            data = json.loads(data)

            #Concatenate the <namespace>_<repository>_imageid to generate a unique primary key id in Elasticsearch
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
            document['domainName'] = data.get('container_config').get('Domainname',"")
            document['user'] = data.get('container_config').get('User',"")
            document['memory'] = data.get('container_config').get('Memory',"")
            document['memorySwap'] = data.get('container_config').get('MemorySwap',"")
            document['cpuShares'] = data.get('container_config').get('CpuShares',"")
            document['attachStdin'] = data.get('container_config').get('AttachStdin',"")
            document['attachStdout'] = data.get('container_config').get('AttachStdout',"")
            document['attachStderr'] = data.get('container_config').get('AttachStderr',"")
            document['portSpecs'] = data.get('container_config').get('PortSpecs',"")
            document['exposedPorts'] = data.get('container_config').get('ExposedPorts',"")
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
            document['onBuild'] = data.get('container_config').get('OnBuild',"")
            document['domainName'] = data.get('container_config').get('Domainname',"")
            document['dockerVersion'] = data.get('docker_version',"")
            documentList.append(document)

        #Get the Elasticsearch address from the config file
        cfg = config.load()
        es = ElasticSearch(cfg.search_options.get("address"))
        es.bulk_index(cfg.search_options.get("index"), cfg.search_options.get("type"), documentList, id_field='id')

    def _handle_repository_deleted(self, sender, namespace, repository):
        pass

    def results(self, search_term):
        pass