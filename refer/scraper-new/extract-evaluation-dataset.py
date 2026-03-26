import pandas as pd
import numpy as np

np.random.seed(8888)


try:
    df = pd.read_csv('results.csv')
    total_records = len(df)
    
    print(f"Total records in file: {total_records}")
    sample_size = min(1000, total_records)
    sampled_df = df.sample(n=sample_size, random_state=8888)
    sampled_df.to_csv('evaluation_dataset_1000.csv', index=False)
    print(f"Successfully extracted {sample_size} records to evaluation_dataset_1000.csv")
    
except Exception as e:
    print(f"Error occurred: {e}")