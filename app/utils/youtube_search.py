import requests
import re
from datetime import datetime

YOUTUBE_API_KEY = "" # Add your API Key here

ACTION_TERMS = {
    "change", "reset", "cancel", "enable", "disable", "update",
    "set", "setup", "pair", "connect", "download", "install",
    "share", "schedule", "delete", "remove", "turn", "add",
    "edit", "manage", "recover", "restore"
}

BRAND_TERMS = {
    "amazon", "lyft", "uber", "facebook", "whatsapp", "instagram",
    "gmail", "google", "apple", "samsung", "siri", "spotify",
    "zoom", "tiktok", "paypal", "venmo", "roku", "alexa", "echo", 
    "youtube", "prime", "outlook", "teams", "messenger", "snapchat", "netflix"
}

CRITICAL_TOPIC_TERMS = {
    "address", "password", "email", "account", "profile", "contacts",
    "messages", "ride", "rides", "schedule", "appointment",
    "subscription", "wifi", "bluetooth", "volume", "accessibility",
    "photos", "videos", "storage", "payment", "payments",
    "notification", "notifications", "voice", "font", "text", "texts",
    "number", "calendar", "reminder", "reminders", "font size", "brightness"
}

def clean_query(query):
    return re.sub(r'\W+', '_', query.strip())

def get_duration_rank(duration):
    if 15 <= duration < 30:
        return 1
    elif 30 <= duration < 45:
        return 2
    elif 45 <= duration < 60:
        return 3
    elif 60 <= duration < 90:
        return 4
    elif 90 <= duration <= 120:
        return 5
    elif duration < 15:
        return 6
    else:
        return 999

def has_tutorial_indicators(title, description):
    tutorial_terms = [
        "how to", "tutorial", "guide", "step by step", "walkthrough",
        "instructions", "help", "demo", "example", "settings",
        "enable", "disable", "turn on", "turn off", "change", "setup",
        "connect", "pair", "configure"
    ]
    
    title_lower = title.lower()
    desc_lower = description.lower()
    
    count = 0
    for term in tutorial_terms:
        if term in title_lower:
            count += 2
        if term in desc_lower:
            count += 1
    
    return count > 0, count

def has_query_in_description(query, description):
    query_lower = query.lower()
    desc_lower = description.lower()
    
    if query_lower in desc_lower:
        return True, 2
    
    query_words = [w for w in query_lower.split() if len(w) > 2]
    matches = sum(1 for word in query_words if word in desc_lower)
    
    if matches >= len(query_words) * 0.5:
        return True, 1
    
    return False, 0

def build_keyword_profile(query_key_words):
    unique_keywords = list(dict.fromkeys(query_key_words))
    weights = {}
    priority_tokens = set()
    total_weight = 0.0
    for word in unique_keywords:
        weight = 1.0
        if len(word) >= 8:
            weight += 0.2
        if word in ACTION_TERMS:
            weight += 0.5
        if word in BRAND_TERMS:
            weight += 0.8
        if word in CRITICAL_TOPIC_TERMS:
            weight += 0.7
            priority_tokens.add(word)
        elif word in ACTION_TERMS:
            priority_tokens.add(word)
        weights[word] = weight
        total_weight += weight
    priority_weight_total = sum(weights[w] for w in priority_tokens) if priority_tokens else 0.0
    return {
        "weights": weights,
        "total_weight": total_weight,
        "priority_tokens": priority_tokens,
        "priority_weight_total": priority_weight_total
    }

