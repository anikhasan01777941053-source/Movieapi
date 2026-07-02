import os
import sys
import subprocess
import asyncio
from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

# ==================== ১. ডিপেন্ডেন্সি ক্লোন লজিক ====================
REPO_DIR_HYPHEN = "Moviebox-API"
REPO_URL = "https://github.com/walterwhite-69/Moviebox-API.git"

if not os.path.exists(REPO_DIR_HYPHEN):
    try:
        print(f"Cloning dependency from {REPO_URL}...")
        subprocess.run(["git", "clone", REPO_URL, REPO_DIR_HYPHEN], check=True)
    except Exception as e:
        print(f"Clone failed: {e}")

# গ্লোবাল মডিউল কনফ্লিক্ট এড়াতে sys.path এর শুরুতে পাথ ইনসার্ট করা
local_repo_path = os.path.abspath(REPO_DIR_HYPHEN)
if local_repo_path not in sys.path:
    sys.path.insert(0, local_repo_path)

# ফ্রেশভাবে লোকাল api.py মডিউল ইম্পোর্ট করা
try:
    import api
except ImportError as err:
    print(f"Critical Error loading api.py: {err}")
    api = None

# অসিঙ্ক ফাংশন রান করার হেল্পার
def run_async(async_func):
    return asyncio.run(async_func)


# ==================== ২. হোমপেজ ও সার্চ রুটস ====================
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


# ==================== ৩. মুভি/সিরিজ ডিটেইলস রুট ====================
@app.route('/detail/<path:slug>', methods=['GET'])
def get_movie_or_series_detail(slug):
    if not api: return jsonify({"status": "error", "message": "API module missing"})
    try:
        data = run_async(api.get_movie_detail(slug))
        return jsonify(data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# ==================== ৪. 🔥 ৪MD-প্রুফ প্লেয়ার ও স্ট্রিমিং গেটওয়ে ====================
@app.route('/api/stream/<id>', methods=['GET'])
def get_stream_link(id):
    season_num = request.args.get('se', '1')   
    episode_num = request.args.get('ep', '1')  
    
    # অফিশিয়াল স্টেবল প্লেয়ার গেটওয়ে ইউআরএল
    h5_player_url = f"https://h5.aoneroom.com/player?id={id}&se={season_num}&ep={episode_num}&source=ailok.pc"
    
    # অ্যাপ যদি সরাসরি প্লেয়ারের JSON ইউআরএল চায় (?format=json)
    if request.args.get('format') == 'json':
        return jsonify({
            "status": "success",
            "id": id,
            "season": season_num,
            "episode": episode_num,
            "player_url": f"https://movieapi-fvjx.onrender.com/api/player_view/{id}?se={season_num}&ep={episode_num}"
        })
        
    # ডিরেক্ট লিংকে হিট করলে এই কাস্টম ফুল-স্ক্রিন HTML প্লেয়ারটি লোড হবে
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Stream Player</title>
        <style>
            body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; background-color: #000; }}
            iframe {{ width: 100%; height: 100%; border: none; }}
        </style>
    </head>
    <body>
        <iframe src="{h5_player_url}" allowfullscreen="true" scrolling="no" allow="encrypted-media; autoplay"></iframe>
    </body>
    </html>
    """
    return render_template_string(html_content)

# সাপোর্টিং রুট (অ্যাপ ওয়েবভিউ সেফটি ভিউ)
@app.route('/api/player_view/<id>', methods=['GET'])
def player_view(id):
    season_num = request.args.get('se', '1')
    episode_num = request.args.get('ep', '1')
    h5_player_url = f"https://h5.aoneroom.com/player?id={id}&se={season_num}&ep={episode_num}&source=ailok.pc"
    return render_template_string(f'<iframe src="{h5_player_url}" style="width:100%;height:100%;border:none;" allowfullscreen></iframe>')


# ==================== ৫. সার্ভার স্টার্ট লজিক ====================
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
