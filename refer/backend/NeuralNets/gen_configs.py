import os
import json
from itertools import product

base_config = {
    "model_config": {
        "model_type": "BiGRU",
        "args": {
            "dim_input": 300,
            "dim_hidden": 256,
            "num_layers": 1,
            "dim_output": 2,
            "embedding_strategy": "word2vec",
            "pretrained_path": "word2vec-google-news-300",
            "embedding_frozen": False,
            "context_window": 5,
            "oov_handing": "average_context"
        }
    },
    "tokenizer_config": {
        "tokenizer_type": "nltk",
        "args": {
            "dataset": "rotten_tomatoes"
        }
    },
    "trainer_args": {
        "task": "classification",
        "training_batch_size": 64,
        "validation_batch_size": 64,
        "learning_rate": 0.0005,
        "epoch": 20
    },
    "metric_config": {
        "metrics": [
            {"name": "accuracy", "args": {}},
            {"name": "f1", "args": {}},
            {"name": "precision", "args": {}},
            {"name": "recall", "args": {}}
        ]
    },
    "data_config": {
        "name": "rotten_tomatoes",
        "is_huggingface": True,
        "type": "classification"
    },
    "analysis_config": {
        "output_dir": "experiments/n_layers/bigru_layer=1",
        "record_metrics": True,
        "record_gradients": True,
        "save_interval": 1000
    }
}

embedding_strategies = [
    ("glove-twitter-25", 20, 25),
    ("glove-twitter-100", 128, 100),
    ("glove-twitter-200", 128, 200),
    ("word2vec-google-news-300", 256, 300)
]

oov_handlings = ['using_unk', 'closest_word']
architectures = ['DeepRNN', 'GRU', 'LSTM', 'BiGRU', 'BiLSTM', 'BiDeepRNN']

num_layers_list = [1]

exp_name = "oov_training_handling"
config_dir = f'./configs/{exp_name}'

os.makedirs(config_dir, exist_ok=True)

shell_script_lines = []

for oov, (embedding_strategy, hidden_size, dim_input), architecture, num_layers in product(oov_handlings, embedding_strategies, architectures, num_layers_list):
    config = json.loads(json.dumps(base_config))
    
    config['model_config']['model_type'] = architecture
    config['model_config']['args']['dim_input'] = dim_input
    config['model_config']['args']['num_layers'] = num_layers
    config['model_config']['args']['dim_hidden'] = hidden_size
    config['model_config']['args']['pretrained_path'] = embedding_strategy
    config['model_config']['args']['oov_handing'] = oov
    
    output_dir = f"experiments/{exp_name}/{architecture}_oov={oov}_embedding={embedding_strategy}"
    config['analysis_config']['output_dir'] = output_dir
    
    config_filename = f"{architecture}_oov={oov}_embedding={embedding_strategy}.json"
    config_filepath = os.path.join(config_dir, config_filename)
    
    with open(config_filepath, 'w') as f:
        json.dump(config, f, indent=4)
    
    shell_script_lines.append(f"python train.py --config {config_filepath}")
    
shell_script_content = '\n'.join(shell_script_lines)
shell_script_path = f'{exp_name}.sh'

with open(shell_script_path, 'w') as f:
    f.write(shell_script_content)

# os.chmod(shell_script_path, 0o755)

print(f"Generated {len(shell_script_lines)} configurations.")
print(f"Configurations are saved in {config_dir}")
print(f"Shell script to run all configurations is saved as {shell_script_path}")
