FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install -r /app/build/requirements.txt
RUN pip install fastapi[standard] uvicorn
RUN python -m spacy download en_core_web_sm

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
