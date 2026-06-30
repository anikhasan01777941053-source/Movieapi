import os
from flask import Flask, jsonify, request

# মুভিবক্সের আসল মডিউল এবং সেশন ইমপোর্ট করা হলো
from moviebox_api.v1.core import Homepage, Search, MovieDetails, TVSeriesDetails
from moviebox_api.v1.requests import Session

app = Flask(__name__)

def get_homepage_raw_data():
    """হোমপেজের মেইন জেসন ডাটা সিঙ্কোনাসলি তুলে আনার ফাংশন"""
    hp = Homepage()
    return hp.get_content_sync()

def get_items_by_index(index_num):
    """operatingList এর নির্দিষ্ট পজিশন থেকে মুভির লিস্ট বের করার ফাংশন"""
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


# ==================== ১. হোমপেজের ভাগ ভাগ করা সব ক্যাটাগরি ====================

@app.route('/v1/homepage/banner', methods=['GET'])
def get_homepage_banner():
    try:
        raw_json = get_homepage_raw_data()
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


# ==================== ২. মুভি ও সিরিজ সার্চ ====================

@app.route('/v1/search', methods=['GET'])
def search_v1():
    q = request.args.get('q', '')
    if not q:
        return jsonify({"status": "error", "message": "Query parameter 'q' is missing"})
    try:
        sh = Search(keyword=q)
        raw_json = sh.get_content_sync()
        return jsonify({"status": "success", "data": raw_json})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# ==================== ৩. ডিটেইলস ডাটা জেনারেটর (403 সেফ ও পারফেক্ট) ====================

@app.route('/v1/download', methods=['GET'])
def get_download_urls():
    detail_path = request.args.get('path', '')
    item_type = request.args.get('type', 'movie')
    
    if not detail_path:
        return jsonify({"status": "error", "message": "Parameter 'path' is missing"})
        
    try:
        # ১. সেশন তৈরি করা
        sess = Session()
        
        # ২. আইডি বা পাথ থাকলে ফুল ইউআরএল ফরম্যাটে কনভার্ট করা
        full_url = detail_path
        if not detail_path.startswith("http") and not detail_path.startswith("/detail"):
            full_url = f"/detail/{detail_path}"

        # ৩. মুভি নাকি সিরিজ সেই অনুযায়ী অবজেক্ট কল করা
        if item_type.lower() == 'series' or 'tv' in detail_path.lower():
            provider = TVSeriesDetails(full_url, session=sess)
        else:
            provider = MovieDetails(full_url, session=sess)
            
        # ৪. সার্ভার ব্লক এড়াতে সরাসরি ডিটেইলস জেসন কনটেন্ট সিঙ্কোনাসলি তুলে আনা
        details_data = provider.get_content_sync()
        
        return jsonify({
            "status": "success", 
            "item_type": item_type,
            "data": details_data
        })
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": "ডাটা জেনারেট করতে সমস্যা হয়েছে।",
            "error_details": str(e)
        })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
