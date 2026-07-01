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


# ==================== ৩. ফিক্সড ডাউনলোড ও মেটাডাটা এপিআই ====================

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

        if item_type.lower() == 'series' or 'tv' in detail_path.lower():
            provider = TVSeriesDetails(full_url, session=sess)
        else:
            provider = MovieDetails(full_url, session=sess)
            
        raw_details = provider.get_content_sync()
        
        # ১. resData কনটেইনার আনপ্যাকিং (সবচেয়ে গুরুত্বপূর্ণ পার্ট)
        details_data = {}
        if isinstance(raw_details, dict):
            if "resData" in raw_details and isinstance(raw_details["resData"], dict):
                details_data = raw_details["resData"]
            else:
                details_data = raw_details

        # ২. সাবজেক্ট আইডি এক্সট্র্যাকশন
        subject_id = None
        if isinstance(details_data, dict):
            if "subject" in details_data and isinstance(details_data["subject"], dict):
                subject_id = details_data["subject"].get("subjectId") or details_data["subject"].get("id")
            if not subject_id and "subjectId" in details_data:
                subject_id = details_data["subjectId"]

        # ৩. সোর্স ও প্রিভিউ লিংক প্রসেসিং
        downloads_list = []
        if isinstance(details_data, dict):
            if "videoAddress" in details_data and isinstance(details_data["videoAddress"], dict):
                v_addr = details_data["videoAddress"]
                if v_addr.get("url"):
                    downloads_list.append({"quality": v_addr.get("definition", "HD"), "url": v_addr.get("url")})
            
            if not downloads_list and "trailer" in details_data and isinstance(details_data["trailer"], dict):
                t_addr = details_data["trailer"].get("videoAddress", {})
                if t_addr and t_addr.get("url"):
                    downloads_list.append({"quality": "Auto/Preview", "url": t_addr.get("url")})

        # ৪. ফাইনাল ডেলিভারি রেসপন্স
        return jsonify({
            "status": "success",
            "item_type": item_type,
            "subject_id": subject_id or "unknown",
            "current_season": season_num,
            "current_episode": episode_num,
            "downloads": downloads_list,
            "seasons_info": details_data.get("resource", {}).get("seasons", []) if isinstance(details_data, dict) else []
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "WalterWhite-69 API এর সাথে মেটাডাটা পার্সিং এরর হয়েছে।",
            "error_details": str(e)
        })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
