# run service

```shell
cd BeyondAgent
python beyondagent/core/service/model_service.py
```

# test service

```shell
python beyondagent/test/test_service.py
```

# qingxu
```shell
# 1. edit query, port, vm etc
nano docker-compose.yml
# 2. run
docker compose down && docker compose build && docker compose up
# 3. then watch vm at http://localhost:16901 (default password is headless)
```


# vector store
If a vector database is involved, you will need an Elasticsearch environment. You can refer to the following steps:
- If you don’t have Docker installed, download and install [Docker Desktop](https://www.docker.com/products/docker-desktop) for your operating system. 
- To set up [Elasticsearch](https://www.elastic.co/docs/solutions/search/run-elasticsearch-locally) and Kibana locally, run the start-local script in the command line:
```shell
curl -fsSL https://elastic.co/start-local | sh
```

Or manually download and load the image. Here, we take elasticsearch-wolfi:9.0.0 as an example:
```shell
docker pull docker.elastic.co/elasticsearch/elasticsearch-wolfi:9.0.0
docker run -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  -e "xpack.license.self_generated.type=trial" \
  docker.elastic.co/elasticsearch/elasticsearch-wolfi:9.0.0
```

# run module service
