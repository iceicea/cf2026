"""
乘风2026 投票数据采集脚本
由 GitHub Action 每5分钟调用一次
从芒果TV API 获取最新票数，追加到 data.json
"""
import json
import time
import urllib.request
import os

API_URL = "https://vote.api.mgtv.com/chengfeng/query_vote_list"
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
USER_AGENT = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"


def fetch_vote_data():
    """从 API 获取投票数据"""
    params = f"request_time={int(time.time() * 1000)}"
    url = f"{API_URL}?{params}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Referer", "https://lego.mgtv.com/")
    req.add_header("Origin", "https://lego.mgtv.com")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("errno") == 0:
                return data["data"]["vote_list"]
            print(f"API error: {data.get('errmsg', 'unknown')}")
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None


def load_history():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            pass
    return {"timestamps": [], "contestants": {}}


def save_history(history):
    tmp_file = DATA_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, DATA_FILE)


def main():
    print(f"[collect.py] 开始采集...")
    vote_list = fetch_vote_data()
    if not vote_list:
        print("[collect.py] 获取数据失败，退出")
        exit(1)

    history = load_history()
    now_ts = int(time.time())

    # 检查是否需要新增数据点（避免同一分钟内重复采集）
    if history["timestamps"]:
        last_ts = history["timestamps"][-1]
        # 如果距离上次采集不到3分钟且不是第一次，跳过
        if now_ts - last_ts < 180 and len(history["timestamps"]) > 1:
            print(f"[collect.py] 距上次采集仅 {now_ts - last_ts} 秒，跳过")
            exit(0)

    history["timestamps"].append(now_ts)

    for item in vote_list:
        name = item["vote_name"]
        ha_val = 0
        ga_val = 0
        for opt in item["option_name"]:
            if opt["option_name"] == "夯爆了":
                ha_val = opt["option_vote_number"]
            elif opt["option_name"] == "尬场了":
                ga_val = opt["option_vote_number"]

        if name not in history["contestants"]:
            history["contestants"][name] = {
                "vote_id": item["vote_id"],
                "song": item["song_name"],
                "夯爆了": [],
                "尬场了": [],
            }

        c = history["contestants"][name]
        c["夯爆了"].append(ha_val)
        c["尬场了"].append(ga_val)

    # 补齐可能缺失的数据
    ts_len = len(history["timestamps"])
    for c in history["contestants"].values():
        while len(c["夯爆了"]) < ts_len:
            last = c["夯爆了"][-1] if c["夯爆了"] else 0
            c["夯爆了"].append(last)
        while len(c["尬场了"]) < ts_len:
            last = c["尬场了"][-1] if c["尬场了"] else 0
            c["尬场了"].append(last)

    save_history(history)

    # 打印摘要
    incs = []
    for name, c in history["contestants"].items():
        ha = c["夯爆了"]
        if len(ha) >= 2:
            inc = ha[-1] - ha[-2]
            incs.append((name, inc, ha[-1]))
    incs.sort(key=lambda x: x[1], reverse=True)

    print(f"[collect.py] ✅ 采集成功! 数据点: {len(history['timestamps'])}, 选手: {len(history['contestants'])}")
    print(f"[collect.py] Top 5 增量: " + ", ".join(f"{n} +{i:,}" for n, i, _ in incs[:5]))


if __name__ == "__main__":
    main()
