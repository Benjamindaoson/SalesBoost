#!/usr/bin/env python3
"""
意图识别训练数据准备脚本
生成销售场景的意图标注数据集
"""
import os
import pandas as pd
from pathlib import Path

# 销售场景意图标注数据集（中英文混合）
TRAINING_DATA = [
    # 价格相关 (price_objection / price_inquiry)
    {"text": "这个价格太贵了", "label": "price_objection"},
    {"text": "能不能便宜点", "label": "price_objection"},
    {"text": "有没有折扣", "label": "price_objection"},
    {"text": "太贵了，买不起", "label": "price_objection"},
    {"text": "价格能再优惠吗", "label": "price_objection"},
    {"text": "This is too expensive", "label": "price_objection"},
    {"text": "Can you give me a discount", "label": "price_objection"},
    {"text": "The price is too high", "label": "price_objection"},

    {"text": "多少钱", "label": "price_inquiry"},
    {"text": "价格是多少", "label": "price_inquiry"},
    {"text": "费用怎么算", "label": "price_inquiry"},
    {"text": "收费标准是什么", "label": "price_inquiry"},
    {"text": "What's the price", "label": "price_inquiry"},
    {"text": "How much does it cost", "label": "price_inquiry"},

    # 产品咨询 (product_inquiry)
    {"text": "这个产品有什么功能", "label": "product_inquiry"},
    {"text": "能介绍一下产品吗", "label": "product_inquiry"},
    {"text": "有哪些特色", "label": "product_inquiry"},
    {"text": "跟竞品比有什么优势", "label": "product_inquiry"},
    {"text": "具体怎么用", "label": "product_inquiry"},
    {"text": "What are the features", "label": "product_inquiry"},
    {"text": "Can you explain the product", "label": "product_inquiry"},
    {"text": "What makes it different", "label": "product_inquiry"},

    # 权益咨询 (benefit_inquiry)
    {"text": "会员有什么权益", "label": "benefit_inquiry"},
    {"text": "VIP有哪些好处", "label": "benefit_inquiry"},
    {"text": "能享受什么服务", "label": "benefit_inquiry"},
    {"text": "购买后有什么保障", "label": "benefit_inquiry"},
    {"text": "What benefits do I get", "label": "benefit_inquiry"},
    {"text": "What's included in membership", "label": "benefit_inquiry"},

    # 积极反馈 (positive_feedback)
    {"text": "听起来不错", "label": "positive_feedback"},
    {"text": "这个很有吸引力", "label": "positive_feedback"},
    {"text": "感觉挺好的", "label": "positive_feedback"},
    {"text": "我很感兴趣", "label": "positive_feedback"},
    {"text": "Sounds good", "label": "positive_feedback"},
    {"text": "That's interesting", "label": "positive_feedback"},
    {"text": "I like it", "label": "positive_feedback"},

    # 犹豫不决 (hesitation)
    {"text": "我再考虑考虑", "label": "hesitation"},
    {"text": "让我想想", "label": "hesitation"},
    {"text": "还需要犹豫一下", "label": "hesitation"},
    {"text": "不太确定", "label": "hesitation"},
    {"text": "I need to think about it", "label": "hesitation"},
    {"text": "Let me consider", "label": "hesitation"},
    {"text": "I'm not sure", "label": "hesitation"},

    # 谈判 (negotiation)
    {"text": "能不能送点东西", "label": "negotiation"},
    {"text": "有没有赠品", "label": "negotiation"},
    {"text": "可以加送服务吗", "label": "negotiation"},
    {"text": "能免费试用吗", "label": "negotiation"},
    {"text": "Can you throw in something extra", "label": "negotiation"},
    {"text": "Any free trial", "label": "negotiation"},

    # 时间压力 (time_pressure)
    {"text": "我很急，什么时候能交付", "label": "time_pressure"},
    {"text": "最快多久能完成", "label": "time_pressure"},
    {"text": "交付周期多长", "label": "time_pressure"},
    {"text": "How soon can you deliver", "label": "time_pressure"},
    {"text": "What's the timeline", "label": "time_pressure"},

    # 案例请求 (case_request)
    {"text": "有没有成功案例", "label": "case_request"},
    {"text": "能举个例子吗", "label": "case_request"},
    {"text": "其他客户怎么说", "label": "case_request"},
    {"text": "有客户评价吗", "label": "case_request"},
    {"text": "Any success stories", "label": "case_request"},
    {"text": "Can you give me an example", "label": "case_request"},

    # 竞品对比 (competitor_comparison)
    {"text": "和XX比怎么样", "label": "competitor_comparison"},
    {"text": "为什么不选竞品", "label": "competitor_comparison"},
    {"text": "你们有什么优势", "label": "competitor_comparison"},
    {"text": "How do you compare to competitors", "label": "competitor_comparison"},

    # 决策确认 (final_confirmation)
    {"text": "好的，我买了", "label": "final_confirmation"},
    {"text": "可以，成交", "label": "final_confirmation"},
    {"text": "那就这样吧", "label": "final_confirmation"},
    {"text": "OK, I'll take it", "label": "final_confirmation"},
    {"text": "Let's do it", "label": "final_confirmation"},

    # 拒绝 (soft_rejection)
    {"text": "我觉得不太合适", "label": "soft_rejection"},
    {"text": "可能不需要", "label": "soft_rejection"},
    {"text": "暂时不考虑", "label": "soft_rejection"},
    {"text": "I don't think it's for me", "label": "soft_rejection"},
    {"text": "Not interested right now", "label": "soft_rejection"},

    # 寒暄 (greeting)
    {"text": "你好", "label": "greeting"},
    {"text": "您好", "label": "greeting"},
    {"text": "Hi", "label": "greeting"},
    {"text": "Hello", "label": "greeting"},

    # 无意义填充 (filler)
    {"text": "嗯嗯", "label": "filler"},
    {"text": "啊哈", "label": "filler"},
    {"text": "哦", "label": "filler"},
    {"text": "OK", "label": "filler"},
    {"text": "I see", "label": "filler"},

    # 不清楚 (unclear)
    {"text": "不知道说什么", "label": "unclear"},
    {"text": "随便聊聊", "label": "unclear"},
    {"text": "emmm", "label": "unclear"},
]

