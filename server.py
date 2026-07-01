import os
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

# ==================== ১. হোমপেজ ক্যাটাগরি সমূহ ====================
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

# ==================== ২. মুভি ও সিরিজ সার্চ ====================
@app.route('/v1/search', methods=['GET'])
def search_v1():
    q = request.args.get('q', '')
    if not q: return jsonify({"status": "error", "message": "Query parameter 'q' is missing"})
    try:
        sh = Search(keyword=q)
        return jsonify({"status": "success", "data": sh.get_content_sync()})
    except Exception as e: return jsonify({"status": "error", "message": str(e)})


# ==================== ৩. ভিডিও ডাউনলোড ও প্লে-লিংক জেনারেটর ====================

@app.route('/v1/download', methods=['GET'])
def get_download_urls():
    detail_path = request.args.get('path', '')
    item_type = request.args.get('type', 'movie')
    
    if not detail_path:
        return jsonify({"status": "error", "message": "Parameter 'path' is missing"})
        
    try:
        sess = Session()
        full_url = detail_path if detail_path.startswith("http") or detail_path.startswith("/detail") else f"/detail/{detail_path}"

        # মুভি বা সিরিজ অনুযায়ী মেইন ডিটেইলস ডাটা তুলে আনা
        if item_type.lower() == 'series' or 'tv' in detail_path.lower():
            provider = TVSeriesDetails(full_url, session=sess)
        else:
            provider = MovieDetails(full_url, session=sess)
            
        details_data = provider.get_content_sync()
        
        # আমাদের নিজস্ব স্ট্রাকচারড রেসপন্স তৈরি করা যা স্কেচওয়্যারে সহজে পার্স করা যাবে
        video_links = []
        
        # ১. মুভির ক্ষেত্রে যদি সরাসরি ডিরেক্ট প্লে লিংক (videoAddress) থাকে
        if "videoAddress" in details_data and details_data["videoAddress"]:
            v_addr = details_data["videoAddress"]
            if v_addr.get("url"):
                video_links.append({
                    "quality": f"{v_addr.get('definition', 'Default')} (Movie)",
                    "url": v_addr.get("url"),
                    "size": v_addr.get("size", 0)
                })
                
        # ২. ট্রেইলার বা প্রিভিউ লিংক যদি থাকে সেটাও ব্যাকআপ হিসেবে অ্যাড করা
        if "trailer" in details_data and details_data["trailer"]:
            trailer_data = details_data["trailer"]
            # যদি এর ভেতরেও কোনো ভিডিও অ্যাড্রেস থাকে
            if isinstance(trailer_data, dict) and trailer_data.get("videoAddress"):
                t_addr = trailer_data["videoAddress"]
                if t_addr.get("url"):
                    video_links.append({
                        "quality": "Preview / Trailer",
                        "url": t_addr.get("url"),
                        "size": t_addr.get("size", 0)
                    })

        # যদি কোনো লিংক খুঁজে পায়
        if video_links:
            return jsonify({
                "status": "success",
                "item_type": item_type,
                "has_video": True,
                "downloads": video_links,
                "full_data": details_data  # ব্যাকআপ হিসেবে পুরো জেসনও থাকলো
            })
            
        # কোনো কারণে ডিরেক্ট লিংক রেডি না থাকলে সেফ জেসন রেসপন্স পাঠানো
        return jsonify({
            "status": "success",
            "item_type": item_type,
            "has_video": False,
            "downloads": [],
            "full_data": details_data
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "সার্ভার ডাটা প্রসেস করতে পারেনি।",
            "error_details": str(e)
        })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
