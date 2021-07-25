from google.cloud import storage
import logging
import os
import asyncio
import json

import feedparser
from deepgram import Deepgram

logging.info("Starting deepgram-acw")

# Keys for required environment variables; should match keys in .env.yaml.
ENV_TARGET_FEED_URL = 'TARGET_FEED_URL'
ENV_TRANSCRIPTIONS_BUCKET_NAME = 'TRANSCRIPTIONS_BUCKET_NAME'
ENV_DEEPGRAM_API_KEY = 'DEEPGRAM_API_KEY'


def __get_env(name):
    """
    __get_env is a helper for getting required environment variables. Set
    missing environment variables in an .env.yaml file:
    https://cloud.google.com/functions/docs/configuring/env-var
    """
    value = os.getenv(name)
    if not value:
        raise EnvironmentError('Environment missing required variable: {}'.format(name))
    return value


# Initialize Storage client for writing to transcriptions bucket.
storage_client = storage.Client()
transcriptions_bucket = storage_client.bucket(__get_env(ENV_TRANSCRIPTIONS_BUCKET_NAME))

# Initialize Deepgram client.
deepgram_client = Deepgram(__get_env(ENV_DEEPGRAM_API_KEY))

# Retrieve URL for feed to transcribe.
target_feed_url = __get_env(ENV_TARGET_FEED_URL)


def _main():
    """
    _main parses the target feed and processes up to three new entries.
    """
    logging.info("Processing feed: {}".format(target_feed_url))
    feed = feedparser.parse(target_feed_url)
    # Skip entries that have already been transcribed.
    processed = __existing_blobs()
    unprocessed = [entry for entry in feed.entries if __should_process(processed, entry)]
    # Limit to transcribing three feed entries: prevent the function from going
    # haywire if all feed IDs change at once.
    num_unprocessed = len(unprocessed)
    if num_unprocessed > 3:
        logging.warning("{} unprocessed entries; processing first 3".format(num_unprocessed))
        unprocessed = unprocessed[:3]

    logging.info("Processing {} new entries".format(len(unprocessed)))
    for entry in unprocessed:
        _process(entry)


def __existing_blobs():
    """
    __existing_blobs returns the set of *.txt transcriptions in the
    transcriptions bucket.
    """
    all_blobs = list(storage_client.list_blobs(transcriptions_bucket))
    logging.info("Listed {} existing blobs".format(len(all_blobs)))
    return set([b.name for b in all_blobs if ".txt" in b.name])


def __should_process(processed, entry):
    """
    __should_process returns True iff the name of the transcript that would be
    produced for entry does not correspond to a name in processed.
    """
    return __transcript_blob_name(entry) not in processed


def __transcript_blob_name(entry):
    """
    __transcript_blob_name constructs the name of the transcript text blob that
    would be produced for entry.
    """
    return entry.link + ".txt"


def _process(entry):
    """
    _process gets a transcription for entry, then
    """
    logging.info("Processing entry {}: {}".format(entry.id, entry.link))
    response = _transcribe(entry)
    # Write transcript to GCS
    transcript_blob_name = __transcript_blob_name(entry)
    transcript_blob = transcriptions_bucket.blob(transcript_blob_name)
    with transcript_blob.open('wt') as f:
        for u in response['results']['utterances']:
            f.write("{}\t{}\n".format(u['speaker'], u['transcript']))
    logging.info("Wrote transcript to {}".format(transcript_blob_name))


def _transcribe(entry: feedparser.FeedParserDict):
    """
    _transcribe hands entry's audio enclosure to the Deepgram API and writes the
    full JSON-encoded response to the transcriptions bucket before returning it.
    """
    audio_enclosures = [e for e in entry.enclosures if e.type == "audio/mpeg"]
    if len(audio_enclosures) != 1:
        logging.warning("Entry {} has {} audio enclosures; skipping".format(
            entry.id,
            len(audio_enclosures)
        ))
        return
    enclosure = audio_enclosures.pop()
    response = asyncio.run(deepgram_client.transcription.prerecorded(
        {"url": enclosure.href},
        {
            "punctuate": True,
            "utterances": True,
            "diarize": True,
            "utt_split": 2,
        }
    ))
    # Write response JSON to GCS
    logging.info("Got response: {}".format(response['metadata']))
    json_blob_name = entry.link + ".json"
    transcriptions_bucket.blob(json_blob_name).upload_from_string(
        json.dumps(response),
        content_type="application/json"
    )
    logging.info("Wrote JSON response to {}".format(json_blob_name))
    return response


def http_main(request):
    """
    http_main is a thin wrapper around main for use as a http-triggered Cloud
    Function entry point.
    """
    _main()


def topic_main(event, context):
    """
    topic_main is a thin wrapper around main for use as a Pub/Sub-triggered
    Cloud Function entry point.
    """
    _main()
