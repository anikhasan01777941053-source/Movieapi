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


# ==================== ৩. ভিডিও ডাউনলোড লিংক জেনারেটর (ফাইনাল হেডার বাইপাস) ====================

@app.route('/v1/download', methods=['GET'])
def get_download_urls():
    detail_path = request.args.get('path', '')
    item_type = request.args.get('type', 'movie')
    
    if not detail_path:
        return jsonify({"status": "error", "message": "Parameter 'path' is missing"})
        
    try:
        sess = Session()
        full_url = detail_path if detail_path.startswith("http") or detail_path.startswith("/detail") else f"/detail/{detail_path}"

        # ১. প্রথমে মুভি বা সিরিজের আইডি (subjectId) বের করার জন্য ডিটেইলস নিয়ে আসা
        if item_type.lower() == 'series' or 'tv' in detail_path.lower():
            provider = TVSeriesDetails(full_url, session=sess)
        else:
            provider = MovieDetails(full_url, session=sess)
            
        details_data = provider.get_content_sync()
        
        # জেসন থেকে মেইন সাবজেক্ট আইডি তুলে নেওয়া
        subject_id = details_data.get("subjectId") or details_data.get("subject", {}).get("subjectId")
        
        if not subject_id:
            return jsonify({"status": "error", "message": "Subject ID could not be extracted", "data": details_data})

        # ২. মুভিবক্সের নিজস্ব ডাউনলোড এপিআই-তে রিকোয়েস্ট পাঠানো (উইথ পারফেক্ট ব্রাউজার হেডার)
        download_api_url = f"https://h5.aoneroom.com/wefeed-h5-bff/web/subject/download?subjectId={subject_id}&se=1&ep=1"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://fmoviesunblocked.net/",
            "Origin": "https://h5.aoneroom.com",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Platform": "web"
        }

        # পাইথনের নিজস্ব ক্লায়েন্ট দিয়ে কুকি এবং হেডারসহ রিকোয়েস্ট এক্সেকিউট করা
        with httpx.Client(headers=headers, follow_redirects=True) as client:
            response = client.get(download_api_url)
            video_json = response.json()

        # যদি ডাউনলোড ডাটা সাকসেসফুলি চলে আসে
        if video_json.get("data", {}).get("downloads") or video_json.get("data", {}).get("hasResource"):
            return jsonify({
                "status": "success",
                "item_type": item_type,
                "subject_id": subject_id,
                "data": video_json.get("data")
            })
        
        # কোনো কারণে ফাঁকা আসলে ব্যাকআপ হিসেবে র ডিটেইলস ডাটাটাই ফেরত পাঠানো
        return jsonify({
            "status": "success",
            "note": "Raw details bypass",
            "data": details_data
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "লিংক জেনারেট করতে সমস্যা হয়েছে।",
            "error_details": str(e)
        })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
