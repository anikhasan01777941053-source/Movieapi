import os
import sys
import subprocess
import asyncio

# ১. রিপোজিটরি ক্লোন লজিক
REPO_DIR_HYPHEN = "Moviebox-API"
REPO_URL = "https://github.com/walterwhite-69/Moviebox-API.git"

if not os.path.exists(REPO_DIR_HYPHEN):
    try:
        print(f"Cloning dependency from {REPO_URL}...")
        subprocess.run(["git", "clone", REPO_URL, REPO_DIR_HYPHEN], check=True)
    except Exception as e:
        print(f"Clone failed: {e}")

# ২. 🔥 গ্লোবাল মডিউল কনফ্লিক্ট এড়াতে sys.path এর একদম শুরুতে (0 নম্বর ইনডেক্সে) পাথ ইনসার্ট করা
local_repo_path = os.path.abspath(REPO_DIR_HYPHEN)
if local_repo_path in sys.path:
    sys.path.remove(local_repo_path)
sys.path.insert(0, local_repo_path)

# এবার একদম ফ্রেশভাবে আমাদের লোকাল api.py ইম্পোর্ট হবে
try:
    import api
except ImportError as err:
    print(f"Critical Error loading api.py: {err}")
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

@app.route('/v1/homepage/popular', methods=['GET'])
def get_homepage_popular():
    if not api: return jsonify({"status": "error", "message": "API module missing"})
    try: return jsonify({"status": "success", "data": run_async(api.get_movies())})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route('/v1/search', methods=['GET'])
def search_v1():
    if not api: return jsonify({"status": "error", "message": "API module missing"})
    q = request.args.get('q', '')
    if not q: return jsonify({"status": "error", "message": "Query parameter 'q' is missing"})
    try: return jsonify({"status": "success", "data": run_async(api.get_search_results(q))})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})


# ==================== নতুন রুট ১: /detail/{slug} ====================
@app.route('/detail/<path:slug>', methods=['GET'])
def get_movie_or_series_detail(slug):
    if not api: return jsonify({"status": "error", "message": "API module missing"})
    try:
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
