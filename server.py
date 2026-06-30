import os
import asyncio
from flask import Flask, jsonify, request

# মুভিবক্সের আসল মডিউলগুলো ইমপোর্ট করা হচ্ছে
from moviebox_api.v1.core import Homepage, Search, MovieDetails, TVSeriesDetails

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
            # নির্দিষ্ট পজিশনের আইটেম নেওয়া হচ্ছে
            section = operating_list[index_num]
            
            # আপনার ৩ নম্বর স্ক্রিনশটের স্ট্রাকচার অনুযায়ী items বের করা হচ্ছে
            banner_data = section.get("banner", {}) if section else {}
            items = banner_data.get("items", []) if banner_data else []
            
            return {"status": "success", "count": len(items), "data": items}
            
        return {"status": "success", "count": 0, "data": []}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ==================== ১. হোমপেজের ভাগ ভাগ করা সব ক্যাটাগরি (ইন্ডেক্স অনুযায়ী) ====================

@app.route('/v1/homepage/banner', methods=['GET'])
def get_homepage_banner():
    """টপ স্লাইডার ব্যানার"""
    try:
        raw_json = get_homepage_raw_data()
        banner_data = raw_json.get("banner", {})
        items = banner_data.get("items", []) if banner_data else []
        return jsonify({"status": "success", "count": len(items), "data": items})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/v1/homepage/trending', methods=['GET'])
def get_homepage_trending():
    """১ম ক্যাটাগরি (Trending Now) - ইন্ডেক্স ০"""
    return jsonify(get_items_by_index(0))

@app.route('/v1/homepage/cinema', methods=['GET'])
def get_homepage_cinema():
    """২য় ক্যাটাগরি (Cinema) - ইন্ডেক্স ১"""
    return jsonify(get_items_by_index(1))

@app.route('/v1/homepage/hotshort', methods=['GET'])
def get_homepage_hotshort():
    """৩য় ক্যাটাগরি (Hot Short TV) - ইন্ডেক্স ২"""
    return jsonify(get_items_by_index(2))

@app.route('/v1/homepage/popular', methods=['GET'])
def get_homepage_popular():
    """৪র্থ ক্যাটাগরি (Popular/Bollywood) - ইন্ডেক্স ৩"""
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


# ==================== ৩. ভিডিও ডাউনলোড ও আসল স্ট্রিম ইউআরএল ====================

@app.route('/v1/download', methods=['GET'])
def get_download_urls():
    provider = MovieDetails(detail_path=detail_path)
    item_type = request.args.get('type', 'movie')
    
    if not provider:
        return jsonify({"status": "error", "message": "Parameter 'path' (provider) is missing"})
        
    try:
        # আমরা ট্রাই করছি দেখার জন্য যে এই ক্লাসের ভেতরে কী কী প্যারামিটার নেওয়া সম্ভব
        import inspect
        try:
            # মুভির জন্য চেক
            sig = inspect.signature(MovieDetails.__init__)
            params = list(sig.parameters.keys())
        except Exception:
            params = ["unknown"]

        # এবার আপনার মডিউল অনুযায়ী সঠিক প্যারামিটারটি খুঁজে নিয়ে অবজেক্ট তৈরি করা
        if 'detail_path' in params:
            provider = MovieDetails(detail_path=detail_path)
        elif 'path' in params:
            provider = MovieDetails(path=detail_path)
        elif 'id' in params:
            provider = MovieDetails(id=detail_path)
        elif 'url' in params:
            provider = MovieDetails(url=detail_path)
        else:
            # যদি এর কোনোটিই না মিলে, তবে মেইন আর্গুমেন্ট যেটা প্রথম পজিশনে আছে সেটা দেওয়া
            provider = MovieDetails(detail_path)
            
        video_data = run_async(provider.get_content())
        return jsonify({"status": "success", "data": video_data})
        
    except Exception as e:
        # এখানে আমরা মডিউলের আসল প্যারামিটার লিস্ট এবং এরর একসাথে দেখাবো যেন ১ বারেই ফিক্স হয়
        import inspect
        try:
            m_params = str(inspect.signature(MovieDetails.__init__))
            t_params = str(inspect.signature(TVSeriesDetails.__init__))
        except:
            m_params = "N/A"
            t_params = "N/A"
            
        return jsonify({
            "status": "error", 
            "message": str(e),
            "MovieDetails_expects": m_params,
            "TVSeriesDetails_expects": t_params
        })
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

