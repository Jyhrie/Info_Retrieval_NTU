# Info_Retrieval_NTU
to start solr

```bash
docker compose up --build 
```

get container name
```bash
docker ps 
```

create solr core
```bash
docker exec -it <container_id> solr create_core -c info_retrieval
```

