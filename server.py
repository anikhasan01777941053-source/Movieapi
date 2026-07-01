import os
from flask import Flask, jsonify, request
from moviebox_api.v1.core import Homepage, Search, MovieDetails, TVSeriesDetails
from moviebox_api.v1 import DownloadableMovieFilesDetail
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


# ==================== ৩. ভিডিওর আসল ডাউনলোড ফাইল লিংক জেনারেটর ====================

@app.route('/v1/download', methods=['GET'])
def get_download_urls():
    detail_path = request.args.get('path', '')
    item_type = request.args.get('type', 'movie')
    
    if not detail_path:
        return jsonify({"status": "error", "message": "Parameter 'path' is missing"})
        
    try:
        # ১. সেশন তৈরি করা
        sess = Session()
        
        # ২. ফুল ইউআরএল পাথ সেট করা
        full_url = detail_path if detail_path.startswith("http") or detail_path.startswith("/detail") else f"/detail/{detail_path}"

        # ৩. মুভি বা সিরিজ অনুযায়ী অবজেক্ট কল করা
        if item_type.lower() == 'series' or 'tv' in detail_path.lower():
            provider = TVSeriesDetails(full_url, session=sess)
        else:
            provider = MovieDetails(full_url, session=sess)
            
        # ৪. মুভির মূল মেটাডাটা মডেল বের করা
        target_movie_details_model = provider.get_content_model_sync()
        
        # ৫. অফিশিয়াল লাইব্রেরি দিয়ে ভিডিও ফাইল ও ডাউনলোডের ডাটা এক্সট্রাক্ট করা
        downloadable_files = DownloadableMovieFilesDetail(sess, target_movie_details_model)
        downloadable_files_detail = downloadable_files.get_content_sync()
        
        # যদি সাকসেসফুলি ভিডিওর লিস্ট পাওয়া যায়
        return jsonify({
            "status": "success", 
            "item_type": item_type,
            "data": downloadable_files_detail
        })
        
    except Exception as e:
        # যদি সার্ভার ব্লক বা ৪MD এরর আসে, তাহলে আমরা অটোমেটিক আরেকটি ফ্রি পাবলিক প্রক্সি দিয়ে ট্রাই করব
        try:
            # একটি ফ্রি প্রক্সি সেটআপ (যা মুভিবক্সের ৪MD ব্লক রিমুভ করবে)
            os.environ["HTTP_PROXY"] = "http://20.111.54.16:80"  # ব্যাকআপ পাবলিক প্রক্সি আইপি
            os.environ["HTTPS_PROXY"] = "http://20.111.54.16:80"
            
            sess_proxy = Session()
            if item_type.lower() == 'series' or 'tv' in detail_path.lower():
                provider = TVSeriesDetails(full_url, session=sess_proxy)
            else:
                provider = MovieDetails(full_url, session=sess_proxy)
                
            target_movie_details_model = provider.get_content_model_sync()
            downloadable_files = DownloadableMovieFilesDetail(sess_proxy, target_movie_details_model)
            downloadable_files_detail = downloadable_files.get_content_sync()
            
            return jsonify({
                "status": "success",
                "proxy_used": True,
                "item_type": item_type,
                "data": downloadable_files_detail
            })
        except Exception as proxy_err:
            return jsonify({
                "status": "error", 
                "message": "মুভিবক্স সিকিউরিটির কারণে ভিডিও লিংক জেনারেট করা যাচ্ছে না।",
                "error_details": str(e),
                "proxy_error": str(proxy_err)
            })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
