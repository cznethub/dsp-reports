FROM python:3.10-slim

WORKDIR /app

COPY models.py models.py
COPY requirements.txt requirements.txt
COPY settings.py settings.py
COPY submissions_report.py submissions_report.py

RUN pip install -r requirements.txt

CMD ["python", "submissions_report.py"]
