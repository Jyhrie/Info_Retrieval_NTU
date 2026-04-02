# Info_Retrieval_NTU
to start solr

```bash
docker compose up --build 
```

get container name/id
```bash
docker ps 
```

create solr core
```bash
docker exec -it <container_id> solr create_core -c info_retrieval
```

copy file into docker container
```bash
docker cp your_file.csv <container_id>:/data/your_file.csv

```

upload file into solr core
```bash
docker exec -it <container_id> bin/solr post -c info_retrieval /data/your_file.csv
```
