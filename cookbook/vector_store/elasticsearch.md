## Elasticsearch Vector Store
If a vector database is involved, you will need an Elasticsearch environment. You can refer to the following steps.

### Install Docker Desktop
If you don’t have Docker installed, download and install [Docker Desktop](https://www.docker.com/products/docker-desktop) for your operating system. 

### Set up Elasticsearch
You can choose one of the following three options.

#### All in One Script
To set up [Elasticsearch](https://www.elastic.co/docs/solutions/search/run-elasticsearch-locally) and Kibana locally, run the start-local script in the command line:
```shell
curl -fsSL https://elastic.co/start-local | sh
```

#### Docker Run Image with 4GB Memory
manually download and load the image. Here, we take `elasticsearch-wolfi:9.0.0` as an example:
```shell
docker pull docker.elastic.co/elasticsearch/elasticsearch-wolfi:9.0.0
docker run -p 9200:9200 \
  --memory='4GB' \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "xpack.license.self_generated.type=trial" \
  docker.elastic.co/elasticsearch/elasticsearch-wolfi:9.0.0
```

#### Docker Run Image with Http Host
```shell
docker pull docker.elastic.co/elasticsearch/elasticsearch-wolfi:9.0.0
docker run -p 8200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "xpack.license.self_generated.type=trial" \
  -e "http.host=0.0.0.0" \
  docker.elastic.co/elasticsearch/elasticsearch-wolfi:9.0.0
```

### Inject Environment Variables
Inject variables of the `ES_HOSTS` into the environment where you use Elasticsearch.
```shell
export ES_HOSTS=http://localhost:9200
```