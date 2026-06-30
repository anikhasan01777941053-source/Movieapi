import os
import asyncio
from flask import Flask, jsonify, request

# অফিশিয়াল ডকুমেন্টেশনের সঠিক পাথ অনুযায়ী মডিউলগুলো ইমপোর্ট করা হলো
from moviebox_api.v1.core import Homepage, Search, MovieDetails, TVSeriesDetails
from moviebox_api.v1 import DownloadableMovieFilesDetail
from moviebox_api.v1.requests import Session

app = Flask(__name__)

def run_async(async_func):
    """Async ফাংশন রান করার হেল্পার"""
    return asyncio.run(async_func)

def get_homepage_raw_data():
    """হোমপেজের মেইন জেসন ডাটা ব্যাকগ্রাউন্ডে তুলে আনার ফাংশন"""
    hp = Homepage()
    return run_async(hp.get_content())

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
        raw_json = run_async(sh.get_content())
        return jsonify({"status": "success", "data": raw_json})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


# ==================== ৩. আসল ফুল মুভি ও সিরিজ ভিডিও লিংক জেনারেটর ====================

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
            
        # ৪. মুভির মূল মেটাডাটা মডেল বের করা
        target_movie_details_model = run_async(provider.get_content_model())
        
        # ৫. আসল ফুল মুভির প্লে-লিংক এবং ডাউনলোডের ডাটা এক্সট্রাক্ট করা
        downloadable_files = DownloadableMovieFilesDetail(sess, target_movie_details_model)
        downloadable_files_detail = run_async(downloadable_files.get_content())
        
        return jsonify({
            "status": "success", 
            "item_type": item_type,
            "data": downloadable_files_detail
        })
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": "ফুল ভিডিও লিংক জেনারেট করতে সমস্যা হয়েছে।",
            "error_details": str(e)
        })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