def prepare_datasets():
    """准备训练和测试数据集"""

    # 创建数据目录
    data_dir = Path("data/intent")
    data_dir.mkdir(parents=True, exist_ok=True)

    # 转换为DataFrame
    df = pd.DataFrame(TRAINING_DATA)

    # 数据增强：添加一些变体
    augmented_data = []
    for _, row in df.iterrows():
        text, label = row['text'], row['label']

        # 原始数据
        augmented_data.append({"text": text, "label": label})

        # 添加标点符号变体
        if not text.endswith(('?', '？', '!', '！')):
            augmented_data.append({"text": text + "？", "label": label})

        # 添加语气词变体（仅中文）
        if any('\u4e00' <= c <= '\u9fff' for c in text):
            augmented_data.append({"text": text + "啊", "label": label})
            augmented_data.append({"text": text + "呢", "label": label})

    df_augmented = pd.DataFrame(augmented_data)

    # 打乱顺序
    df_augmented = df_augmented.sample(frac=1, random_state=42).reset_index(drop=True)

    # 划分训练集和测试集 (80/20)
    train_size = int(len(df_augmented) * 0.8)
    train_df = df_augmented[:train_size]
    test_df = df_augmented[train_size:]

    # 保存CSV格式
    train_df.to_csv(data_dir / "intent_train.csv", index=False)
    test_df.to_csv(data_dir / "intent_test.csv", index=False)

    # 转换为FastText格式
    with open(data_dir / "intent_train.txt", "w", encoding="utf-8") as f:
        for _, row in train_df.iterrows():
            f.write(f"__label__{row['label']} {row['text']}\n")

    with open(data_dir / "intent_test.txt", "w", encoding="utf-8") as f:
        for _, row in test_df.iterrows():
            f.write(f"__label__{row['label']} {row['text']}\n")

    print(f"[OK] Data preparation completed!")
    print(f"   Training set: {len(train_df)} samples")
    print(f"   Test set: {len(test_df)} samples")
    print(f"   Intent categories: {df_augmented['label'].nunique()}")
    print(f"   Category distribution:")
    print(df_augmented['label'].value_counts())
    print(f"\nFiles saved to: {data_dir.absolute()}")

    return train_df, test_df

if __name__ == "__main__":
    prepare_datasets()
