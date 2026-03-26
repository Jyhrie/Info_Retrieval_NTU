# SC4021-Info-retrieval

Building an opinion search engine on trading platforms (Which trading platform is the best?)

## Getting started
Please ensure that you have machine with CUDA enabled GPU as it it necessary for the backend to startup and get working.

### Running the Application (with Automated Indexing)
**1\. Create JSON dataset in respective folder**

1. Go into the indexing folder via the command `cd indexing`.
2. Create a virtual environment using `python -m venv venv` and activate it
3. Install the requirements using `pip install -r build/requirements.txt`
4. Cd into the scripts folder and run the command `python index_to_solr.py`
5. You should see `✅ sample_docs.json created with XXX documents.` in your logs.
6. To check if the dataset is present, go to the dataset folder and there should be a file called `sample_docs.json`.

**2\. Start all services using Docker Compose**

Run the following command on terminal:

```bash
docker-compose up --build
```

This command will:

-   Start the Solr server on port 8983

-   Build and start the backend service on port 8000

-   Automatically index documents into Solr using the `solr-indexer` service, as the `solr-indexer` container waits briefly for Solr to be ready and then automatically sends the documents located in `indexing/dataset/sample_docs.json` to the `mycollection` core in Solr.

✅ Make sure your Docker daemon is running before executing the above command.

You should see `✅ Done.` in your logs.

---

**3\. Verify Solr Indexing (Optional) and Runnning the application as a whole (Neccessary)**

After running `docker-compose up --build`, you should see log messages like:

`🚀 Posting sample_docs.json to Solr...
...
✅ Done.`

To manually verify the indexed data:

1\.  Visit: <http://localhost:8983/solr/#/mycollection/query>

2\.  In the query box, type:

    `*:*`

3\.  Click **Execute Query**

4\.  You should see a list of indexed documents in the response panel.

Once the backend and frontend has been set up (you should see <http://0.0.0.0:8000> for backend and <http://localhost:5173> for frontend):
1\. Visit: <http://localhost:5173> to see the frontend and test out the application
2\. Visit: <http://localhost:8000/docs> to see the api endpoints for backend