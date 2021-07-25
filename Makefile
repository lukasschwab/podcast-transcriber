deploy-http: main.py requirements.txt .env.yaml
	gcloud functions deploy "deepgram-acw" --entry-point "http_main" --runtime "python37" --trigger-http --env-vars-file .env.yaml --max-instances 1

deploy-topic: main.py requirements.txt .env.yaml
	gcloud functions deploy "deepgram-acw-cron" --entry-point "topic_main" --runtime "python37" --trigger-topic weekly-cron-topic --env-vars-file .env.yaml --max-instances 1
