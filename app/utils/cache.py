import os
import json
import hashlib
import re
from urllib.parse import urlparse, parse_qs

def extract_video_id(video_url):
    try:
        parsed_url = urlparse(video_url)
        if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
            query_params = parse_qs(parsed_url.query)
            return query_params.get('v', [None])[0]
        elif parsed_url.hostname == 'youtu.be':
            return parsed_url.path[1:]
    except Exception:
        pass
    
    return hashlib.md5(video_url.encode()).hexdigest()[:12]

def get_cached_video_result(video_id):
    cache_file = f"output/video_cache/{video_id}.json"
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    return None

def cache_video_result(video_id, result):
    os.makedirs("output/video_cache", exist_ok=True)
    cache_file = f"output/video_cache/{video_id}.json"
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(result, f, indent=2)
        return True
    except Exception as e:
        return False

def is_video_cached(video_id):
    cache_file = f"output/video_cache/{video_id}.json"
    return os.path.exists(cache_file)