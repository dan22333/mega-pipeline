import os
import glob
from fastapi import APIRouter, File, Query
from starlette.responses import FileResponse
import uuid
import random
from google.cloud import storage
import openai
from api.pipeline import sync_file_ondemand

gcp_project = "ac215-project"
bucket_name = "mega-pipeline-bucket"
input_audios = "/persistent/input_audios"
text_prompts = "/persistent/text_prompts"
text_paragraphs = "/persistent/text_paragraphs"
text_audios = "/persistent/text_audios"
text_translated = "/persistent/text_translated"
output_audios = "/persistent/output_audios"


# Define Router
router = APIRouter()

# Routes


@router.post("/saveaudio")
async def saveaudio(file: bytes = File(...)):
    print("audio file:", len(file), type(file))

    # Save the file
    os.makedirs(input_audios, exist_ok=True)

    # Generate a unique id
    # file_id = uuid.uuid1()
    file_id = f"input-{random.randint(1,10):02d}"
    file_path = os.path.join(input_audios, str(file_id) + ".mp3")

    with open(file_path, "wb") as output:
        output.write(file)

    # Upload to bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    destination_blob_name = file_path.replace("/persistent/", "")
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(file_path)


@router.get("/input_audios")
async def get_input_audios():
    os.makedirs(input_audios, exist_ok=True)

    files = glob.glob(input_audios + "/*")
    files = sorted(files, key=lambda t: -os.stat(t).st_mtime)
    print(files)

    # Find all the other files in the pipeline
    results = []
    for file in files:
        uuid = os.path.basename(file).replace(".mp3", "")
        text_prompt = ""
        text_prompt_file = os.path.join(text_prompts, uuid + ".txt")
        if os.path.exists(text_prompt_file):
            with open(text_prompt_file) as f:
                text_prompt = f.read()

        text_paragraph = ""
        text_paragraph_file = os.path.join(text_paragraphs, uuid + ".txt")
        if os.path.exists(text_paragraph_file):
            with open(text_paragraph_file) as f:
                text_paragraph = f.read()

        text_translate = ""
        text_translate_file = os.path.join(text_translated, uuid + ".txt")
        if os.path.exists(text_translate_file):
            with open(text_translate_file) as f:
                text_translate = f.read()
        output_audio = ""
        output_audio_file = os.path.join(output_audios, uuid + ".mp3")
        if os.path.exists(output_audio_file):
            output_audio = output_audio_file

        text_audio = ""
        text_audio_file = os.path.join(text_audios, uuid + ".mp3")
        if os.path.exists(text_audio_file):
            text_audio = text_audio_file

        op = {
            "uuid": uuid,
            "input_audio": file,
            "text_prompt": text_prompt,
            "text_paragraph": text_paragraph,
            "text_audio": text_audio,
            "text_translate": text_translate,
            "output_audio": output_audio,
        }
        results.append(op)
    # results = [{"audio_path": file, "text": os.path.basename(
    #     file).replace(".mp3", "")} for file in files]

    return results


@router.get("/get_audio_data")
async def get_audio_data(path: str = Query(..., description="Audio path")):
    print(path)
    return FileResponse(path, media_type="audio/mp3")


@router.get("/sync_audio")
async def sync_audio():
    print("Deleting on demand")
    sync_file_ondemand()
    return {"done"}


@router.delete("/audio_data")
async def delete_audio_data(path: str = Query(..., description="Audio path")):
    print(path)

    storage_client = storage.Client(project=gcp_project)
    bucket = storage_client.bucket(bucket_name)

    file_id = os.path.basename(path).replace(".mp3", "")

    # Find blob in bucket and delete
    blob = bucket.blob("input_audios/" + file_id + ".mp3")
    blob.delete()
    os.remove(input_audios + "/" + file_id + ".mp3")
    blob = bucket.blob("text_prompts/" + file_id + ".txt")
    blob.delete()
    os.remove(text_prompts + "/" + file_id + ".txt")
    blob = bucket.blob("text_paragraphs/" + file_id + ".txt")
    blob.delete()
    os.remove(text_paragraphs + "/" + file_id + ".txt")
    blob = bucket.blob("text_translated/" + file_id + ".txt")
    blob.delete()
    os.remove(text_translated + "/" + file_id + ".txt")
    blob = bucket.blob("text_audios/" + file_id + ".mp3")
    blob.delete()
    os.remove(text_audios + "/" + file_id + ".mp3")
    blob = bucket.blob("output_audios/" + file_id + ".mp3")
    blob.delete()
    os.remove(output_audios + "/" + file_id + ".mp3")