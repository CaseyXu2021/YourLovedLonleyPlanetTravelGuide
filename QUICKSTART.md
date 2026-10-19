# 🚀 快速开始指南 (Quick Start Guide)

## 15分钟内开始使用

### 第1步：准备环境 (Setup Environment)
```bash
# 1. 进入项目目录
cd "D:\Your-Loved-Lonely-Planet-Semantic-Search-App_v2\Your-Loved-Lonely-Planet-Semantic-Search-App-main"

# 2. 确保虚拟环境已激活
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# 3. 升级pip
python -m pip install --upgrade pip

# 4. 安装/更新所需库
pip install -r requirements.txt
```

### 第2步：验证天气服务 (Verify Weather Service)
```bash
# 运行测试脚本，验证所有API都工作正常
python test_weather_service.py

# 预期输出：
# ✅ Open-Meteo Weather API: Connected
# ✅ Open-Meteo Geocoding API: Connected
# ✅ 多个城市的天气数据正确获取
```

### 第3步：启动应用 (Start Application)
```bash
# 启动Streamlit应用
streamlit run app_simplified_original.py

# 浏览器会自动打开：http://localhost:8501
```

---

## 🎯 核心功能快速演示 (Feature Demo)

### 🔍 Smart Search 模式
1. 在侧栏选择一个国家
2. 输入旅行问题（例如："What are best attractions?"）
3. 点击"Search & Analyze"
4. 查看AI推荐

### ✈️ Create Plan 模式（新增天气功能）

#### 步骤1：基本信息
```
✏️ 填写表单：
- 旅行人数：2
- 目的地：Paris
- 出发日期：2026-03-20
- 结束日期：2026-03-25
↓
🌤️ 自动显示Paris的实时天气和5天预报
```

#### 步骤2：偏好选择
```
☑️ 勾选喜欢的活动类型：
- Cultural & History
- Food & Cuisine
- Photography
- ...
```

#### 步骤3：预算设置
```
💰 设置您的日均预算：
- 选择预算等级（Budget/Comfortable/Luxury）
- 或手动滑块调整（$50-$500）
```

#### 步骤4：景点推荐
```
🏛️ 点击"Get Recommendations"
- 查看10个推荐景点
- 勾选感兴趣的景点
```

#### 步骤5：生成行程
```
📝 点击"Generate Detailed Itinerary"
↓
AI包含天气因素生成智能行程
↓
📅 显示天气预报卡片
🎯 显示每日活动建议
💰 显示预算分析
↓
📥 下载Excel或📧 发送邮箱
```

---

## ⚙️ 核心代码使用示例 (Code Examples)

### 获取天气数据
```python
from weather_service import weather_service

# 获取指定城市的天气
weather = weather_service.get_weather("Paris")

# 访问当前天气
temp = weather['current']['temp']          # 温度
condition = weather['current']['condition'] # 天气状况
humidity = weather['current']['humidity']   # 湿度
wind = weather['current']['wind']           # 风速

# 访问预报
for day in weather['forecast']:
    print(f"{day['day']}: {day['temp_min']}°C ~ {day['temp_max']}°C")
```

### 获取活动推荐
```python
from weather_service import get_activity_recommendations

activities = get_activity_recommendations(weather)
# 返回: ["Beach", "Water Sports", "Picnic", ...]

for activity in activities:
    print(f"🎯 {activity}")
```

### 在AI提示中使用天气
```python
# 现有代码已集成，调用方式：
itinerary = generate_itinerary(
    days=5,
    attractions=[...],
    budget=2000,
    preferences=["Beach", "Food"],
    destination="Paris",
    weather_data=weather,  # 新增参数
    api_key=AZURE_API_KEY
)
```

---

## 📊 数据流示例 (Data Flow Example)

```
用户选择目的地 (User selects destination)
        ↓
调用 weather_service.get_weather("Paris")
        ↓
Geocoding API: "Paris" → (48.8566, 2.3522)
        ↓
Weather API: 获取实时和预报数据
        ↓
数据缓存24小时 (Cache for 24 hours)
        ↓
在UI显示天气信息 (Display in UI)
显示5天预报卡片 (5-day forecast cards)
推荐合适的活动 (Recommend activities)
        ↓
生成行程时，AI考虑天气因素
(AI generates itinerary considering weather)
        ↓
最终行程包含天气适应性安排
(Final itinerary includes weather-adapted activities)
```

---

