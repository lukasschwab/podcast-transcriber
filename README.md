# deepgram-acw

A set-it-and-forget-it GCP Cloud Function for transcribing a podcast, built for the [Arms Control Wonk Podcast](https://www.armscontrolwonk.com/) Slack community.

## Overview

[main.py](./main.py) defines a Cloud Function that

1. Waits on an invocation from a Pub/Sub topic;
2. Fetches a podcast's RSS or Atom feed of episodes;
3. Selects up to three most recent episodes for which it hasn't already produced transcripts;
4. Submits those podcast episodes to [Deepgram](https://deepgram.com/)'s automated speech recognition API for transcription;
5. Writes the Deepgram response and a processed transcript to Google Cloud Storage.

That cloud function is designed to be invoked on a regular schedule; the [setup instructions](#Setup) below and [Makefile](./Makefile) provide `cron`-like invocations by using Cloud Scheduler to publish to the Pub/Sub topic.

## Usage

### Requirements

+ `gsutil` and `gcloud`
+ Python 3.7
+ Deepgram account

### Setup

**Recommended:** start with an empty GCP project for the resources created here (a Cloud Storage bucket, Pub/Sub topic, Cloud Scheduler job, and Cloud Function). Run `gcloud config set project your-project-name` to point the Google Cloud SDK tools at that project.

1. Create a Google Cloud Storage bucket.

    Run `make bucket`.

2. Create `.env.yaml` file with required environment variables.

    `TARGET_FEED_URL`
    : The URL of a podcast's Atom/RSS feed, e.g. `"https://armscontrolwonk.libsyn.com/rss"`.

    `TRANSCRIPTIONS_BUCKET_NAME`
    : The name of the Google Cloud Storage bucket created in step 1.

    `DEEPGRAM_API_KEY`
    : Your personal Deepgram API key. This is a secret!

    <details><summary>Example .env.yaml file</summary>

    ```yaml
    # Configuration
    TARGET_FEED_URL: "https://armscontrolwonk.libsyn.com/rss"
    TRANSCRIPTIONS_BUCKET_NAME: "transcriptions"

    # Secrets
    DEEPGRAM_API_KEY: "your_deepgram_secret_here"
    ```

    </details>

3. Initialize the scheduling infrastructure (Pub/Sub topic and Cloud Scheduler job; [documentation](https://cloud.google.com/scheduler/docs/tut-pub-sub)).

    Run `make cron-job`.

4. Deploy the Cloud Function.

    Run `make deploy`.

To work through the backlog of episodes in the feed, repeatedly run the created job: `gcloud scheduler jobs run WeeklyJob`.

### Customization

#### Scheduling

Set up a transcription schedule appropriate to your podcast; these default settings are well-configured for a podcast with up to three episodes per week.

To check for updates more or less frequently, [change the Cloud Scheduler job frequency.](https://cloud.google.com/scheduler/docs/configuring/cron-job-schedules) Default: once per week.

To transcribe more or fewer episodes per function execution, change the threshold in [main.py#_main](./main.py). Default: up to 3 episodes.

#### Deepgram and transcripts

The Deepgram request in [main.py#_transcribe](./main.py) is tailored to the ACW podcast; if the speech in your podcast is faster or slower, you may want to decrease or increase the `utt_split` utterance threshold, respectively.

See [Deepgram's API documentation](https://developers.deepgram.com/api-reference/speech-recognition-api) and [Python SDK](https://github.com/deepgram/python-sdk) for a documentation of the available options.

Want transcripts in a different format? Change how [main.py#_process](./main.py) formats utterances.

<!--

## To do

+ Check Deepgram usage before transcribing
+ Explain how it knows which episodes have been transcribed, "haywire" scenarios
+ Discuss cost
+ Rename the repo something more generic
+ Add tests
+ Write out to GitHub repo

*Could* split out the deepgram-getting and the transcript-production into separate cloud functions chained together... but I don't see a really compelling reason to do so.

-->
