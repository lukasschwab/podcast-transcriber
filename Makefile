cloud_fn_config := --runtime "python37" --trigger-topic weekly-cron-topic --env-vars-file .env.yaml --max-instances 1 --timeout=480s

# Deploy targets

deploy-topic: main.py requirements.txt .env.yaml
	gcloud pubsub topics describe weekly-cron-topic
	gcloud functions deploy "deepgram-acw-cron" \
		--entry-point "topic_main" \
		$(cloud_fn_config)

deploy-http: main.py requirements.txt .env.yaml
	gcloud functions deploy "deepgram-acw" \
		--entry-point "http_main" \
		$(cloud_fn_config)

# One-time infra initialization targets

cron_job: cron_topic
	gcloud scheduler jobs create pubsub WeeklyJob \
		--schedule="0 9 * * 1" \
		--topic="weekly-cron-topic" \
		--message-body="" \
		--attributes="src=WeeklyJob"

cron_topic:
	gcloud pubsub topics create weekly-cron-topic

# Dev targets

lint: main.py
	flake8 . --count --max-complexity=10 --statistics