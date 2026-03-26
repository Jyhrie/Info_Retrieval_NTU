import json
import argparse
from functools import partial
from typing import Dict

from datasets import load_dataset

import torch
from torch.utils.data import DataLoader
from torch.nn.utils.rnn import pad_sequence

from NeuralNets.utils.tokenizer import build_tokenizer, BaseTokenizer
from NeuralNets.models import build_model
from NeuralNets.trainer import TrainingArgs

SUPPORTED_TASKS = ["classification"]

class ClassificationDatasetFromList(torch.utils.data.Dataset):
  def __init__(self, input_list, tokenizer, type=None):
    self.dataset_type = type
    self.input_list = input_list
    self.tokenizer = tokenizer
  
  def __len__(self):
    return len(self.input_list)
  
  def __getitem__(self, idx):
    text = self.input_list[idx]
    ids = self.tokenizer.tokenize(text)["ids"]
    length = len(ids)
    ids = torch.tensor(ids)
    return ids, length

  def count(self, idx):
    item = self.dataset[idx]
    text = item["text"]
    res = self.tokenizer.tokenize(text)
    ids = res["ids"]
    tokens = res["tokens"]
    length = len(ids)
    n_unks = sum([1 for i in ids if i == self.tokenizer.unk_id])
    return n_unks, length

class ClassificationDataset(torch.utils.data.Dataset):
  def __init__(self, dataset, tokenizer, type=None):
    self.dataset_type = type
    self.dataset = dataset
    self.tokenizer = tokenizer
  
  def __len__(self):
    return len(self.dataset)
  
  def __getitem__(self, idx):
    item = self.dataset[idx]
    text = item["text"]
    if self.dataset_type == "neutral_sentiment":
      label = int(item["label"] + 1) # -1, 0, 1 -> 0, 1, 2 Neutral, Positive, Negative
    else:
      label = item["label"] # normal
    ids = self.tokenizer.tokenize(text)["ids"]
    length = len(ids)
    ids = torch.tensor(ids)
    return ids, length, label

  def count(self, idx):
    item = self.dataset[idx]
    text = item["text"]
    res = self.tokenizer.tokenize(text)
    ids = res["ids"]
    tokens = res["tokens"]
    length = len(ids)
    n_unks = sum([1 for i in ids if i == self.tokenizer.unk_id])
    return n_unks, length
  

def get_dataloaders_from_list(
  input_list: list[str],
  bs: int,
  tokenizer: BaseTokenizer,
  dataset_args: Dict,
  training_args: TrainingArgs
):
  assert training_args.task in SUPPORTED_TASKS, f"Task {training_args.task} not supported"
  assert hasattr(training_args, "training_batch_size"), "Batch size not found in training args"
  assert "is_huggingface" in dataset_args, "is_huggingface not found in dataset args"
  assert "name" in dataset_args, "Dataset name not found in dataset args"
  
  if training_args.task == "classification":
    print("Tokenizer unk id:",tokenizer.unk_id)
    infer_dataset = ClassificationDatasetFromList(input_list, tokenizer)
    
    def padding_fn(batch):
      (xx, lengths) = zip(*batch)
      xx_pad = pad_sequence(xx, batch_first=True, padding_value=tokenizer.pad_id)
      return xx_pad, torch.tensor(lengths)
    
    infer_loader = DataLoader(infer_dataset, batch_size=bs, shuffle=True, collate_fn=padding_fn)
  else:
    raise NotImplementedError(f"Task {training_args.task} not implemented")
  
  return infer_loader

def get_dataloaders(
  tokenizer: BaseTokenizer,
  dataset_args: Dict,
  training_args: TrainingArgs
):
  assert training_args.task in SUPPORTED_TASKS, f"Task {training_args.task} not supported"
  assert hasattr(training_args, "training_batch_size"), "Batch size not found in training args"
  assert "is_huggingface" in dataset_args, "is_huggingface not found in dataset args"
  assert "name" in dataset_args, "Dataset name not found in dataset args"
  
  training_bs = training_args.training_batch_size
  val_bs = training_args.validation_batch_size
  if dataset_args["is_huggingface"]:
    dataset = load_dataset(dataset_args["name"])
  else:
    assert "path" in dataset_args, "Path not found in dataset args"
    dataset = load_dataset(dataset_args["path"])
  
  if training_args.task == "classification":
    print("Tokenizer unk id:",tokenizer.unk_id)
    if dataset_args["name"] == "johntoro/Reddit-Stock-Sentiment": # old version
      train_dataset = ClassificationDataset(dataset["train"], tokenizer, type="neutral_sentiment")
      validation_dataset = ClassificationDataset(dataset["validation"], tokenizer, type="neutral_sentiment")
    else:
      train_dataset = ClassificationDataset(dataset["train"], tokenizer)
      validation_dataset = ClassificationDataset(dataset["validation"], tokenizer)
    # test_dataset = ClassificationDataset(dataset["test"], tokenizer)
    
    n_unks, n_total = 0, 0
    for i in range(len(train_dataset)):
      n_unks_i, n_total_i = train_dataset.count(i)
      n_unks += n_unks_i
      n_total += n_total_i
    print(f"Train set: {n_unks} UNKs out of {n_total} tokens")
    
    n_unks, n_total = 0, 0
    for i in range(len(validation_dataset)):
      n_unks_i, n_total_i = validation_dataset.count(i)
      n_unks += n_unks_i
      n_total += n_total_i
    print(f"Validation set: {n_unks} UNKs out of {n_total} tokens")
    
    n_unks, n_total = 0, 0
    # for i in range(len(test_dataset)):
    #   n_unks_i, n_total_i = test_dataset.count(i)
    #   n_unks += n_unks_i
    #   n_total += n_total_i
    # print(f"Test set: {n_unks} UNKs out of {n_total} tokens")
    # partial function to be used in DataLoader
    def padding_fn(batch):
      (xx, lengths, yy) = zip(*batch)
      xx_pad = pad_sequence(xx, batch_first=True, padding_value=tokenizer.pad_id)
      return xx_pad, torch.tensor(lengths), torch.tensor(yy)
    
    train_loader = DataLoader(train_dataset, batch_size=training_bs, shuffle=True, collate_fn=padding_fn)
    val_loader   = DataLoader(validation_dataset, batch_size=val_bs, shuffle=True, collate_fn=padding_fn)
    # test_loader  = DataLoader(test_dataset, batch_size=val_bs, shuffle=True, collate_fn=padding_fn)
  else:
    raise NotImplementedError(f"Task {training_args.task} not implemented")
  
  return train_loader, val_loader

if __name__ == "__main__":
  argparser = argparse.ArgumentParser()
  argparser.add_argument("--config", type=str, required=True)
  args = argparser.parse_args()
  print("Config file: ", args.config)
  config = json.load(open(args.config))
  print(config)
  
  training_args = TrainingArgs(
    **config["trainer_args"]
  )
  model = build_model(config["model_config"])
  tokenizer = build_tokenizer(config["tokenizer_config"])
  train_loader, val_loader = get_dataloaders(
    tokenizer=tokenizer, 
    dataset_args=config["data_config"], 
    training_args=training_args
  )