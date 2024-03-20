FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY dsp_reports dsp_reports
ENV PYTHONPATH "${PYTHONPATH}:/app/dsp_reports"

CMD ["python", "dsp_reports/main.py"]
