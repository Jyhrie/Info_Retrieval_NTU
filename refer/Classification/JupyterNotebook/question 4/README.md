
# 📘 Reddit Stock Sentiment Classification

This project performs sentiment analysis on data scraped from Reddit stock-related subreddits (e.g., r/stocks, r/StockMarket). It includes text preprocessing, sentiment scoring, named entity recognition, clustering, and evaluation of classification performance.

## 📁 Files

- `Classification.ipynb`: Main Jupyter Notebook containing the entire pipeline from preprocessing to evaluation.
- `Labelled.csv`: Manually labelled data (10% of total) used for evaluation.
- `Sentimented.csv`: Output with automatically labeled sentiment results.
- `Sentimented+Labelled.csv`: Merged dataset combining both automatic and manual sentiment labels.

## ⚙️ Requirements

### 📦 Python Libraries

Make sure the following libraries are installed:

```bash
pip install pandas numpy nltk textblob scikit-learn spacy matplotlib seaborn
python -m textblob.download_corpora
python -m nltk.downloader punkt wordnet stopwords averaged_perceptron_tagger
python -m spacy download en_core_web_sm
```

## 🧠 How It Works

### 1. **Data Loading**

The code loads Reddit posts/comments from `.csv` files.

### 2. **Text Preprocessing**

Performs:
- Lowercasing
- Tokenization
- Stopword removal
- Lemmatization

### 3. **Sentiment Analysis**

Uses **TextBlob** to calculate:
- Polarity
- Subjectivity  

And classifies sentiment into:
- `1` (Positive)
- `0` (Neutral)
- `-1` (Negative)

### 4. **Named Entity Recognition**

Uses **spaCy** to extract named entities from cleaned text.

### 5. **Clustering and Classification**

Performs clustering using KMeans to group similar sentiment patterns and evaluates using:
- Accuracy
- Precision
- Recall
- F1 Score

## 📊 Performance Metrics

During execution, the notebook tracks:
- Total processing time
- Records classified per second  

This helps assess scalability of the system.

Formula used:

\[
\text{Records per Second} = \frac{\text{Number of Records}}{\text{Total Processing Time (seconds)}}
\]

## 🚀 Running the Notebook

1. Open `Classification.ipynb` in **Jupyter Notebook** or **JupyterLab**.
2. Run each cell sequentially.
3. Results (including intermediate `.csv` files) will be saved locally.

## 👥 Manual Labelling

- 1,000 samples from a 10,000-record dataset were manually labelled.
- Three annotators reviewed the comments and their corresponding Reddit threads.
- Labels: `1` (positive), `0` (neutral), `-1` (negative)
- Inter-annotator agreement exceeded **80%**

## 📂 Output

- Sentiment-labeled datasets for further use.
- Merged evaluation-ready datasets with both manual and predicted labels.
- Performance reports on classification quality.

## 📬 Questions?

If you encounter any issues or have questions about how to use this notebook, feel free to raise them in the Issues tab (if using GitHub) or contact the project maintainer.
