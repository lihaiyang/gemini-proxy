#coding:utf-8
import http.server
import urllib.request
from urllib.error import HTTPError
import threading
import itertools
import json
import sys

# 1. 从配置文件加载 API 服务配置
API_CONFIGS = []
api_counter = None
api_lock = threading.Lock()

def load_api_configs():
    """
    从 config.json 加载 API 配置。
    """
    global API_CONFIGS, api_counter
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            API_CONFIGS = config.get('api_configs', [])
            if not API_CONFIGS:
                print("Error: 'api_configs' not found or empty in config.json.")
                sys.exit(1)
            api_counter = itertools.cycle(range(len(API_CONFIGS)))
    except FileNotFoundError:
        print("Error: config.json not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Could not decode config.json.")
        sys.exit(1)

# 在程序启动时加载配置
load_api_configs()

# 3. 创建一个函数来获取下一个 API 配置
def get_next_api_config():
    """
    使用线程安全的轮询算法获取下一个 API 配置。
    """
    with api_lock:
        config_index = next(api_counter)
    return API_CONFIGS[config_index]

class ProxyHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    一个反向代理请求处理器，
    将客户端请求通过负载均衡转发到多个上游服务器。
    """

    def _forward_request(self, method):
        """
        一个通用的请求转发函数，处理 GET 和 POST 请求。
        """
        # 4. 获取下一个 API 配置
        api_config = get_next_api_config()
        print(f"Using API key: {api_config.get('name', 'Unnamed')}")
        
        # 5. 构建目标 URL
        target_url = f"{api_config['base_url']}{self.path}"
        
        # 准备转发的请求
        request_headers = dict(self.headers)
        
        # Host 头需要设置为上游服务器的地址
        request_headers["Host"] = urllib.parse.urlparse(target_url).netloc
        
        # 6. 将 API 密钥添加到请求头
        request_headers["x-goog-api-key"] = api_config["api_key"]
        
        # 读取请求体（如果是 POST 请求）
        request_body = None
        if method == 'POST':
            content_length = int(self.headers.get('Content-Length', 0))
            request_body = self.rfile.read(content_length)

        # 创建一个新的请求对象
        proxy_request = urllib.request.Request(
            target_url,
            data=request_body,
            headers=request_headers,
            method=method
        )

        try:
            # 发送请求到上游服务器
            with urllib.request.urlopen(proxy_request) as response:
                # 将上游服务器的响应返回给客户端
                self.send_response(response.status)
                
                # 复制响应头
                for key, value in response.getheaders():
                    if key.lower() not in ('transfer-encoding', 'content-encoding'):
                        self.send_header(key, value)
                self.end_headers()
                
                # 复制响应体
                self.wfile.write(response.read())

        except HTTPError as e:
            # 处理上游服务器返回的 HTTP 错误
            self.send_response(e.code)
            for key, value in e.headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            # 处理其他网络或请求错误
            self.send_error(502, f"Proxy Error: {e}")

    def do_GET(self):
        """处理 GET 请求。"""
        self._forward_request('GET')

    def do_POST(self):
        """处理 POST 请求。"""
        self._forward_request('POST')

def run(server_class=http.server.HTTPServer, handler_class=ProxyHTTPRequestHandler, port=8888):
    """
    启动 HTTP 服务器。
    """
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting proxy server on port {port}...")
    print(f"Load balancing across {len(API_CONFIGS)} API services.")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
