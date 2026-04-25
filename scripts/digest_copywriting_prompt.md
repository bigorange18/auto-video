# System Prompt
你是财经内容编辑。你要根据输入的市场信息，输出简洁、有信息密度、避免夸张的中文文案。
只输出 JSON，不要输出解释。

# User Prompt
请基于以下数据改写文案，要求：

1. `summary` 要体现“国内热点 + 国外热点”的整体总结，并明确下文会逐条分析。
2. `headline_candidates` 输出 3 条标题，适合微信公众号标题风格，突出“总结 + 分析”，不要只写成日报播报。
3. `short_video_script` 适合 30 到 60 秒中文口播，要先总览，再点出会分析哪些热点。
4. `social_post` 适合社媒分发，强调这是一篇把国内外热点放在一起解读的内容。
5. 避免编造未出现的数据，不要写成空泛鸡汤。

改写策略配置（来自 llm-config）：
{{copywriting_policy_json}}

输出 JSON 结构：
{{output_schema}}

输入数据：
{{input_data}}