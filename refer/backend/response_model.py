from typing import List, Dict, Any
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    """
    Model for a query.
    """
    query: str = Field(description="Query")
    subreddit: List[str] = Field(description="List of subreddits chosen by user to search in")
    date: str = Field(description="Start date in ISO format")
class QueryPayload(BaseModel):
    """
    Model for a query payload.
    """
    payload: QueryRequest = Field(description="Query payload")
class Docs(BaseModel):
    """
    Model for a document.
    """
    id: str = Field(description="id which is the same as content_id")
    post_id: str = Field(description="Post id")
    subreddit: str = Field(description="Subreddit")
    title: str = Field(description="Post title")
    url: str = Field(description="Post url")
    post_content: str = Field(description="Post content")
    comment_id: str = Field(description="Comment id")
    comment_content: str = Field(description="Comment content")
    comment_author: str = Field(description="Comment author")
    score: float = Field(description="Upvotes minus downvotes")
    datetime: str = Field(description="Date and time of the post creation in ISO format")

class SolrResponse(BaseModel):
    """
    Model for a solr response from mycollection
    """
    numFound: int = Field(description="Number of results")
    start: int = Field(description="Start index")
    docs: List[Docs] = Field(description="List of documents")

class Comment(BaseModel):
    """
    Model for a comment.
    """
    text: str = Field(description="Comment text")
    sentiment: str | None = Field(description="sentiment of the individual comment")

class Keyword(BaseModel):
    """
    Model for a keyword.
    """
    keyword: str = Field(description="Keyword")
    count: int = Field(description="Count of the keyword in the results")

class QueryResponse(BaseModel):
    """
    Response model for a query.
    """
    sentiment: str = Field(description="Overall sentiment of the results returned from solr")
    comments: List[Comment] = Field(description="List of comments returned from solr")
    keywords: List[Keyword] = Field(description="List of keywords within the results in the solr")
    subreddits: List[str] = Field(description="List of subreddits the comments or posts belong to")
    recordCount: int = Field(description="Total number of records returned from solr")
