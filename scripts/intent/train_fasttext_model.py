#!/usr/bin/env python3
"""
FastText意图分类模型训练脚本
"""
import fasttext
from pathlib import Path
import sys

def train_intent_model():
    """训练FastText意图分类模型"""

    data_dir = Path("data/intent")
    model_dir = Path("models")
    model_dir.mkdir(parents=True, exist_ok=True)

    train_file = data_dir / "intent_train.txt"
    test_file = data_dir / "intent_test.txt"
    model_path = model_dir / "intent_classifier.bin"

    if not train_file.exists():
        print(f"[ERROR] Training file not found: {train_file}")
        print("Please run 'python scripts/intent/prepare_training_data.py' first")
        sys.exit(1)

    print("[INFO] Training FastText model...")
    print(f"  Training data: {train_file}")
    print(f"  Test data: {test_file}")

    # 训练模型
    model = fasttext.train_supervised(
        input=str(train_file),
        lr=0.5,              # 学习率
        epoch=25,            # 训练轮次
        wordNgrams=2,        # 使用bigrams提升上下文理解
        dim=100,             # 词向量维度
        loss='softmax',      # 多分类损失函数
        verbose=2            # 显示训练进度
    )

    print("\n[INFO] Training completed!")

    # 在测试集上评估
    if test_file.exists():
        print("\n[INFO] Evaluating on test set...")
        result = model.test(str(test_file))

        # result是元组: (样本数, Precision, Recall)
        n_samples, precision, recall = result
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        print(f"  Test samples: {n_samples}")
        print(f"  Precision: {precision:.4f}")
        print(f"  Recall: {recall:.4f}")
        print(f"  F1-Score: {f1_score:.4f}")

        # 目标检查
        if precision < 0.85:
            print(f"\n[WARNING] Precision ({precision:.2%}) is below target (85%)")
            print("  Consider: adding more training data or tuning hyperparameters")

    # 保存模型
    model.save_model(str(model_path))
    print(f"\n[OK] Model saved to: {model_path.absolute()}")

    # 测试几个样本
    print("\n[INFO] Testing with sample inputs:")
    test_cases = [
        "这个价格太贵了",
        "What are the features",
        "我再考虑考虑",
        "好的，我买了",
        "有没有成功案例"
    ]

    try:
        for text in test_cases:
            # 使用临时方法避免numpy兼容性问题
            labels, probs = model.predict(text, k=1)
            label = labels[0].replace("__label__", "")
            confidence = float(probs[0]) if hasattr(probs[0], '__float__') else probs[0]
            print(f"  '{text}' -> {label} (confidence: {confidence:.3f})")
    except Exception as e:
        print(f"  [WARNING] Sample testing skipped due to numpy compatibility: {e}")

    return model

if __name__ == "__main__":
    try:
        train_intent_model()
    except Exception as e:
        print(f"[ERROR] Training failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
