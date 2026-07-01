import os
import sys
import subprocess

# ১. লাইব্রেরি অটো-ক্লোন ও পাথ সেটআপ
REPO_DIR = "Moviebox_API"
REPO_URL = "https://github.com/walterwhite-69/Moviebox-API.git"

if not os.path.exists(REPO_DIR):
    try:
        subprocess.run(["git", "clone", REPO_URL, REPO_DIR], check=True)
    except Exception:
        pass

base_path = os.path.abspath(REPO_DIR)
if base_path not in sys.path: sys.path.append(base_path)

from flask import Flask, jsonify, request

try:
    from moviebox_api.v1.core import Homepage, Search, MovieDetails, TVSeriesDetails
    from moviebox_api.v1.requests import Session
except ImportError:
    sub_path = os.path.abspath(os.path.join(REPO_DIR, "moviebox_api"))
    if sub_path not in sys.path: sys.path.append(sub_path)
    from moviebox_api.v1.core import Homepage, Search, MovieDetails, TVSeriesDetails
    from moviebox_api.v1.requests import Session

app = Flask(__name__)

# ==================== হোমপেজ ও সার্চ রুটস ====================
@app.route('/v1/homepage/banner', methods=['GET'])
def get_homepage_banner():
    hp = Homepage()
    return jsonify(hp.get_content_sync())

@app.route('/v1/search', methods=['GET'])
def search_v1():
    q = request.args.get('q', '')
    if not q: return jsonify({"status": "error", "message": "Missing query"})
    sh = Search(keyword=q)
    return jsonify(sh.get_content_sync())


# ==================== 🔥 ফিক্সড রুট ১: /detail/{slug} (র ডাটা প্রিন্ট করবে) ====================
@app.route('/detail/<path:slug>', methods=['GET'])
def get_movie_or_series_detail(slug):
    try:
        sess = Session()
        full_url = f"/detail/{slug}"
        
        if "tv" in slug.lower() or "series" in slug.lower():
            provider = TVSeriesDetails(full_url, session=sess)
        else:
            provider = MovieDetails(full_url, session=sess)
            
        # মুভিবক্স থেকে আসা একদম অরিজিনাল ডাটা সরাসরি রিটার্ন করবে
        raw_data = provider.get_content_sync()
        return jsonify(raw_data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# ==================== 🔥 ফিক্সড রুট ২: /api/stream/{id} (সেফ টেস্ট রান) ====================
@app.route('/api/stream/<id>', methods=['GET'])
def get_stream_link(id):
    detail_path = request.args.get('detail_path', '')
    season_num = request.args.get('se', '1')   
    episode_num = request.args.get('ep', '1')  
    
    try:
        sess = Session()
        full_url = detail_path if detail_path.startswith("http") or detail_path.startswith("/detail") else f"/detail/{detail_path}"
        
        provider = TVSeriesDetails(full_url, session=sess) if ("tv" in detail_path.lower() or "series" in detail_path.lower()) else MovieDetails(full_url, session=sess)
        raw_details = provider.get_content_sync()
        
        # ডাটা এনালাইসিসের জন্য পুরো কাঁচা ডাটা অবজেক্টটাই আমরা স্ট্রিমস এর ভেতরে পাস করে দিচ্ছি
        return jsonify({
            "status": "success",
            "info": "নিচের raw_response চেক করে আমাদের আসল চাবির নাম বের করতে হবে ভাই।",
            "id": id,
            "season": season_num,
            "episode": episode_num,
            "raw_response": raw_details
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
