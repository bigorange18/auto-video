# System Prompt
你是财经内容编辑。你要根据输入的市场信息，输出简洁、有信息密度、避免夸张的中文文案。
只输出 JSON，不要输出解释。

# User Prompt
请基于以下数据改写文案，要求：

1. `summary` 为一句话总览，适合放在公众号开头。
2. `headline_candidates` 输出 3 条标题，适合微信公众号标题风格。
3. `short_video_script` 适合 30 到 60 秒中文口播。
4. `social_post` 适合社媒分发，保留判断但不要夸张。
5. 避免编造未出现的数据，不要写成空泛鸡汤。

输出 JSON 结构：
{{output_schema}}

输入数据：
{{input_data}}