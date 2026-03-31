from django.db import models

# class RedditOpinion(models.Model):
#     # Foreign key/Topic info
#     topic = models.CharField(max_length=255) #[cite: 6]
#     record_type = models.CharField(max_length=50) # e.g., 'comment'
    
#     # IDs from Reddit
#     post_id = models.CharField(max_length=50)
#     record_id = models.CharField(max_length=100, unique=True)
    
#     # Text Data
#     text_raw = models.TextField() #[cite: 26]
#     text_clean = models.TextField() # Preprocessed for IR 
    
#     # Sentiment Analysis Fields (Subtasks)
#     subjectivity = models.IntegerField() # Neutral (0) vs Opinionated (1) [cite: 89, 90]
#     polarity = models.IntegerField() # Positive (1) vs Negative (-1) [cite: 90]
    
#     # Model Metadata (HuggingFace/Gemini)
#     hf_label = models.CharField(max_length=10)
#     hf_score = models.FloatField()
#     final_class = models.CharField(max_length=20) # e.g., 'Positive' [cite: 6]
    
#     # Ranking and Confidence
#     rank_score = models.FloatField() # [cite: 71]
#     rank_abs_conf = models.FloatField()
#     rank = models.IntegerField()

#     def __str__(self):
#         return f"{self.topic} - {self.final_class}"
