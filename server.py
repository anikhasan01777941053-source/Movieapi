import os
import sys
import subprocess

# ১. রিপোজিটরি ফোল্ডার চেক ও ক্লোন লজিক
REPO_DIR = "Moviebox_API"
REPO_URL = "https://github.com/walterwhite-69/Moviebox-API.git"

if not os.path.exists(REPO_DIR):
    try:
        print(f"Cloning dependency from {REPO_URL}...")
        subprocess.run(["git", "clone", REPO_URL, REPO_DIR], check=True)
    except Exception as clone_err:
        print(f"Git clone failed: {clone_err}")

# পাইথনের পাথে ফোল্ডারটি যুক্ত করা
base_path = os.path.abspath(REPO_DIR)
if base_path not in sys.path:
    sys.path.append(base_path)

from flask import Flask, jsonify, request

# ২. ট্রাই-ক্যাচ ব্লক দিয়ে সঠিক ক্লাসগুলো ইম্পোর্ট করা (EpisodeDetails বাদ দেওয়া হয়েছে)
try:
    from moviebox_api.v1.core import Homepage, Search, MovieDetails, TVSeriesDetails
    from moviebox_api.v1.requests import Session
except ImportError:
    sub_path = os.path.abspath(os.path.join(REPO_DIR, "moviebox_api"))
    if sub_path not in sys.path:
        sys.path.append(sub_path)
    try:
        from moviebox_api.v1.core import Homepage, Search, MovieDetails, TVSeriesDetails
        from moviebox_api.v1.requests import Session
    except ImportError as final_err:
        print(f"Critical Import Error: {final_err}")
        Homepage = Search = MovieDetails = TVSeriesDetails = Session = None

app = Flask(__name__)

def get_homepage_raw_data():
    if not Homepage: return {"error": "API library not loaded properly"}
    hp = Homepage()
    return hp.get_content_sync()

def get_items_by_index(index_num):
    try:
        raw_json = get_homepage_raw_data()
        if isinstance(raw_json, dict) and "error" in raw_json: return {"status": "error", "message": raw_json["error"]}
        operating_list = raw_json.get("operatingList", [])
        if len(operating_list) > index_num:
            section = operating_list[index_num]
            banner_data = section.get("banner", {}) if section else {}
            items = banner_data.get("items", []) if banner_data else []
            return {"status": "success", "count": len(items), "data": items}
        return {"status": "success", "count": 0, "data": []}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==================== হোমপেজ ও সার্চ রুটস ====================
@app.route('/v1/homepage/banner', methods=['GET'])
def get_homepage_banner():
    try:
        raw_json = get_homepage_raw_data()
        if isinstance(raw_json, dict) and "error" in raw_json: return jsonify(raw_json)
        banner_data = raw_json.get("banner", {})
        items = banner_data.get("items", []) if banner_data else []
        return jsonify({"status": "success", "count": len(items), "data": items})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})

@app.route('/v1/homepage/trending', methods=['GET'])
def get_homepage_trending(): return jsonify(get_items_by_index(0))

@app.route('/v1/homepage/cinema', methods=['GET'])
def get_homepage_cinema(): return jsonify(get_items_by_index(1))

@app.route('/v1/homepage/hotshort', methods=['GET'])
def get_homepage_hotshort(): return jsonify(get_items_by_index(2))

@app.route('/v1/homepage/popular', methods=['GET'])
def get_homepage_popular(): return jsonify(get_items_by_index(3))

@app.route('/v1/search', methods=['GET'])
def search_v1():
    if not Search: return jsonify({"status": "error", "message": "API library missing"})
    q = request.args.get('q', '')
    if not q: return jsonify({"status": "error", "message": "Query parameter 'q' is missing"})
    try:
        sh = Search(keyword=q)
        return jsonify({"status": "success", "data": sh.get_content_sync()})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})


# ==================== নতুন রুট ১: /detail/{slug} ====================
@app.route('/detail/<path:slug>', methods=['GET'])
def get_movie_or_series_detail(slug):
    if not MovieDetails: return jsonify({"status": "error", "message": "API library missing"})
    try:
        sess = Session()
        full_url = f"/detail/{slug}"
        
        if "tv" in slug.lower() or "series" in slug.lower():
            provider = TVSeriesDetails(full_url, session=sess)
        else:
            provider = MovieDetails(full_url, session=sess)
            
        raw_data = provider.get_content_sync()
        return jsonify(raw_data)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# ==================== নতুন রুট ২: /api/stream/{id}?detail_path={slug} ====================
@app.route('/api/stream/<id>', methods=['GET'])
def get_stream_link(id):
    detail_path = request.args.get('detail_path', '')
    season_num = request.args.get('se', '1')   
    episode_num = request.args.get('ep', '1')  
    
    try:
        sess = Session()
        downloads_list = []
        
        # ১. সিরিজের ক্ষেত্রে ডাইনামিক সাবজেক্ট এপিআই রিকোয়েস্ট ফায়ার করা (উইদাউট EpisodeDetails ক্লাস)
        if "tv" in detail_path.lower() or "series" in detail_path.lower():
            try:
                target_api = f"https://h5.aoneroom.com/wefeed-h5-bff/web/subject/play-info?subjectId={id}&seasonNum={season_num}&episodeNum={episode_num}"
                web_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                    "Referer": "https://h5.aoneroom.com/",
                    "Origin": "https://h5.aoneroom.com",
                    "Accept": "application/json, text/plain, */*"
                }
                # সেশন ব্যবহার করে সেফ কল করা
                res = sess.get(target_api, headers=web_headers)
                api_data = res.json() if hasattr(res, 'json') else {}
                play_info = api_data.get("data", {})
                
                if play_info.get("playAddress"):
                    addr = play_info["playAddress"]
                    downloads_list.append({"quality": addr.get("definition", "HD"), "url": addr.get("url")})
                elif play_info.get("videoAddress"):
                    addr = play_info["videoAddress"]
                    downloads_list.append({"quality": addr.get("definition", "HD"), "url": addr.get("url")})
            except Exception:
                pass
        
        # ২. ব্যাকআপ হিসেবে মুভি বা র মেটাডাটা থেকে ট্রেইলার/মেন লিংক চেক করা
        if not downloads_list and detail_path:
            full_url = detail_path if detail_path.startswith("http") or detail_path.startswith("/detail") else f"/detail/{detail_path}"
            if "tv" in detail_path.lower() or "series" in detail_path.lower():
                provider = TVSeriesDetails(full_url, session=sess)
            else:
                provider = MovieDetails(full_url, session=sess)
                
            raw_details = provider.get_content_sync()
            details_data = raw_details.get("resData", raw_details) if isinstance(raw_details, dict) else {}
            
            if isinstance(details_data, dict):
                if "videoAddress" in details_data and isinstance(details_data["videoAddress"], dict):
                    v_addr = details_data["videoAddress"]
                    if v_addr.get("url"):
                        downloads_list.append({"quality": v_addr.get("definition", "HD"), "url": v_addr.get("url")})
                
                if not downloads_list and "trailer" in details_data and isinstance(details_data["trailer"], dict):
                    t_addr = details_data["trailer"].get("videoAddress", {})
                    if t_addr and t_addr.get("url"):
                        downloads_list.append({"quality": "Auto/Preview", "url": t_addr.get("url")})

        return jsonify({
            "status": "success",
            "id": id,
            "season": season_num,
            "episode": episode_num,
            "streams": downloads_list
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
