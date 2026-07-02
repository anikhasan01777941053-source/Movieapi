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


# ==================== 🔥 নতুন ৪MD বাইপাস স্ট্রিম রুট ====================
@app.route('/api/stream/<id>', methods=['GET'])
def get_stream_link(id):
    detail_path = request.args.get('detail_path', '')
    season_num = request.args.get('se', '1')   
    episode_num = request.args.get('ep', '1')  
    
    streams_list = []
    
    try:
        # ১. প্রথমে ব্যাকএন্ড স্ক্র্যাপার দিয়ে ট্রাই করা (যদি আইপি ব্লক ছুটে যায়)
        if api:
            try:
                raw_streams = run_async(api.get_stream_sources(
                    subject_id=str(id),
                    detail_path=str(detail_path),
                    se=int(season_num),
                    ep=int(episode_num)
                ))
                if raw_streams and isinstance(raw_streams, list):
                    for s in raw_streams:
                        if isinstance(s, dict) and s.get("url"):
                            streams_list.append({"quality": s.get("quality", "HD"), "url": s.get("url")})
            except Exception:
                pass # ৪MD এরর আসলে স্কিপ করবে

        # ২. 🔥 চিরস্থায়ী সমাধান (৪MD বাইপাস): অফিশিয়াল H5 গেটওয়ে প্লেয়ার সোর্স তৈরি
        # এটি ইউজারের ব্রাউজার আইপি ব্যবহার করে প্লে হবে, তাই ৪MD আসবে না
        h5_player_url = f"https://h5.aoneroom.com/player?id={id}&se={season_num}&ep={episode_num}&source=ailok.pc"
        streams_list.append({
            "quality": "Multi-Resolution (Official H5 Gateway)",
            "url": h5_player_url,
            "note": "Open this link directly in any browser or webview to play seamlessly."
        })
        
        # ৩. ব্যাকআপ ওয়ান-রুম ডিরেক্ট ওয়েব প্লেয়ার লিংক
        web_player_url = f"https://www.aoneroom.com/play/{id}?season={season_num}&episode={episode_num}"
        streams_list.append({
            "quality": "Web Stream (Direct Backup)",
            "url": web_player_url
        })

        return jsonify({
            "status": "success",
            "id": id,
            "season": season_num,
            "episode": episode_num,
            "streams": streams_list
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
