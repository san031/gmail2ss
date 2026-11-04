FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

# /app is the cwd, so jobs.xlsx (sheet.DEFAULT_PATH) and logs/ land here
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

EXPOSE 8501

# Streamlit app imports `sheet` / `summary`, which sit next to app.py
CMD ["streamlit", "run", "src/tracker/app.py", \
     "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
