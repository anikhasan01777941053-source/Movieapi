import os
import sys
import subprocess

# ==================== ১. লাইব্রেরি অটো-ক্লোন ও পাথ সেটআপ ====================
REPO_DIR = "Moviebox_API"
REPO_URL = "https://github.com/walterwhite-69/Moviebox-API.git"

if not os.path.exists(REPO_DIR):
    try:
        print(f"Cloning dependency from {REPO_URL}...")
        subprocess.run(["git", "clone", REPO_URL, REPO_DIR], check=True)
    except Exception as clone_err:
        print(f"Git clone failed: {clone_err}")

# পাইথনের গ্লোবাল পাথে মডিউল ডিরেক্টরি যুক্ত করা
base_path = os.path.abspath(REPO_DIR)
if base_path not in sys.path:
    sys.path.append(base_path)

from flask import Flask, jsonify, request

# ==================== ২. মুভিবক্স এপিআই ক্লাস ইম্পোর্ট হ্যান্ডলিং ====================
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

# ==================== ৩. ইন্টারনাল হেল্পার ফাংশনস ====================
def get_homepage_raw_data():
    if not Homepage: 
        return {"error": "API library not loaded properly"}
    hp = Homepage()
    return hp.get_content_sync()

def get_items_by_index(index_num):
    try:
        raw_json = get_homepage_raw_data()
        if isinstance(raw_json, dict) and "error" in raw_json: 
            return {"status": "error", "message": raw_json["error"]}
        operating_list = raw_json.get("operatingList", [])
        if len(operating_list) > index_num:
            section = operating_list[index_num]
            banner_data = section.get("banner", {}) if section else {}
            items = banner_data.get("items", []) if banner_data else []
            return {"status": "success", "count": len(items), "data": items}
        return {"status": "success", "count": 0, "data": []}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ==================== ৪. হোমপেজ ও সার্চ রুটস ====================
@app.route('/v1/homepage/banner', methods=['GET'])
def get_homepage_banner():
    try:
        raw_json = get_homepage_raw_data()
        if isinstance(raw_json, dict) and "error" in raw_json: 
            return jsonify(raw_json)
        banner_data = raw_json.get("banner", {})
        items = banner_data.get("items", []) if banner_data else []
        return jsonify({"status": "success", "count": len(items), "data": items})
    except Exception as e: 
        return jsonify({"status": "error", "message": str(e)})

@app.route('/v1/homepage/trending', methods=['GET'])
def get_homepage_trending(): 
    return jsonify(get_items_by_index(0))

@app.route('/v1/homepage/cinema', methods=['GET'])
def get_homepage_cinema(): 
    return jsonify(get_items_by_index(1))

@app.route('/v1/homepage/hotshort', methods=['GET'])
def get_homepage_hotshort(): 
    return jsonify(get_items_by_index(2))

@app.route('/v1/homepage/popular', methods=['GET'])
def get_homepage_popular(): 
    return jsonify(get_items_by_index(3))

@app.route('/v1/search', methods=['GET'])
def search_v1():
    if not Search: 
        return jsonify({"status": "error", "message": "API library missing"})
    q = request.args.get('q', '')
    if not q: 
        return jsonify({"status": "error", "message": "Query parameter 'q' is missing"})
    try:
        sh = Search(keyword=q)
        return jsonify({"status": "success", "data": sh.get_content_sync()})
    except Exception as e: 
        return jsonify({"status": "error", "message": str(e)})


# ==================== ৫. ডিটেইলস মেটাডাটা রুট (/detail/{slug}) ====================
@app.route('/detail/<path:slug>', methods=['GET'])
def get_movie_or_series_detail(slug):
    if not MovieDetails: 
        return jsonify({"status": "error", "message": "API library missing"})
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


# ==================== ৬. স্টেবল স্ট্রিমিং ও প্লে-লিংক রুট ====================
@app.route('/api/stream/<id>', methods=['GET'])
def get_stream_link(id):
    detail_path = request.args.get('detail_path', '')
    season_num = request.args.get('se', '1')   
    episode_num = request.args.get('ep', '1')  
    
    try:
        sess = Session()
        downloads_list = []
        
        if detail_path:
            full_url = detail_path if detail_path.startswith("http") or detail_path.startswith("/detail") else f"/detail/{detail_path}"
            
            # টাইপ সিরিজ হলে TVSeriesDetails থেকে স্ট্রাকচার অনুযায়ী ফিল্টার করা
            if "tv" in detail_path.lower() or "series" in detail_path.lower():
                provider = TVSeriesDetails(full_url, session=sess)
                raw_details = provider.get_content_sync()
                details_data = raw_details.get("resData", raw_details) if isinstance(raw_details, dict) else {}
                
                # সিজন ও এপিসোডের অবজেক্ট ফিল্টারিং লজিক
                if isinstance(details_data, dict) and "episode_list" in details_data:
                    for ep in details_data.get("episode_list", []):
                        if str(ep.get("season")) == str(season_num) and str(ep.get("episode")) == str(episode_num):
                            v_addr = ep.get("videoAddress", {})
                            if v_addr and v_addr.get("url"):
                                downloads_list.append({"quality": v_addr.get("definition", "HD"), "url": v_addr.get("url")})
                                
                if not downloads_list and isinstance(details_data, dict):
                    v_addr = details_data.get("videoAddress")
                    if isinstance(v_addr, dict) and v_addr.get("url"):
                        downloads_list.append({"quality": v_addr.get("definition", "HD"), "url": v_addr.get("url")})

            # টাইপ মুভি হলে সরাসরি MovieDetails এর ভিডিও অ্যাড্রেস নেওয়া
            else:
                provider = MovieDetails(full_url, session=sess)
                raw_details = provider.get_content_sync()
                details_data = raw_details.get("resData", raw_details) if isinstance(raw_details, dict) else {}
                
                if isinstance(details_data, dict) and "videoAddress" in details_data:
                    v_addr = details_data["videoAddress"]
                    if isinstance(v_addr, dict) and v_addr.get("url"):
                        downloads_list.append({"quality": v_addr.get("definition", "HD"), "url": v_addr.get("url")})

            # গ্লোবাল ফলব্যাক: ট্রেইলার/প্রিভিউ সোর্স ইউআরএল
            if not downloads_list and isinstance(details_data, dict) and "trailer" in details_data:
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
