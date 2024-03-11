docker build -t dsp-reports .
docker run --env-file .env -v ./:/app/output dsp-reports


Required environment settings for the .env file

```bash
MONGO_USERNAME=
MONGO_PASSWORD=
MONGO_HOST=
MONGO_DATABASE=
MONGO_PROTOCOL=
```
