from google.cloud import storage
import logging
import os
import asyncio
import json

import feedparser
from deepgram import Deepgram

PODCAST_FEED = "https://armscontrolwonk.libsyn.com/rss"
TRANSCRIPTIONS_BUCKET = "acw-transcriptions"

logging.info("Starting deepgram-acw")

storage_client = storage.Client()
bucket = storage_client.bucket(TRANSCRIPTIONS_BUCKET)

deepgram_key = os.getenv('DEEPGRAM_API_KEY')
if not deepgram_key:
    raise EnvironmentError("Missing deepgram API key")
deepgram_client = Deepgram(deepgram_key)

def main(request):
    logging.info("Processing feed: {}".format(PODCAST_FEED))
    feed = feedparser.parse(PODCAST_FEED)

    processed = existing_blobs()
    unprocessed = [entry for entry in feed.entries if should_process(processed, entry)]

    num_unprocessed = len(unprocessed)
    if num_unprocessed > 3:
        logging.warning("{} unprocessed entries; processing first 3".format(num_unprocessed))
        unprocessed = unprocessed[:3]

    logging.info("Processing {} new entries".format(len(unprocessed)))
    for entry in unprocessed:
        process(entry)

def existing_blobs():
    all_blobs = list(storage_client.list_blobs(bucket))
    logging.info("Listed {} existing blobs".format(len(all_blobs)))
    return set([b.name for b in all_blobs if ".txt" in b.name])

def should_process(processed, entry):
    return to_transcript_blob_name(entry) not in processed

def to_transcript_blob_name(entry):
    return entry.link + ".txt"

def process(entry):
    logging.info("Processing entry {}: {}".format(entry.id, entry.link))
    response = transcribe(entry)
    # Write transcript to GCS
    transcript_blob_name = to_transcript_blob_name(entry)
    transcript_blob = bucket.blob(transcript_blob_name)
    with transcript_blob.open('wt') as f:
        for u in response['results']['utterances']:
            f.write("{}\t{}\n".format(u['speaker'], u['transcript']))
    logging.info("Wrote transcript to {}".format(transcript_blob_name))

def transcribe(entry):
    audio_enclosures = [e for e in entry.enclosures if e.type == "audio/mpeg"]
    if len(audio_enclosures) != 1:
        logging.warning("Entry {} has {} audio enclosures; skipping".format(
            entry.id,
            len(audio_enclosures)
        ))
        return
    enclosure = audio_enclosures.pop()
    source = { "url": enclosure.href }
    response = asyncio.run(deepgram_client.transcription.prerecorded(source, {
        "punctuate": True,
        "utterances": True,
        "diarize": True
    }))
    # Write response JSON to GCS
    logging.info("Got response: {}".format(response['metadata']))
    json_blob_name = entry.link + ".json"
    bucket.blob(json_blob_name).upload_from_string(
        json.dumps(response),
        content_type="application/json"
    )
    logging.info("Wrote JSON response to {}".format(json_blob_name))
    return response