def compute_keyword_metrics(query_lower, query_key_words, keyword_profile, title, description, stop_words):
    title_lower = title.lower()
    title_words_clean = re.sub(r'[^\w\s]', '', title_lower).split()
    title_keywords = [w for w in title_words_clean if w not in stop_words and len(w) > 1]

    description = description or ""
    content_text = f"{title_lower} {description.lower()}"
    content_words_clean = re.sub(r'[^\w\s]', '', content_text).split()
    content_keywords = [w for w in content_words_clean if w not in stop_words and len(w) > 1]
    content_keyword_set = set(content_keywords)

    matching_keywords = [w for w in query_key_words if w in content_keyword_set]
    matching_keyword_count = len(matching_keywords)

    if query_key_words:
        base_ratio = matching_keyword_count / len(query_key_words)
    else:
        base_ratio = 0.0

    if title_keywords:
        title_coverage = matching_keyword_count / len(title_keywords)
        combined_ratio = (base_ratio + title_coverage) / 2 if (base_ratio or title_coverage) else 0.0
        keyword_match_ratio = max(base_ratio, combined_ratio)
    else:
        keyword_match_ratio = base_ratio

    query_clean = re.sub(r'[^\w\s]', '', query_lower)
    has_exact_match = query_clean in title_lower if query_clean else False

    has_desc_match, desc_score = has_query_in_description(query_lower, description)

    weights = keyword_profile.get("weights", {})
    total_weight = keyword_profile.get("total_weight", 0.0)
    priority_tokens = keyword_profile.get("priority_tokens", set())
    priority_weight_total = keyword_profile.get("priority_weight_total", 0.0)

    matched_weight = sum(weights.get(w, 0.0) for w in content_keyword_set if w in weights)
    weighted_keyword_ratio = matched_weight / total_weight if total_weight else base_ratio

    priority_matched_weight = sum(weights.get(w, 0.0) for w in content_keyword_set if w in priority_tokens)
    if priority_weight_total > 0:
        priority_keyword_coverage = priority_matched_weight / priority_weight_total
    else:
        priority_keyword_coverage = 1.0

    brand_hits = sum(1 for w in query_key_words if w in BRAND_TERMS and w in content_keyword_set)

    combined_relevance = (
        weighted_keyword_ratio * 4.0
        + keyword_match_ratio * 1.5
        + priority_keyword_coverage * 3.0
        + (1.5 if has_exact_match else 0.0)
        + desc_score
        + (brand_hits * 0.75)
        + matching_keyword_count * 0.5
    )

    return {
        "keyword_match_ratio": keyword_match_ratio,
        "key_word_match_ratio": keyword_match_ratio,  # legacy field name for existing consumers
        "matching_keyword_count": matching_keyword_count,
        "title_keyword_count": len(title_keywords),
        "has_exact_match": has_exact_match,
        "has_description_match": has_desc_match,
        "description_match_score": desc_score,
        "brand_hits": brand_hits,
        "combined_relevance_score": combined_relevance,
        "weighted_keyword_ratio": weighted_keyword_ratio,
        "priority_keyword_coverage": priority_keyword_coverage,
        "has_any_keyword_signal": (matching_keyword_count > 0) or has_desc_match or has_exact_match
    }

def create_search_queries(original_query):
    query_lower = original_query.lower()
    queries = []
    
    queries.append(original_query)
    
    if 'how to' not in query_lower:
        queries.append(f"how to {original_query}")
    
    queries.append(f"{original_query} tutorial")
    queries.append(f"{original_query} guide")
    queries.append(f"{original_query} step by step")
    queries.append(f"{original_query} walkthrough")
    
    augmented_queries = []
    for q in queries:
        augmented_queries.append(q)
        if "phone" not in q.lower():
            augmented_queries.append(f"{q} on my phone")
    queries = augmented_queries

    if "phone" not in query_lower:
        queries.append(f"{original_query} phone")
        queries.append(f"{original_query} on phone")

    seen = set()
    unique_queries = []
    for q in queries:
        if q.lower() not in seen:
            seen.add(q.lower())
            unique_queries.append(q)
    
    return unique_queries[:8]

