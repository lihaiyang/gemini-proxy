# gemini-proxy

### 功能
本地启动一个反向代理，将LLM的请求转发至google gemini，支持多个key轮询以提高额度。

### 配置
编辑config.json文件，填入自己的key。可以填写多个，name只是一个标识，并不影响功能。

### 启动
在本目录下
`python gemini-proxy.py`
