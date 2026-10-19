# 🌍 Lonely Planet 智能旅游指南 - 代码框架学习文档

## 📋 目录
1. [项目概述](#项目概述)
2. [架构设计](#架构设计)
3. [三个主要页面](#三个主要页面)
4. [核心服务模块](#核心服务模块)
5. [技术栈](#技术栈)
6. [数据流程](#数据流程)

---

## 项目概述

**项目名称**: You Loved Lonely Planet - 语义搜索 + LLM 驱动的旅游推荐应用
**框架**: Streamlit + Azure OpenAI + Sentence Transformers
**功能**: 智能旅游目的地推荐、天气预报、景点评分、酒店推荐

### 核心特性:
- 🔍 **语义搜索**: 基于 Lonely Planet 知识库的RAG (检索增强生成)
- 🤖 **AI 推荐**: Azure OpenAI GPT-4o-mini 生成个性化建议
- 🗺️ **交互式地图**: Folium 地图选择目的地
- 🌤️ **天气集成**: Open-Meteo API 实时天气数据
- 🎭 **景点数据库**: AI 生成的景点评分系统
- 🏨 **酒店推荐**: AI 生成的多档次酒店数据库

---

## 架构设计

```
┌─────────────────────────────────────────────────┐
│        Streamlit Web UI (前端)                   │
├─────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────┐  ┌────────────┐ │
│  │  Page 1:    │  │  Page 2: │  │  Page 3:   │ │
│  │ Map 选择器  │  │ 旅游计划 │  │  搜索系统  │ │
│  └─────────────┘  └──────────┘  └────────────┘ │
├─────────────────────────────────────────────────┤
│        业务逻辑层 (Service Layer)               │
├─────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────┐  │
│  │ 天气服务  │ 景点服务 │ 酒店服务 │ 地图服务   │
│  └──────────────────────────────────────────┘  │
├─────────────────────────────────────────────────┤
│        数据层 (Data Layer)                      │
├─────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────┐  │
│  │ Lonely Planet │ Open-Meteo │ Azure OpenAI  │
│  │  知识库 (PKL) │   天气API  │   LLM API      │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

---

## 三个主要页面

### 📍 第1页: 地图目的地选择 (render_destination_panel)
**位置**: `app_simplified_original.py` 第 ~380-395 行

**功能**:
- 交互式世界地图，标记所有可用目的地
- 三色标记系统: 🟢Green (有知识库) | ⚫Gray (无知识库)
- 下拉菜单选择国家
- 收藏夹功能 (可选)
- 国家图片走马灯显示

**关键函数**:
```python
render_destination_panel()          # 主渲染函数
image_carousel()                    # 图片轮播展示
```

**关键文件**:
- `map_selector.py` - 交互式地图实现
- `image_carousel.py` - 图片轮播组件

**当前问题**:
- 地图单纯显示，没有交互反馈
- 地图选择与下拉框没有联动
- 缺少"确认"按钮

---

### 📅 第2页: 旅游计划与天气 (render_travel_plan_page)
**位置**: `app_simplified_original.py` 第 ~1200-1500+ 行

**8个Tabs设计**:
1. **基本信息** - 旅行人数、目的地、日期、旅行天数
2. **偏好设定** - 旅游风格 (文化、美食、海滩等)
3. **预算设置** - 每人每日预算 (budget/舒适/奢华)
4. **景点选择** - AI推荐的景点，可多选
5. **🌤️ 天气预报** - 7日天气预报 (当前需要英语化)
6. **景点数据库** - 从 attractions_service.py 生成
7. **酒店搜索** - 从 hotels_service.py 生成
8. **奖励内容** - 待扩展

**天气Tab结构**:
```python
# 当前状态: 混合了中文和英文
fetch_weather_data(city_name, days=7)    # 获取天气
get_mock_weather(destination)             # 备选模拟数据

# 显示内容:
- 当前温度、湿度、风速
- 7日每日最高/最低温度
- 降水概率
- 天气描述 (中+英混合)
```

**问题**:
- 天气描述含有中文，需要英文版本
- 天气变化不跟踪城市切换
- 没有重新获取按钮

---

### 🔍 第3页: 语义搜索系统 (Main Tab Page)
**位置**: `app_simplified_original.py` 第 ~200-600 行

**功能**:
- **侧边栏** - 目的地封面、搜索参数(top-k)、API配置
- **主要搜索框** - 自然语言查询
- **RAG流程**: 语义搜索 → 上下文提取 → AI增强 → 答案生成
- **搜索结果** - Tabs显示相关文档片段

**核心RAG流程**:
```
用户查询 → 文本向量化 (Sentence Transformers)
  ↓
在知识库embeddings中搜索最相似的top-k个片段
  ↓
提取关键词和页码
  ↓
构建RAG提示词
  ↓
调用Azure OpenAI (GPT-4o-mini)
  ↓
生成智能回答 + 页码引用
```

---

## 核心服务模块

### 🌤️ weather_service.py
**功能**: 实时天气预报 + AI 活动推荐

**关键函数**:
```python
get_city_coordinates(city_name)        # 城市地理编码
fetch_weather_data(city_name, days=7)  # 获取7日预报
get_activity_recommendations()         # 根据天气推荐活动
get_weather_emoji()                    # 天气表情符号
get_mock_weather()                     # 模拟天气数据
```

**数据来源**: Open-Meteo API (免费，无需API密钥)

**当前问题**:
- 天气描述混合中英文
- 缺少对城市变化的响应

---

### 🎭 attractions_service.py
**功能**: AI生成景点数据库 + 评分系统

**关键函数**:
```python
generate_attractions_for_city()         # 生成景点列表
format_attractions_for_display()        # 格式化显示
get_attractions_summary()               # 摘要
```

**数据结构**:
```json
{
  "id": "unique_slug",
  "name": "景点名称",
  "rating": 4.7,
  "review_count": 3421,
  "emoji": "🎭",
  "type": "top|medium|worst",
  "category": "culture|nature|food|shopping",
  "why_popular": "为什么受欢迎",
  "entry_fee": "$12-15 USD",
  "operating_hours": "9:00 AM - 5:00 PM",
  "best_time_to_visit": "最佳参观时间",
  "pro_tips": ["技巧1", "技巧2"]
}
```

**需要增强**: 增加 Top Rated Restaurants

---

### 🏨 hotels_service.py
**功能**: AI生成酒店数据库 + 三档推荐

**关键函数**:
```python
generate_hotels_for_city()              # 生成酒店列表
format_hotels_for_display()             # 格式化显示
get_mock_hotels()                       # 模拟酒店数据
```

**三档酒店**:
- 💰 Budget: $30-60/night
- 🏨 Mid-range: $80-150/night
- 👑 Luxury: $200+/night

---

### 🗺️ map_selector.py
**功能**: 交互式Folium地图

**关键函数**:
```python
create_country_map()                    # 创建地图
render_interactive_map()                # 渲染地图
```

**地图标记系统**:
- 🟢 Green + ✅ 图标 = 有知识库 (15个国家)
- ⚫ Gray + 🚫 图标 = 无知识库

**需要改进**: 
- 缺少地图点击交互
- 缺少确认按钮反馈

---

## 技术栈

| 层级 | 技术 | 用途 |
|-----|------|------|
| **前端** | Streamlit 1.28+ | UI框架 |
| **地图** | Folium | 交互式地图 |
|  | streamlit-folium | Streamlit集成 |
| **向量搜索** | Sentence-Transformers | 文本向量化 |
|  | scikit-learn | KNN相似度搜索 |
| **LLM** | Azure OpenAI API | GPT-4o-mini |
| **天气** | Open-Meteo API | 实时天气 |
| **数据** | Pickle (.pkl) | Lonely Planet知识库 |
| **导出** | openpyxl | Excel生成 |
| **邮件** | smtplib | Gmail集成 |

---

## 数据流程

### 1️⃣ 启动应用流程
```
1. 初始化 Streamlit 配置
2. 加载知识库索引 (knowledge_bases/*.pkl)
3. 缓存 Sentence-Transformers 模型
4. 设置侧边栏参数
5. 渲染选中的页面
```

### 2️⃣ 语义搜索流程
```
用户输入查询 (如: "Bangkok 最好吃的食物")
  ↓
encode_query() → 向量 (384维)
  ↓
KNN搜索 → top-k相似文本块
  ↓
提取元数据 (页码、相关性%)
  ↓
构建RAG提示词with相关文本
  ↓
调用GPT-4o-mini生成答案 (可选)
  ↓
展示答案 + 来源文档
```

### 3️⃣ 天气数据流程
```
用户选择目的地
  ↓
extract_city_name(destination)
  ↓
get_city_coordinates(city_name)  ← 地理编码
  ↓
fetch_weather_data(lat, lon)     ← Open-Meteo API
  ↓
映射天气代码 → 描述 (中/英)
  ↓
显示7日预报卡片
```

### 4️⃣ 景点推荐流程
```
用户选择偏好 (文化、美食、冒险等)
  ↓
semantic_search(pref_query, country)  ← 在知识库中搜索
  ↓
ThreadPoolExecutor 并发调用
  ↓
generate_short_title() → 生成标题
generate_ai_enhanced_description() → 生成描述
  ↓
显示彩色卡片 (每个景点不同颜色)
  ↓
用户选择喜欢的景点
  ↓
生成行程表
```

---

## 文件结构

```
Your-Loved-Lonely-Planet-Semantic-Search-App-main/
│
├── app_simplified_original.py          # 主应用 (3000+ 行)
│
├── 服务层 (Service Layer)
│   ├── weather_service.py              # 天气预报服务
│   ├── attractions_service.py          # 景点生成服务
│   ├── hotels_service.py               # 酒店生成服务
│   ├── map_selector.py                 # 地图选择器
│   └── image_carousel.py               # 图片轮播
│
├── 数据层 (Data Layer)
│   ├── knowledge_bases/                # Lonely Planet知识库(.pkl)
│   │   ├── Austria.pkl
│   │   ├── Cambodia.pkl
│   │   ├── China.pkl
│   │   ├── ... (15个国家)
│   │
│   ├── book_picture/                   # 国家封面图片
│   │   ├── Austria/
│   │   ├── Cambodia/
│   │   └── ... (国家子文件夹)
│   │
│   └── cover_picture/                  # 封面图
│       ├── Austria.png
│       ├── Cambodia.png
│       └── ...
│
├── 配置与文档
│   ├── requirements.txt                # Python依赖
│   ├── QUICKSTART.md                   # 快速启动
│   ├── README.md                       # 项目说明
│   └── CODEBASE_FRAMEWORK_CN.md        # 本文档
│
└── 工具
    ├── test_weather_service.py         # 天气服务测试
    └── PUSH_TO_GITHUB.bat             # Git推送脚本
```

---

## 关键代码片段

### 语义搜索核心
```python
def semantic_search(query: str, country_name: str, top_k: int = 5):
    """在知识库中搜索最相似的文本块"""
    kb = load_knowledge_base(country_name)
    model = get_embedding_model()
    
    query_vec = model.encode([query], convert_to_numpy=True)  # 编码查询
    nn = NearestNeighbors(n_neighbors=min(top_k, len(kb["chunks"])))
    nn.fit(kb["embeddings"])
    
    distances, indices = nn.kneighbors(query_vec)
    similarities = 1 - distances[0]
    
    return results, similarities
```

### RAG提示词构建
```python
def build_rag_prompt(query: str, contexts: List[Dict]) -> str:
    """构建带上下文的提示词"""
    context_text = "\n\n".join([
        f"[Page {c['page']}, {c['relevance_pct']}]\n{c['text'][:1000]}"
        for c in contexts
    ])
    
    return f"""Based on these Lonely Planet excerpts:
{context_text}

Answer user question: {query}

Format:
**Keywords**: ...
**Detailed Suggestions**: ...
**Pro Tips**: ...
"""
```

### 天气数据映射
```python
WEATHER_DESCRIPTIONS = {
    0: 'Clear sky (晴天)',  # 需要改为英文Only
    1: 'Mainly clear (主要晴朗)',
    # ...更多代码
}
```

---

## 关键Session State变量

```python
st.session_state.plan_data = {
    "travelers": 1,                    # 旅行人数
    "start_date": datetime.date,       # 开始日期
    "end_date": datetime.date,         # 结束日期
    "destination": "Thailand",         # 目的地
    "preferences": ["美食", "文化"],   # 偏好列表
    "budget": 2500,                    # 每人每日预算
    "selected_attractions": [],        # 选中的景点
}

st.session_state.attractions = [...]   # AI推荐的景点列表
st.session_state.weather_data_7day = {} # 7日天气数据
```

---

## 性能优化

### 缓存策略
```python
@st.cache_resource           # 整个会话周期缓存
def get_embedding_model():
    return SentenceTransformer("...")

@st.cache_data(ttl=86400)   # 24小时缓存
def get_city_coordinates(city_name):
    # 地理编码结果
```

### 并发处理
```python
# 景点推荐使用多线程加速
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(...): i for i in range(10)}
    for future in as_completed(futures):
        attraction = future.result()
```

---

## 下一步改进方向

✅ **已完成**:
- 语义搜索 + RAG
- 天气集成
- 景点数据库
- 行程生成

🔄 **待改进**:
- ❌ 地图与下拉框联动 (需要完成)
- ❌ 天气英语化 (需要完成)
- ❌ 更多图片来源 (需要完成)
- ❌ Google Reviews集成
- ❌ Top Rated Restaurants (需要完成)
- 🔜 用户收藏功能
- 🔜 分享行程功能
- 🔜 多语言支持

---

## 调试技巧

### 启用调试模式
```python
# 侧边栏切换: "Show Debug Info"
# 显示:
- 检索到的文本块数量
- 平均相似度分数
- 提取的关键词
- 向量维度
```

### 测试天气服务
```bash
python test_weather_service.py
# 验证 Open-Meteo API 连接
```

### 查看知识库统计
```python
# 在 knowledge_bases/ 目录中查看
ls -lh knowledge_bases/ | grep .pkl
# 显示各国家知识库大小
```

---

## 常见问题解决

| 问题 | 症状 | 解决方案 |
|-----|------|---------|
| 知识库加载失败 | "No knowledge base found" | 检查 knowledge_bases/*.pkl 文件 |
| API认证失败 | "Authentication failed" | 在侧边栏输入有效的Azure OpenAI密钥 |
| 天气数据为空 | "Unable to determine" | 检查城市名称是否正确，Open-Meteo服务状态 |
| 地图不显示 | 空白区域 | 检查streamlit-folium是否安装 |
| 图片不显示 | 图片加载失败 | 检查 cover_picture/, book_picture/ 路径 |

---

**文档版本**: v1.0  
**最后更新**: 2026-03-20  
**作者**: Code Analysis