def get_best_video(query, max_results=30, max_duration_seconds=120, min_duration_seconds=20):
    search_queries = create_search_queries(query)
    all_videos = []
    
    for search_query in search_queries:
        search_url = "https://www.googleapis.com/youtube/v3/search"
        search_params = {
            "part": "snippet",
            "q": search_query,
            "type": "video",
            "maxResults": max(10, max_results // len(search_queries) + 5),
            "key": YOUTUBE_API_KEY,
            "relevanceLanguage": "en",
            "order": "relevance",
            "videoDefinition": "high",
            "videoCategoryId": "28",
            "safeSearch": "moderate"
        }

        try:
            response = requests.get(search_url, params=search_params).json()
            if "error" in response:
                error_info = response.get("error", {})
                print(f"YouTube API Error: {error_info}")
                continue
        except Exception as e:
            print(f"YouTube Search API request failed: {str(e)}")
            continue

        for item in response.get("items", []):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            if not any(v["id"] == video_id for v in all_videos):
                published_at = item["snippet"].get("publishedAt", "")
                all_videos.append({
                    "id": video_id, 
                    "title": title, 
                    "url": video_url,
                    "search_query": search_query,
                    "published_at": published_at
                })

    if not all_videos:
        print("No videos found from YouTube search")
        return None

    video_ids = [v["id"] for v in all_videos]

    details_url = "https://www.googleapis.com/youtube/v3/videos"
    details_params = {
        "part": "contentDetails,statistics,snippet",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY
    }

    try:
        details_response = requests.get(details_url, params=details_params).json()
        if "error" in details_response:
            error_info = details_response.get("error", {})
            print(f"YouTube API Error: {error_info}")
            return None
    except Exception as e:
        print(f"YouTube Video Details API request failed: {str(e)}")
        return None

    scored_videos = []
    for item in details_response.get("items", []):
        duration_str = item["contentDetails"]["duration"]
        definition = item["contentDetails"].get("definition", "sd")

        hours = int(re.search(r'(\d+)H', duration_str).group(1)) if re.search(r'(\d+)H', duration_str) else 0
        minutes = int(re.search(r'(\d+)M', duration_str).group(1)) if re.search(r'(\d+)M', duration_str) else 0
        seconds = int(re.search(r'(\d+)S', duration_str).group(1)) if re.search(r'(\d+)S', duration_str) else 0

        total_seconds = hours * 3600 + minutes * 60 + seconds

        if min_duration_seconds <= total_seconds <= max_duration_seconds:
            for vr in all_videos:
                if vr["id"] == item["id"]:
                    published_at = vr.get("published_at", "")
                    
                    try:
                        if published_at:
                            publish_str = published_at.replace('Z', '').split('.')[0]
                            publish_date = datetime.strptime(publish_str, '%Y-%m-%dT%H:%M:%S')
                            years_ago = (datetime.now() - publish_date).days / 365.25
                            if years_ago > 5:
                                continue
                    except:
                        pass
                    
                    vr["duration_seconds"] = total_seconds
                    vr["views"] = int(item["statistics"].get("viewCount", 0))
                    vr["likes"] = int(item["statistics"].get("likeCount", 0))
                    vr["definition"] = definition
                    vr["description"] = item["snippet"].get("description", "")
                    vr["channel"] = item["snippet"].get("channelTitle", "")
                    
                    like_to_view_ratio = vr["likes"] / vr["views"] if vr["views"] > 0 else 0
                    vr["like_to_view_ratio"] = like_to_view_ratio
                    
                    scored_videos.append(vr)
                    break

    if not scored_videos:
        return None

    query_lower = query.lower()
    stop_words = {'how', 'to', 'a', 'an', 'the', 'on', 'in', 'at', 'for', 'of', 'with', 'do', 'i', 'you', 'my', 'me'}
    
    query_words = re.sub(r'[^\w\s]', '', query_lower).split()
    query_key_words = [w for w in query_words if w not in stop_words and len(w) > 1]
    keyword_profile = build_keyword_profile(query_key_words)
    
    for video in scored_videos:
        metrics = compute_keyword_metrics(
            query_lower=query_lower,
            query_key_words=query_key_words,
            keyword_profile=keyword_profile,
            title=video.get("title", ""),
            description=video.get("description", ""),
            stop_words=stop_words
        )
        video.update(metrics)
    
    engagement_strict_min_likes = 10
    engagement_strict_min_ratio = 0.015
    engagement_relaxed_min_likes = 3
    engagement_relaxed_min_ratio = 0.005
    relevance_threshold = 0.75
    secondary_relevance_threshold = 0.6
    
    high_confidence = []
    relevance_only = []
    backup_candidates = []
    
    for video in scored_videos:
        duration = video.get("duration_seconds", 0)
        duration_rank = get_duration_rank(duration)
        views = video.get("views", 0)
        likes = video.get("likes", 0)
        like_ratio = video.get("like_to_view_ratio", 0)
        
        duration_score = 1.0 / (duration_rank + 1)
        view_reliability = min(views / 10000, 1.0)
        weighted_engagement = like_ratio * 1000 * (0.3 + 0.7 * view_reliability)
        popularity_score = min(views / 30000, 1.0)
        quality_score = (duration_score * 2.0) + weighted_engagement + (popularity_score * 2.0)
        video["quality_score"] = quality_score
        video["_duration_rank"] = duration_rank
        
        is_relevant = (
            video.get("keyword_match_ratio", 0.0) >= relevance_threshold
            or video.get("weighted_keyword_ratio", 0.0) >= relevance_threshold
            or video.get("has_exact_match")
        )

        if is_relevant:
            if likes >= engagement_strict_min_likes and like_ratio >= engagement_strict_min_ratio:
                high_confidence.append(video)
            elif likes >= engagement_relaxed_min_likes and like_ratio >= engagement_relaxed_min_ratio:
                relevance_only.append(video)
            else:
                relevance_only.append(video)
        else:
            if (
                video.get("keyword_match_ratio", 0.0) >= secondary_relevance_threshold
                or video.get("weighted_keyword_ratio", 0.0) >= secondary_relevance_threshold
                or video.get("has_any_keyword_signal")
            ):
                backup_candidates.append(video)
    
    if high_confidence:
        candidate_videos = high_confidence
    elif relevance_only:
        candidate_videos = relevance_only
    elif backup_candidates:
        candidate_videos = backup_candidates
    else:
        candidate_videos = scored_videos
    
    def sort_key(video):
        return (
            not video.get("has_exact_match"),
            video.get("_duration_rank", 999),
            -video.get("quality_score", 0.0),
            -video.get("views", 0),
            -video.get("likes", 0),
            -video.get("keyword_match_ratio", 0.0),
        )
    
    candidate_videos.sort(key=sort_key)
    filtered_videos = candidate_videos

    if filtered_videos:
        best_video = filtered_videos[0]
    else:
        best_video = None

    if filtered_videos:
        print(f"\n{'='*80}")
        print(f"TOP 3 VIDEO CANDIDATES:")
        print(f"{'='*80}")
        for i, video in enumerate(filtered_videos[:3]):
            duration = video.get('duration_seconds', 0)
            views = video.get('views', 0)
            likes = video.get('likes', 0)
            like_ratio = video.get('like_to_view_ratio', 0)
            title = video.get('title', '')
            
            # Calculate quality score for display (same formula as selection)
            duration_rank = get_duration_rank(duration)
            duration_score = 1.0 / (duration_rank + 1)
            view_reliability = min(views / 10000, 1.0)
            weighted_engagement = like_ratio * 1000 * (0.3 + 0.7 * view_reliability)
            popularity_score = min(views / 30000, 1.0)
            quality_score = (duration_score * 2.0) + weighted_engagement + (popularity_score * 2.0)
            keyword_ratio = video.get('key_word_match_ratio', 0)
            
            video_url = video.get('url', '')
            marker = "- SELECTED" if i == 0 else ""
            print(f"{i+1}. {title}")
            print(f"   URL: {video_url}")
            print(f"   Duration: {duration}s | Views: {views:,} | Likes: {likes:,} ({like_ratio:.2%})")
            print(f"   Quality Score: {quality_score:.2f} | Keyword Match: {keyword_ratio:.1%} {marker}")
        print(f"{'='*80}\n")
        
        # Clean up helper keys
        for video in filtered_videos:
            if "_sort_key" in video:
                del video["_sort_key"]
            if "_duration_rank" in video:
                del video["_duration_rank"]
            if "quality_score" in video:
                del video["quality_score"]
    
    if not best_video:
        print("No suitable videos found - Try rephrasing your query or adjusting the search parameters.")
        return None
    
    title = best_video.get('title', '')
    video_url = best_video.get('url', '')
    
    best_video['quality_metrics'] = {
        'total_candidates': len(filtered_videos),
        'title_match': 'exact' if query.lower() in title.lower() else 'partial',
        'duration_seconds': best_video.get('duration_seconds', 0),
        'duration_rank': get_duration_rank(best_video.get('duration_seconds', 0)),
        'resolution': best_video.get('definition', 'unknown'),
        'views': best_video.get('views', 0),
        'likes': best_video.get('likes', 0),
        'like_to_view_ratio': best_video.get('like_to_view_ratio', 0)
    }
    
    return best_video
