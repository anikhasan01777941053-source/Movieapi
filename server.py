import os
import sys
import subprocess
import asyncio

# ১. রিপোজিটরি ক্লোন লজিক
REPO_DIR_HYPHEN = "Moviebox-API"
REPO_URL = "https://github.com/walterwhite-69/Moviebox-API.git"

if not os.path.exists(REPO_DIR_HYPHEN):
    try:
        subprocess.run(["git", "clone", REPO_URL, REPO_DIR_HYPHEN], check=True)
    except Exception:
        pass

local_repo_path = os.path.abspath(REPO_DIR_HYPHEN)
if local_repo_path not in sys.path:
    sys.path.insert(0, local_repo_path)

try:
    import api
except ImportError:
    api = None

from flask import Flask, jsonify, request

app = Flask(__name__)

def run_async(async_func):
    return asyncio.run(async_func)

# ==================== হোমপেজ ও সার্চ রুটস ====================
@app.route('/v1/homepage/banner', methods=['GET'])
def get_homepage_banner():
    if not api: return jsonify({"status": "error", "message": "API module missing"})
    try: return jsonify({"status": "success", "data": run_async(api.get_banner())})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route('/v1/homepage/trending', methods=['GET'])
def get_homepage_trending():
    if not api: return jsonify({"status": "error", "message": "API module missing"})
    try: return jsonify({"status": "success", "data": run_async(api.get_trending())})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route('/v1/homepage/cinema', methods=['GET'])
def get_homepage_cinema():
    if not api: return jsonify({"status": "error", "message": "API module missing"})
    try: return jsonify({"status": "success", "data": run_async(api.get_cinema())})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route('/v1/search', methods=['GET'])
def search_v1():
    if not api: return jsonify({"status": "error", "message": "API module missing"})
    q = request.args.get('q', '')
    if not q: return jsonify({"status": "error", "message": "Missing 'q'"})
    try: return jsonify({"status": "success", "data": run_async(api.get_search_results(q))})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route('/detail/<path:slug>', methods=['GET'])
def get_movie_or_series_detail(slug):
    if not api: return jsonify({"status": "error", "message": "API module missing"})
    try: return jsonify(run_async(api.get_movie_detail(slug)))
    except Exception as e: return jsonify({"status": "error", "message": str(e)})


import httpx # হেডার ও এপিআই রিকোয়েস্ট হ্যান্ডেল করার জন্য

# ==================== 🔥 ExoPlayer এর জন্য ডিরেক্ট মিডিয়া সোর্স রুট ====================
@app.route('/api/stream/<id>', methods=['GET'])
def get_stream_link(id):
    detail_path = request.args.get('detail_path', '')
    season_num = request.args.get('se', '1')   
    episode_num = request.args.get('ep', '1')  
    
    streams_list = []
    
    # মুভিবক্সের অফিশিয়াল মোবাইল প্লেয়ার এপিআই এন্ডপয়েন্ট
    player_api_url = "https://h5.aoneroom.com/wefeed-h5-bff/web/subject/play-info"
    
    # প্লেয়ারকে আসল মোবাইল ব্রাউজার হিসেবে প্রমাণ করার জন্য মাস্ট-হ্যাভ হেডার্স
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://h5.aoneroom.com",
        "Referer": f"https://h5.aoneroom.com/player?id={id}&se={season_num}&ep={episode_num}&source=ailok.pc",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }
    
    # এপিআই প্যারামিটার্স
    params = {
        "subjectId": str(id),
        "seasonNum": str(season_num),
        "episodeNum": str(episode_num)
    }
    
    try:
        # ক্লায়েন্ট রিকোয়েস্ট জেনারেট করা (৪০৩ এড়াতে হেডারসহ)
        with httpx.Client(headers=headers, timeout=10.0) as client:
            response = client.get(player_api_url, params=params)
            
            if response.status_code == 200:
                res_json = response.json()
                play_data = res_json.get("data", {})
                
                # প্লেয়ার অ্যাড্রেস অবজেক্ট চেক করা
                video_address = play_data.get("playAddress") or play_data.get("videoAddress")
                
                if video_address and isinstance(video_address, dict):
                    direct_url = video_address.get("url")
                    quality = video_address.get("definition", "Auto (HD)")
                    
                    if direct_url:
                        streams_list.append({
                            "quality": f"ExoPlayer Direct ({quality})",
                            "url": direct_url,
                            "player_type": "direct_media_stream"
                        })
        
        # ফলব্যাক লজিক: কোনো কারণে রেন্ডার আইপি ব্লক থাকলে এইচ৫ ওয়েব প্লেয়ার ব্যাকআপ হিসেবে থাকবে
        if not streams_list:
            h5_url = f"https://h5.aoneroom.com/player?id={id}&se={season_num}&ep={episode_num}&source=ailok.pc"
            streams_list.append({
                "quality": "WebView Fallback (H5 Player)",
                "url": h5_url,
                "player_type": "webview_embed"
            })
            
        return jsonify({
            "status": "success",
            "id": id,
            "season": season_num,
            "episode": episode_num,
            "streams": streams_list
        })
        
    except Exception as e:
        # এরর আসলেও ব্যাকআপ ওয়েব প্লেয়ার রেডি রাখবে যেন অ্যাপ ক্র্যাশ না করে
        h5_url = f"https://h5.aoneroom.com/player?id={id}&se={season_num}&ep={episode_num}&source=ailok.pc"
        return jsonify({
            "status": "success",
            "id": id,
            "season": season_num,
            "episode": episode_num,
            "streams": [{
                "quality": "WebView Fallback (H5 Player)",
                "url": h5_url,
                "player_type": "webview_embed"
            }],
            "error_log": str(e)
        })
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
