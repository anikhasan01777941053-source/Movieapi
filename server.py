import os
import sys
import subprocess
import asyncio

# ১. রিপোজিটরি পাথ সেটআপ (সরাসরি api.py ইম্পোর্ট করার জন্য)
REPO_DIR = "Moviebox_API"
REPO_URL = "https://github.com/walterwhite-69/Moviebox-API.git"

if not os.path.exists(REPO_DIR):
    try:
        subprocess.run(["git", "clone", REPO_URL, REPO_DIR], check=True)
    except Exception as e:
        print(f"Clone failed: {e}")

# পাইথনের পাথে ফোল্ডারটি যুক্ত করা যাতে api.py সরাসরি পাওয়া যায়
base_path = os.path.abspath(REPO_DIR)
if base_path not in sys.path:
    sys.path.append(base_path)

from flask import Flask, jsonify, request

# api.py থেকে সরাসরি ফাংশনগুলো ইম্পোর্ট করা
try:
    import api
except ImportError:
    print("Critical: api.py not found in path")
    api = None

app = Flask(__name__)

# অসিঙ্ক ফাংশনগুলোকে ফ্ল্যাক্সে রান করার জন্য হেল্পার
def run_async(async_func):
    return asyncio.run(async_func)

# ==================== হোমপেজ ও সার্চ রুটস ====================
@app.route('/v1/homepage/banner', methods=['GET'])
def get_homepage_banner():
    if not api: return jsonify({"status": "error", "message": "API module missing"})
    try:
        data = run_async(api.get_banner())
        return jsonify({"status": "success", "data": data})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route('/v1/homepage/trending', methods=['GET'])
def get_homepage_trending():
    try: return jsonify({"status": "success", "data": run_async(api.get_trending())})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route('/v1/homepage/cinema', methods=['GET'])
def get_homepage_cinema():
    try: return jsonify({"status": "success", "data": run_async(api.get_cinema())})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route('/v1/homepage/popular', methods=['GET'])
def get_homepage_popular():
    try: return jsonify({"status": "success", "data": run_async(api.get_movies())})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route('/v1/search', methods=['GET'])
def search_v1():
    q = request.args.get('q', '')
    if not q: return jsonify({"status": "error", "message": "Query parameter 'q' is missing"})
    try:
        data = run_async(api.get_search_results(q))
        return jsonify({"status": "success", "data": data})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})


# ==================== নতুন রুট ১: /detail/{slug} ====================
@app.route('/detail/<path:slug>', methods=['GET'])
def get_movie_or_series_detail(slug):
    if not api: return jsonify({"status": "error", "message": "API module missing"})
    try:
        # api.py এর get_movie_detail ফাংশন কল
        data = run_async(api.get_movie_detail(slug))
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# ==================== নতুন রুট ২: /api/stream/{id}?detail_path={slug} ====================
@app.route('/api/stream/<id>', methods=['GET'])
def get_stream_link(id):
    if not api: return jsonify({"status": "error", "message": "API module missing"})
    
    detail_path = request.args.get('detail_path', '')
    season_num = int(request.args.get('se', '0'))   
    episode_num = int(request.args.get('ep', '0'))  
    
    try:
        # স্ক্রিনশটের একদম শেষ লাইনের ফাংশন অনুযায়ী আর্গুমেন্ট পাস করা হলো
        # get_stream_sources(subject_id, detail_path, se, ep)
        streams_data = run_async(api.get_stream_sources(
            subject_id=str(id),
            detail_path=str(detail_path),
            se=season_num,
            ep=episode_num
        ))
        
        return jsonify({
            "status": "success",
            "id": id,
            "season": season_num,
            "episode": episode_num,
            "streams": streams_data
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
