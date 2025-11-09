import warnings

warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API.*",
    category=UserWarning
)

import pysnowball as ball
from datetime import datetime, timedelta, time as dtime, UTC
from apscheduler.schedulers.background import BackgroundScheduler
import configparser
import requests
import json
import os
import pytz
import signal
import sys
import random

# --- 新增的邮件库 ---
import smtplib
import ssl
from email.message import EmailMessage


# --- 结束 ---

# --- 核心修复：让 configparser 保持大小写 ---
class CaseSensitiveConfigParser(configparser.ConfigParser):
    def optionxform(self, optionstr):
        return optionstr


# --- 修复结束 ---

# 读取配置文件
config = CaseSensitiveConfigParser()
config.read("config.ini", encoding='utf-8')

# [default] 配置
sct_send_key = config.get('default', 'sct_send_key', fallback='')
xq_a_token = config.get('default', 'xq_a_token', fallback='')
u = config.get('default', 'u', fallback='')
interval_type = config.get('default', 'interval_type', fallback='minutes')
interval_value = config.getfloat('default', 'interval_value', fallback=30.0)
xq_id_token = config.get('default', 'xq_id_token', fallback='')
xq_r_token = config.get('default', 'xq_r_token', fallback='')

# --- 新增：读取 [smtp] 配置 ---
smtp_host = config.get('smtp', 'host', fallback=None)
smtp_port = config.getint('smtp', 'port', fallback=465)
smtp_user = config.get('smtp', 'user', fallback=None)
smtp_password = config.get('smtp', 'password', fallback=None)

# --- 新增：读取 [notify_mapping] 配置 ---
notify_mapping = {}
if config.has_section('notify_mapping'):
    # 现在这里会读取到带大写的键 (e.g., 'ZH1004909')
    notify_mapping = dict(config.items('notify_mapping'))

# 要监控的ID列表，直接从 mapping 的键中获取
cube_ids = list(notify_mapping.keys())
if not cube_ids:
    print("❌ 错误：未在 config.ini 的 [notify_mapping] 中配置任何组合ID。")
    sys.exit(1)
if not smtp_user or not smtp_password:
    print("⚠️ 警告：未在 config.ini 的 [smtp] 中配置邮箱信息，将无法发送邮件通知。")

print(f"将要监控的组合ID: {', '.join(cube_ids)}")

processed_ids_file = "processed_ids.json"


