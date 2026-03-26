# Neural Network Text Classification Experiments

This directory contains scripts and configurations for training and evaluating neural network models for text classification tasks.

## Overview

The primary focus is on experimenting with different model architectures, embedding strategies, and techniques for handling specific challenges in natural language processing, such as Out-of-Vocabulary (OOV) words.

## Experiments

### 1. Out-of-Vocabulary (OOV) Handling Strategies

This set of experiments investigates the impact of different strategies for handling words encountered during inference or training that are not present in the pre-trained word embedding vocabulary.

*   **Goal:** Compare the performance of a GRU-based text classifier when using different OOV handling techniques.
*   **Dataset:** `johntoro/Reddit-Stock-Sentiment` (via Hugging Face `datasets`)
*   **Model:** GRU (Gated Recurrent Unit)
*   **Embeddings:** `glove-twitter-200` (Word2Vec)
*   **Tokenizer:** NLTK
*   **Strategies Compared:**
    *   `using_unk`: Replace OOV words with a dedicated `<UNK>` token embedding (trained from scratch or initialized randomly).
    *   `average`: Replace OOV words with the vector average of all known word embeddings in the vocabulary.
    *   `average_context`: Replace OOV words with the vector average of the known word embeddings present in the *current* input sequence (sentence/document).
*   **Configuration Files:** Located in `configs/oov_handling/`:
    *   `nltk_word2vec.json` (using\_unk)
    *   `nltk_word2vec_average.json` (average)
    *   `nltk_word2vec_average_context.json` (average\_context)
*   **Running the Experiments:** Execute the shell script:
    ```bash
    bash oov_handling.sh
    ```
    This script sequentially runs the `train.py` script with each of the configuration files mentioned above.
*   **Output:** Results, including metrics and model checkpoints, are saved in subdirectories under `experiments/oov_handing/`, corresponding to each strategy (e.g., `experiments/oov_handing/glove_gru_using_unk/`).

### 2. (Example) Model Architecture Variations

*(Note: Based on `summer.py`, experiments comparing different aggregation methods and layer depths for unidirectional and bidirectional LSTMs/GRUs might have been conducted previously or could be configured here.)*

This directory can also be used to run experiments comparing different model architectures, hyperparameters (like the number of layers), or aggregation strategies (e.g., using the last hidden state vs. mean/max pooling). The `summer.py` script provides an example of how results from such experiments could be visualized.

## Code Structure

*   `train.py`: The main script responsible for loading data, initializing the model and tokenizer based on a configuration file, running the training loop, and evaluating the model.
*   `configs/`: Contains JSON configuration files defining parameters for different experiments (model architecture, tokenizer, training arguments, data source, analysis settings).
*   `experiments/`: Default root directory where all experiment outputs (logs, metrics, checkpoints, visualizations) are saved. Specific subdirectories are typically created based on the `output_dir` specified in the configuration file.
*   `oov_handling.sh`: A convenience script to run the series of OOV handling experiments.
*   `summer.py`: An example script for plotting and visualizing experiment results (currently configured for aggregation method comparison).
*   *(Other potential files: `model.py`, `tokenizer.py`, `dataset.py`, `utils.py`)*

## How to Run a Single Experiment

To run a specific experiment configuration:

```bash
python -m Classification.NeuralNets.train --config <path_to_your_config.json>
```

## How to Run All Experiments

```bash
bash oov_handling.sh
```

This will execute the `train.py` script with each of the configuration files located in `configs/oov_handling/`.


## Dependencies

Ensure you have the necessary libraries installed. Key dependencies likely include:

*   PyTorch
*   NLTK
*   Hugging Face `datasets`
*   Hugging Face `transformers` (if using transformer-based tokenizers/models)
*   NumPy
*   Matplotlib (for visualization like in `summer.py`)
*   Scikit-learn (for metrics)

