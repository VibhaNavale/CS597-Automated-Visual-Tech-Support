import requests
import re

YOUTUBE_API_KEY = "AIzaSyA3LGzxBvhu6QT6cMrDkIo6vrSpgKbQPXg"  # Add your API key here

def clean_query(query):
    return re.sub(r'\W+', '_', query.strip())

def get_best_video(query, max_results=10, max_duration_seconds=120):
    search_url = "https://www.googleapis.com/youtube/v3/search"
    search_params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "key": YOUTUBE_API_KEY,
        "relevanceLanguage": "en",
        "order": "relevance",
        "videoDefinition": "high"
    }

    response = requests.get(search_url, params=search_params).json()
    if "error" in response:
        print(f"API Error: {response['error']['message']}")
        return None

    video_results = []
    video_ids = []

    for item in response.get("items", []):
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        video_ids.append(video_id)
        video_results.append({"id": video_id, "title": title, "url": video_url})

    if not video_ids:
        return None

    details_url = "https://www.googleapis.com/youtube/v3/videos"
    details_params = {
        "part": "contentDetails,statistics,snippet",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY
    }

    details_response = requests.get(details_url, params=details_params).json()

    valid_videos = []
    for item in details_response.get("items", []):
        duration_str = item["contentDetails"]["duration"]
        definition = item["contentDetails"].get("definition", "sd")

        hours = int(re.search(r'(\d+)H', duration_str).group(1)) if re.search(r'(\d+)H', duration_str) else 0
        minutes = int(re.search(r'(\d+)M', duration_str).group(1)) if re.search(r'(\d+)M', duration_str) else 0
        seconds = int(re.search(r'(\d+)S', duration_str).group(1)) if re.search(r'(\d+)S', duration_str) else 0

        total_seconds = hours * 3600 + minutes * 60 + seconds

        if total_seconds <= max_duration_seconds:
            for vr in video_results:
                if vr["id"] == item["id"]:
                    vr["duration_seconds"] = total_seconds
                    vr["views"] = int(item["statistics"].get("viewCount", 0))
                    vr["definition"] = definition
                    vr["description"] = item["snippet"].get("description", "")
                    valid_videos.append(vr)
                    break

    if not valid_videos:
        return None

    hd_videos = [v for v in valid_videos if v["definition"] == "hd"]

    if hd_videos:
        return max(hd_videos, key=lambda x: x["views"])
    return max(valid_videos, key=lambda x: x["views"])
