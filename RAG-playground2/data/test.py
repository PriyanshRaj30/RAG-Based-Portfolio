import os
from dotenv import load_dotenv

load_dotenv()  # This loads the .env file into os.environ

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# print(f"GROK API KEY {GROQ_API_KEY}")
GROQ_BASE = os.getenv("GROQ_BASE")
# print(f"GROK BASE {GROQ_BASE}")

GROQ_BASE = os.getenv("GROQ_BASE")

# Groq chat models: higher quality for answering
GROQ_ANSWER_MODEL = os.getenv("GROQ_ANSWER_MODEL")

# Local sentence-transformers model for embeddings
EMBED_MODEL_NAME = os.getenv("EMBED_MODEL_NAME")

print(f"GROQ_API_KEY : {GROQ_API_KEY} \n GROQ_BASE: {GROQ_BASE} \n GROQ_ANSWER_MODEL: {GROQ_ANSWER_MODEL} \n EMBED_MODEL_NAME: {EMBED_MODEL_NAME}")