## 🔧 常见操作 (Common Operations)

### 操作1：强制刷新天气数据
```bash
# 重启应用（Streamlit会清除缓存）
streamlit run app_simplified_original.py
```

### 操作2：修改缓存时间
编辑 `weather_service.py`：
```python
@st.cache_data(ttl=86400)  # 24小时，修改数字为秒数
def get_city_coordinates(city_name: str):
    ...
```

### 操作3：测试特定城市
```python
# 在Python终端运行
from weather_service import weather_service

weather = weather_service.get_weather("Tokyo")
print(weather)
```

### 操作4：禁用缓存（调试）
```python
# 修改weather_service.py中的装饰器
@st.cache_data(ttl=0)  # ttl=0表示禁用缓存
```

---

## 🐛 故障排除 (Troubleshooting)

### 问题1：API连接失败
```
❌ 错误信息: "Unable to fetch real weather data"
✅ 解决方案:
   1. 检查网络连接
   2. 运行: python test_weather_service.py
   3. 应用使用模拟数据继续运行
```

### 问题2：城市未被识别
```
❌ 错误: 找不到城市
✅ 解决方案:
   1. 使用完整城市名称，如"Paris, France"
   2. 尝试英文名称
   3. 查看test_weather_service.py中的支持城市列表
```

### 问题3：天气信息不刷新
```
❌ 显示过时数据
✅ 解决方案:
   1. 清除浏览器缓存
   2. 重启Streamlit应用
   3. Ctrl+C 停止，重新运行
```

### 问题4：AI历史记录混乱
```
❌ 不同城市数据混淆
✅ 解决方案:
   1. Streamlit侧栏 → "Clear cache"
   2. 刷新浏览器
   3. 重新启动应用
```

---

## 📈 性能优化 (Performance Tips)

### ✅ 已优化的方面
- 天气数据缓存24小时
- 异步API调用
- 智能回退机制（网络失败时使用模拟数据）

### 🚀 如何获得更快的性能
```python
# 1. 减少顶K（search results）
search_top_k = 3  # 改为 3 而非 5

# 2. 减少预报天数（在generate_itinerary中）
forecast_days = 3  # 改为 3而非 5

# 3. 增加缓存时间
@st.cache_data(ttl=172800)  # 改为 48小时
```

---

## 🎓 学习资源 (Learning Resources)

### 关键文件说明
| 文件 | 说明 | 修改频率 |
|-----|------|--------|
| `weather_service.py` | 天气服务模块 | 低 |
| `app_simplified_original.py` | 主应用 | 中 |
| `test_weather_service.py` | 测试脚本 | 低 |
| `WEATHER_INTEGRATION_README.md` | 详细文档 | 低 |
| `requirements.txt` | 依赖列表 | 低 |

### 文档阅读顺序
1. 📄 本文件（快速开始）- 5分钟
2. 📄 INTEGRATION_COMPLETE.md - 10分钟
3. 📄 WEATHER_INTEGRATION_README.md - 15分钟
4. 💻 查看源代码 - 按需

---

## 🎉 成功指标 (Success Checklist)

完成以下项目表示集成成功：

- [ ] ✅ test_weather_service.py 运行成功
- [ ] ✅ API连接测试通过
- [ ] ✅ 应用启动无错误
- [ ] ✅ 能够显示实时天气
- [ ] ✅ 能够生成带天气的行程
- [ ] ✅ 能够下载Excel或发送邮箱

---

## 💡 下一步 (Next Steps)

### 即刻可做
1. ✅ 尝试生成旅行计划
2. ✅ 体验天气推荐功能
3. ✅ 下载Excel查看结果

### 本周可做
1. 📊 分析不同城市的天气差异
2. 🎯 调整活动推荐的权重
3. 📱 测试移动设备访问

### 本月可做
1. 🌍 添加更多天气数据源
2. 🏃 优化性能
3. 🌐 支持多语言
4. 📈 添加历史数据分析

---

## 📞 获取帮助 (Get Help)

### 文档
- 📖 查看项目中的各个README文件
- 📖 查看代码中的详细注释

### 测试
- 🧪 运行 `test_weather_service.py` 验证环境
- 🧪 检查浏览器的开发者控制台

### 日志
- 📋 Streamlit会输出详细的服务器日志
- 📋 API调用成功/失败都有记录

---

**祝您使用愉快！** 🌍✈️🌤️

有任何问题，请参考详细文档或查看代码注释。
