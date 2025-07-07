FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV DISCORD_TOKEN=REPLACE_IN_STACK
ENV GITHUB_TOKEN=REPLACE_IN_STACK

CMD ["python", "ghetto_gpt_main.py"]
