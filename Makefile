
deploy: main.py requirements.txt .env.yaml
	gcloud functions deploy "deepgram-acw" --entry-point "main" --runtime "python37" --trigger-http --env-vars-file .env.yaml --max-instances 1