def load_processed_ids():
    if os.path.exists(processed_ids_file):
        try:
            with open(processed_ids_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list):
                return set(data)
            else:
                print("文件内容不是列表，自动重置为空列表")
                with open(processed_ids_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                return set()
        except json.JSONDecodeError as e:
            print(f"文件内容无法解析为JSON（{e}），自动重置为空列表")
            with open(processed_ids_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            return set()
        except Exception as e:
            print(f"加载文件时发生错误（{e}），自动重置为空列表")
            with open(processed_ids_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            return set()
    else:
        print(f"{processed_ids_file}文件不存在，自动创建")
        with open(processed_ids_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return set()


processed_ids = load_processed_ids()

# 构建Cookie
cookie_parts = []
if xq_a_token:
    cookie_parts.append(f"xq_a_token={xq_a_token}")
if u:
    cookie_parts.append(f"u={u}")
if xq_id_token:
    cookie_parts.append(f"xq_id_token={xq_id_token}")
if xq_r_token:
    cookie_parts.append(f"xq_r_token={xq_r_token}")
cookie = ";".join(cookie_parts)
if cookie:
    ball.set_token(cookie)
    print("Cookie 已设置 (注意: pysnowball 库不支持全局超时)")


# 时间转换 (保持不变)
def format_timestamp_with_timezone_adjustment(timestamp, hours=0):
    dt_obj = datetime.fromtimestamp(timestamp / 1000, tz=UTC)
    dt_obj = dt_obj + timedelta(hours=hours)
    return dt_obj.astimezone(pytz.timezone('Asia/Shanghai')).strftime('%Y.%m.%d %H:%M:%S')


# Server酱推送 (保持不变, 可选)
def send_serverchan_message(content):
    if not sct_send_key:
        print("⚠️ 未配置Server酱SendKey，跳过推送")
        return
    url = f"https://sctapi.ftqq.com/{sct_send_key}.send"
    data = {
        "title": "雪球组合新调仓通知",
        "desp": content
    }
    try:
        response = requests.post(url, data=data, timeout=10)
        result = response.json()
        if result.get("code") == 0:
            print("✅ Server酱消息发送成功")
        else:
            print(f"❌ Server酱消息发送失败：{result.get('message', '未知错误')}")
    except Exception as e:
        print(f"❌ 发送Server酱消息时出错：{e}")


# --- 邮件推送功能 ---
def send_email_notification(recipient_email, title, content):
    if not smtp_host or not smtp_user or not smtp_password:
        print(f"⚠️ 邮箱SMTP未配置，跳过向 {recipient_email} 的邮件推送")
        return

    msg = EmailMessage()
    msg['Subject'] = title
    msg['From'] = smtp_user
    msg['To'] = recipient_email

    content_html = f"<pre style='font-family: monospace; white-space: pre-wrap;'>{content}</pre>"
    msg.set_content("请使用支持HTML的邮件客户端查看此消息。")
    msg.add_alternative(content_html, subtype='html')

    try:
        context = ssl.create_default_context()
        print(f"正在尝试向 {recipient_email} 发送邮件...")
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            print(f"✅ 邮件成功发送至: {recipient_email}")
    except Exception as e:
        print(f"❌ 向 {recipient_email} 发送邮件时出错: {e}")
        if "Authentication failed" in str(e) or "535" in str(e):
            print("❌ 认证失败！请检查 [smtp] 配置中的 user 和 password (授权码) 是否正确。")


# 保存ID (保持不变)
def save_processed_ids():
    try:
        with open(processed_ids_file, 'w', encoding='utf-8') as f:
            json.dump(list(processed_ids), f)
        print("已处理ID保存成功")
    except Exception as e:
        print(f"保存已处理ID时出错: {e}")


# --- 核心修改：监控与分发逻辑 ---
def monitor_rebalancing_operations():
    # 遍历所有在 [notify_mapping] 中配置的 cube_id
    # 现在 cube_id 会是 'ZH1004909' (保留大写)
    for cube_id in cube_ids:
        try:
            quote_response = ball.quote_current(cube_id)
            if not quote_response:
                continue
            quote_info = quote_response.get(cube_id, {})
            name = quote_info.get("name", "未知名称")

            rebalancing_response = ball.rebalancing_current(cube_id)
            if not rebalancing_response:
                continue
            last_rb = rebalancing_response.get('last_rb')

            if last_rb and last_rb.get('id') not in processed_ids:
                content = f"检测到新调仓操作，组合ID: {cube_id}\n"
                content += f"组合名称: {name}\n"
                content += f"  最新的一次调仓:\n"
                content += f"    调仓ID: {last_rb.get('id')}\n"
                content += f"    调仓状态: {last_rb.get('status')}\n"

                created_at_val = last_rb.get('created_at')
                if created_at_val:
                    created_at = format_timestamp_with_timezone_adjustment(created_at_val)
                    content += f"    调仓时间: {created_at}\n"
                else:
                    content += "    调仓时间: 未知\n"

                rebalancing_id = last_rb.get('id')
                processed_ids.add(rebalancing_id)

                history_response = ball.rebalancing_history(cube_id, 5, 1)
                if not history_response:
                    continue
                history_list = history_response.get('list', [])

                found_history = False
                for history_item in history_list:
                    if history_item.get('id') == rebalancing_id:
                        found_history = True
                        rebalancing_items = history_item.get('rebalancing_items', [])
                        if not rebalancing_items:
                            rebalancing_items = history_item.get('rebalancing_histories', [])

                        if not rebalancing_items:
                            content += "    (未获取到详细调仓股票列表)\n"

                        for item in rebalancing_items:
                            stock_name = item.get('stock_name', '未知股票')
                            stock_symbol = item.get('stock_symbol', item.get('stock_code', '未知代码'))

                            prev_weight = item.get('prev_weight') or 0
                            target_weight = item.get('target_weight', item.get('weight')) or 0

                            price = item.get('price', '未知价格')

                            content += f"    股票信息: {stock_name}（{stock_symbol}）\n"
                            content += f"    调仓价格: {price}\n"
                            content += f"    调仓结果: {prev_weight}% → {target_weight}%\n"

                if not found_history:
                    content += "    (未在最近5次历史中匹配到此调仓ID的详情)\n"

                # --- (推送逻辑修改) ---
                print(content)  # 打印日志

                # 1. (可选) 推送给 Server酱 (全局通知)
                if sct_send_key:
                    send_serverchan_message(content)

                # 2. (核心) 根据 mapping 推送给指定邮箱
                recipients_str = notify_mapping.get(cube_id)
                if recipients_str:
                    recipients = [email.strip() for email in recipients_str.split(',') if email.strip()]
                    email_title = f"雪球组合 {name} 新调仓通知"
                    for email_addr in recipients:
                        send_email_notification(email_addr, email_title, content)
                else:
                    print(f"⚠️ 组合 {cube_id} 触发了调仓，但在 [notify_mapping] 中未找到对应的通知邮箱。")

                save_processed_ids()
        except Exception as e:
            # 捕获API调用期间发生的任何错误
            # "该组合不存在" 错误也会在这里被捕获并打印
            print(f"监控组合ID {cube_id} 时发生错误: {e}")


# --- (以下代码保持不变) ---

# 全天候监控
def job():
    t = convert_interval_to_str(interval_type, interval_value)
    print(
        f"正在查询中... 当前时间 {datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y.%m.%d %H:%M:%S')} , 下一次执行 {t} 后")
    monitor_rebalancing_operations()


# 退出逻辑
def signal_handler(sig, frame):
    print('程序中断。')
    if scheduler and scheduler.running:
        scheduler.shutdown()
    sys.exit(0)


def convert_interval_to_str(interval_type, interval_value):
    if interval_type == 'seconds':
        return f"{int(interval_value)}秒"
    elif interval_type == 'minutes':
        return f"{int(interval_value)}分"
    elif interval_type == 'hours':
        return f"{int(interval_value)}小时"
    else:
        return f"{int(interval_value)}分"


# 注册信号处理
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

scheduler = BackgroundScheduler(timezone=pytz.timezone('Asia/Shanghai'))

interval_mapping = {
    'seconds': 'seconds',
    'minutes': 'minutes',
    'hours': 'hours'
}

interval_key = interval_mapping.get(interval_type, 'minutes')

scheduler.add_job(
    job,
    'interval',
    **{interval_key: interval_value},
    max_instances=5
)

print("开始全天候监控 (已支持邮件分发)...")
job()
scheduler.start()

try:
    while True:
        pass
except (KeyboardInterrupt, SystemExit):
    signal_handler(None, None)