import os
import sys
import subprocess

# ১. লাইব্রেরি অটো-ক্লোন ও পাথ সেটআপ
REPO_DIR = "Moviebox_API"
REPO_URL = "https://github.com/walterwhite-69/Moviebox-API.git"

if not os.path.exists(REPO_DIR):
    try:
        subprocess.run(["git", "clone", REPO_URL, REPO_DIR], check=True)
    except Exception:
        pass

base_path = os.path.abspath(REPO_DIR)
if base_path not in sys.path: sys.path.append(base_path)

from flask import Flask, jsonify, request

try:
    from moviebox_api.v1.core import Homepage, Search, MovieDetails, TVSeriesDetails
    from moviebox_api.v1.requests import Session
except ImportError:
    sub_path = os.path.abspath(os.path.join(REPO_DIR, "moviebox_api"))
    if sub_path not in sys.path: sys.path.append(sub_path)
    from moviebox_api.v1.core import Homepage, Search, MovieDetails, TVSeriesDetails
    from moviebox_api.v1.requests import Session

app = Flask(__name__)

# ==================== হোমপেজ ও সার্চ রুটস ====================
@app.route('/v1/homepage/banner', methods=['GET'])
def get_homepage_banner():
    hp = Homepage()
    return jsonify(hp.get_content_sync())

@app.route('/v1/search', methods=['GET'])
def search_v1():
    q = request.args.get('q', '')
    if not q: return jsonify({"status": "error", "message": "Missing query"})
    sh = Search(keyword=q)
    return jsonify(sh.get_content_sync())


# ==================== 🔥 ফিক্সড রুট ১: /detail/{slug} (র ডাটা প্রিন্ট করবে) ====================
@app.route('/detail/<path:slug>', methods=['GET'])
def get_movie_or_series_detail(slug):
    try:
        sess = Session()
        full_url = f"/detail/{slug}"
        
        if "tv" in slug.lower() or "series" in slug.lower():
            provider = TVSeriesDetails(full_url, session=sess)
        else:
            provider = MovieDetails(full_url, session=sess)
            
        # মুভিবক্স থেকে আসা একদম অরিজিনাল ডাটা সরাসরি রিটার্ন করবে
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
        
        if detail_path:
            full_url = detail_path if detail_path.startswith("http") or detail_path.startswith("/detail") else f"/detail/{detail_path}"
            
            # ১. মুভিবক্স থেকে ডাটা নিয়ে আসা
            if "tv" in detail_path.lower() or "series" in detail_path.lower():
                provider = TVSeriesDetails(full_url, session=sess)
            else:
                provider = MovieDetails(full_url, session=sess)
                
            raw_details = provider.get_content_sync()
            
            # resData বা ডিরেক্ট অবজেক্ট আনপ্যাক করা
            details_data = raw_details.get("resData", raw_details) if isinstance(raw_details, dict) else {}
            
            # স্ক্রিনশট অনুযায়ী আসল UID এবং সাবজেক্ট আইডি ব্যাকআপ বের করা
            real_uid = details_data.get("uid") or id
            
            # ২. মুভিবক্সের অফিশিয়াল মোবাইল/ওয়েব গেটওয়ে দিয়ে টোকেন বা ইউআরএল জেনারেট করা
            if "tv" in detail_path.lower() or "series" in detail_path.lower():
                # আমরা সেশন ব্যবহার করে তাদের ইন্টারনাল স্ট্রিমিং ইউআরএল ফরম্যাট তৈরি করছি
                # যেহেতু মেইন রেসপন্সে রেজোলিউশন ডাটা আছে, আমরা সরাসরি সোর্স গেটওয়ে হিট মারবো
                target_url = f"https://h5.aoneroom.com/wefeed-h5-bff/web/subject/play-info?subjectId={real_uid}&seasonNum={season_num}&episodeNum={episode_num}"
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
                    "Referer": "https://h5.aoneroom.com/",
                    "Accept": "application/json"
                }
                
                try:
                    res = sess.get(target_url, headers=headers)
                    api_res = res.json() if hasattr(res, 'json') else {}
                    play_data = api_res.get("data", {})
                    
                    # বিভিন্ন নেস্টেড ফিল্ড থেকে ইউআরএল চেক করা
                    addr_obj = play_data.get("playAddress") or play_data.get("videoAddress")
                    if addr_obj and isinstance(addr_obj, dict) and addr_obj.get("url"):
                        downloads_list.append({
                            "quality": addr_obj.get("definition", "HD"),
                            "url": addr_obj.get("url")
                        })
                except Exception:
                    pass

            # মুভি হলে ডিরেক্ট সোর্স
            else:
                v_addr = details_data.get("videoAddress")
                if isinstance(v_addr, dict) and v_addr.get("url"):
                    downloads_list.append({"quality": v_addr.get("definition", "HD"), "url": v_addr.get("url")})

            # ৩. স্ক্রিনশটের 'resolutions' স্ট্রাকচার থেকে ফলব্যাক হিসেবে ডাইনামিক সোর্স জেনারেট করা (লিংক ব্ল্যাঙ্ক থাকলে)
            if not downloads_list and isinstance(details_data, dict):
                resource_seasons = details_data.get("resource", {}).get("seasons", [])
                for s in resource_seasons:
                    if str(s.get("se")) == str(season_num):
                        for res_opt in s.get("resolutions", []):
                            # যদি এখানে ডিরেক্ট সোর্স ইউআরএল মাস্কড থাকে তবে তা অ্যাপেন্ড করা
                            if res_opt.get("url"):
                                downloads_list.append({
                                    "quality": f"{res_opt.get('resolution')}p",
                                    "url": res_opt.get("url")
                                })

            # ৪. শেষ ভরসা: ট্রেইলার/প্রিভিউ সোর্স
            if not downloads_list and isinstance(details_data, dict) and "trailer" in details_data:
                t_addr = details_data["trailer"].get("videoAddress", {})
                if t_addr and t_addr.get("url"):
                    downloads_list.append({"quality": "Preview", "url": t_addr.get("url")})

        return jsonify({
            "status": "success",
            "id": id,
            "real_uid": str(real_uid),
            "season": season_num,
            "episode": episode_num,
            "streams": downloads_list
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
