import os
import httpx
from flask import Flask, jsonify, request
from moviebox_api.v1.core import Homepage, Search, MovieDetails, TVSeriesDetails
from moviebox_api.v1.requests import Session

app = Flask(__name__)

def get_homepage_raw_data():
    hp = Homepage()
    return hp.get_content_sync()

def get_items_by_index(index_num):
    try:
        raw_json = get_homepage_raw_data()
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
    q = request.args.get('q', '')
    if not q: return jsonify({"status": "error", "message": "Query parameter 'q' is missing"})
    try:
        sh = Search(keyword=q)
        return jsonify({"status": "success", "data": sh.get_content_sync()})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})


# ==================== ৩. ফিক্সড ভিডিও ডাউনলোড ও প্লে-লিংক এপিআই ====================

@app.route('/v1/download', methods=['GET'])
def get_download_urls():
    detail_path = request.args.get('path', '')
    item_type = request.args.get('type', 'movie')
    season_num = request.args.get('se', '1')   
    episode_num = request.args.get('ep', '1')  
    
    if not detail_path:
        return jsonify({"status": "error", "message": "Parameter 'path' is missing"})
        
    try:
        sess = Session()
        full_url = detail_path if detail_path.startswith("http") or detail_path.startswith("/detail") else f"/detail/{detail_path}"

        # ১. মেটাডাটা অবজেক্ট ফেচ করা
        if item_type.lower() == 'series' or 'tv' in detail_path.lower():
            provider = TVSeriesDetails(full_url, session=sess)
        else:
            provider = MovieDetails(full_url, session=sess)
            
        details_data = provider.get_content_sync()
        
        # ২. জেসনের সব লেভেল থেকে নিখুঁতভাবে subjectId খুঁজে বের করার ফিক্সড লজিক
        subject_id = None
        if isinstance(details_data, dict):
            if "subjectId" in details_data and details_data["subjectId"]:
                subject_id = details_data["subjectId"]
            elif "subject" in details_data and isinstance(details_data["subject"], dict):
                subject_id = details_data["subject"].get("subjectId") or details_data["subject"].get("id")
            elif "id" in details_data:
                subject_id = details_data["id"]

        # যদি কোনোভাবেই আইডি না পাওয়া যায়, তবে ম্যানুয়ালি চেক করার জন্য ডাটা রিটার্ন করা
        if not subject_id:
            return jsonify({
                "status": "error", 
                "message": "Subject ID পাওয়া যায়নি। জেসন ফরম্যাট পরিবর্তন হয়েছে।", 
                "debug_keys": list(details_data.keys()) if isinstance(details_data, dict) else "Not a dict"
            })

        # ৩. মুভিবক্স ডাউনলোড এপিআই কল (উইথ ফিক্সড আইডি)
        target_api = f"https://h5.aoneroom.com/wefeed-h5-bff/web/subject/download?subjectId={subject_id}&se={season_num}&ep={episode_num}"
        
        web_headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
            "Referer": "https://fmoviesunblocked.net/",
            "Origin": "https://h5.aoneroom.com",
            "Platform": "web",
            "Accept": "application/json, text/plain, */*"
        }

        with httpx.Client(headers=web_headers, timeout=15.0, follow_redirects=True) as client:
            res = client.get(target_api)
            api_data = res.json()

        video_info = api_data.get("data", {})
        if video_info.get("downloads") or video_info.get("hasResource"):
            return jsonify({
                "status": "success",
                "item_type": item_type,
                "subject_id": subject_id,
                "current_season": season_num,
                "current_episode": episode_num,
                "downloads": video_info.get("downloads", []),
                "captions": video_info.get("captions", [])
            })

        # ৪. ব্যাকআপ সেকশন (যদি কোনো ডাউনলোড লিংক জেনারেট না হয়)
        backup_downloads = []
        if isinstance(details_data, dict) and "trailer" in details_data and details_data["trailer"]:
            t_addr = details_data["trailer"].get("videoAddress", {}) if isinstance(details_data["trailer"], dict) else {}
            if t_addr and t_addr.get("url"):
                backup_downloads.append({
                    "definition": "Preview/Trailer",
                    "url": t_addr.get("url")
                })

        return jsonify({
            "status": "success",
            "note": "Bypassed via metadata fallback",
            "subject_id": subject_id,
            "downloads": backup_downloads,
            "seasons_info": details_data.get("resource", {}).get("seasons", []) if isinstance(details_data, dict) else []
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "সার্ভার ইন্টারনাল এরর ফেস করেছে।",
            "error_details": str(e)
        })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
