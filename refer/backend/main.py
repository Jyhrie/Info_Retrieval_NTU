import logging
import datetime

from fastapi import FastAPI, Response, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from response_model import QueryResponse, QueryPayload

from utils.api_helper import get_results, convert_to_query_response

app = FastAPI(title="Backend for stocks opinion analysis")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.error(f"Validation error: {exc.errors()} | Body: {exc.body}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

# add logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

### handler ###
handler = logging.StreamHandler()
logger.addHandler(handler)

### formatter ###
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# this endpoint is to test if server is up and working
@app.get("/ping")
async def ping():
    return Response(content="pong", status_code=200)

@app.post("/api/query", response_model=QueryResponse)
async def query(query_request: QueryPayload) -> QueryResponse:
    payload = query_request.payload
    query = payload.query
    platforms = payload.subreddit
    start_date = payload.date

    # convert string date in "YYYY-MM-DD" to ISO format
    if start_date:
        try:
            dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            # Append 'Z' to indicate UTC if required
            start_date = dt.isoformat() + "Z"
            logger.info(f"Converted start_date: {start_date}")
        except Exception as e:
            logger.error(f"Date conversion error: {e}")
            start_date = None
        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    print(f"Query: {query}, Platforms: {platforms}, Start Date: {start_date}")
    try:
        # send query to solr and get relevant matches
        results, keywords = get_results(query, platforms, start_date)

        # convert solr response to query response
        recordCount, subreddits, comments = convert_to_query_response(results)

        return QueryResponse(
            sentiment="positive",
            comments=comments,
            keywords=keywords,
            subreddits=subreddits,
            recordCount=recordCount,
        )
    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")