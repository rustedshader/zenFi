# Init the GoogleApiClient
from pathlib import Path

from langchain_community.document_loaders import GoogleApiClient, GoogleApiYoutubeLoader

google_api_client = GoogleApiClient(
    credentials_path=Path(
        "/Users/shubhang/Downloads/client_secret_171308141191-1dk6ptf6491sbqql66jsir5pqth2i613.apps.googleusercontent.com.json"
    )
)


youtube_loader_video = GoogleApiYoutubeLoader(
    google_api_client=google_api_client,
    video_ids=[""],
    add_video_info=True,
    continue_on_failure=True,
    captions_language="en",
)

x = youtube_loader_video.load()
print(x)
