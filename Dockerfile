# 1. Grab the Python software
FROM python:3.9

# 2. Set up a folder for your app inside the server
WORKDIR /code

# 3. Copy the requirements file first (to make it faster)
COPY ./requirements.txt /code/requirements.txt

# 4. Install the libraries (FastAPI, Uvicorn, etc.)
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 5. Copy your actual code
COPY . .

# 6. Open the "door" (port 7860 is required by Hugging Face)
EXPOSE 7860

# 7. Start the app
# CRITICAL: Read the note below before saving!
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
