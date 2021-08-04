cloud_fn_config := --runtime "python37" --trigger-topic weekly-cron-topic --env-vars-file .env.yaml --max-instances 1 --timeout=480s

# Deploy targets

deploy: main.py requirements.txt .env.yaml
	gcloud pubsub topics describe weekly-cron-topic
	gcloud functions deploy "podcast-transcriber-cron" \
		--entry-point "topic_main" \
		$(cloud_fn_config)

deploy-http: main.py requirements.txt .env.yaml
	gcloud functions deploy "podcast-transcriber" \
		--entry-point "http_main" \
		$(cloud_fn_config)

# One-time infra initialization targets

cron-job: cron-topic
	gcloud scheduler jobs create pubsub WeeklyJob \
		--schedule="0 9 * * 1" \
		--topic="weekly-cron-topic" \
		--message-body="" \
		--attributes="src=WeeklyJob"

cron-topic:
	gcloud pubsub topics create weekly-cron-topic

bucket:
	gsutil mb gs://transcriptions

# Dev targets

lint: main.py
	flake8 . --count --max-complexity=10 --statistics
