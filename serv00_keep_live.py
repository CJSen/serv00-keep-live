import time
import hmac
import hashlib
import base64
import urllib.parse
import os
import requests
import paramiko
import json
import datetime

# 获取当前脚本文件的绝对路径
script_dir = os.path.dirname(os.path.abspath(__file__))
with open(f"{script_dir}/servers.json", "r") as f:
    configs = json.load(f)
    f.close()

# 存储结果
results = [f"========{datetime.datetime.now()}========"]


# 生成钉钉相关推送数据,返回调用机器人url
def return_ding_url() -> str:
    timestamp = str(round(time.time() * 1000))
    secret = configs.get("ding_info").get("secret")
    secret_enc = secret.encode("utf-8")
    string_to_sign = "{}\n{}".format(timestamp, secret)
    string_to_sign_enc = string_to_sign.encode("utf-8")
    hmac_code = hmac.new(
        secret_enc, string_to_sign_enc, digestmod=hashlib.sha256
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    access_token = configs.get("ding_info").get("access_token")
    url = f"https://oapi.dingtalk.com/robot/send?access_token={access_token}&timestamp={timestamp}&sign={sign}"
    return url


# 获取server配置,返回ssh client
def get_servers_client(ser_name):
    config = configs.get("servers")
    # 连接远程服务器
    user = config[ser_name]["user"]
    host = config[ser_name]["host"]
    port = config[ser_name]["port"]
    pwd = config[ser_name]["pwd"]
    # 创建SSH对象
    client = paramiko.SSHClient()
    # 允许连接不在know_hosts文件中的主机
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # 连接服务器
    try:
        client.connect(hostname=host, port=port, username=user, password=pwd)
    except Exception as e:
        global results
        results.append(f"{ser_name}: {e}")
        return client, 0
    transport = client.get_transport()
    if transport.is_alive():
        return client, 1
    return client, 0


# 执行相关命令
def execute_the_command():
    global results
    for server in configs["servers"]:

        # 如果配置不连接，则跳过
        if not configs["servers"][server]["connect"]:
            continue
        results.append(f"\n***开始连接:{server}...")
        client, is_alive = get_servers_client(server)
        if not is_alive:
            results.append(f"{server}: ssh 连接失败")
            client.close()
            continue

        # 执行每条命令并获取返回结果
        commands = [
            "date",
            "echo hello from: $USER !!!"
        ]
        try:
            for command in commands:
                stdin, stdout, stderr = client.exec_command(command)
                # 读取标准输出和标准错误
                output = stdout.read().decode()
                error = stderr.read().decode()
                results.append((output if output else error).replace("\n", ""))
        except paramiko.SSHException as e:
            results.append(f"连接异常: {e}")
        finally:
            client.close()  # 关闭SSHClient


execute_the_command()

# 并将日志文件将保存在脚本所在的目录中
log_file_path = os.path.join(script_dir, "serv00_keep_live.log")
ding_markdown = "### serv00自动保活 \n"
for result in results:
    ding_markdown += f"#### {result}\n "
    os.system(f"echo '{result}' >> {log_file_path}")
req = requests.post(
    url=return_ding_url(),
    json={
        # markdown消息
        "msgtype": "markdown",
        "markdown": {"title": "serv00自动保活", "text": ding_markdown},
    },
)
os.system(f"echo 钉钉消息推送结果：{req.json()} '\n\n\n' >> {log_file_path}")
