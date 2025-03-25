from langchain_community.document_loaders import YoutubeLoader

loader = YoutubeLoader.from_youtube_url(
    "https://www.youtube.com/watch?v=QsYGlZkevEg", add_video_info=False, language=["en"]
)
x = loader.load()
print(x)
