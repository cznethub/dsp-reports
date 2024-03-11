docker build -t dsp-reports .
docker run --env-file .env -v ./:/app/output dsp-reports
