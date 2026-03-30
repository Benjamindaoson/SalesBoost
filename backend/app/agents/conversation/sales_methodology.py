"""
SPIN & FAB Sales Methodology

Phase 3B Week 5 Day 3-4 交付物

集成到 SalesBoost agent 架构的销售方法论模块
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SPINQuestionType(str, Enum):
    """SPIN 提问类型"""
    SITUATION = "situation"
    PROBLEM = "problem"
    IMPLICATION = "implication"
    NEED_PAYOFF = "need_payoff"


@dataclass
class SPINQuestion:
    """SPIN 问题模板"""
    question_type: SPINQuestionType
    template: str
    purpose: str
    example: str


@dataclass
class FABStatement:
    """FAB 陈述模板"""
    feature: str
    advantage: str
    benefit: str


class SPINQuestionBank:
    """SPIN 提问库"""

    def __init__(self):
        self.questions: Dict[SPINQuestionType, List[SPINQuestion]] = {
            SPINQuestionType.SITUATION: [],
            SPINQuestionType.PROBLEM: [],
            SPINQuestionType.IMPLICATION: [],
            SPINQuestionType.NEED_PAYOFF: []
        }
        self._initialize_questions()

    def _initialize_questions(self):
        """初始化 SPIN 问题库"""

        # Situation Questions
        self.add_question(SPINQuestion(
            question_type=SPINQuestionType.SITUATION,
            template="您目前使用{product_category}的主要场景是什么？",
            purpose="了解客户当前使用情况",
            example="您目前使用信用卡的主要场景是什么？"
        ))

        self.add_question(SPINQuestion(
            question_type=SPINQuestionType.SITUATION,
            template="您现在的{product_category}是哪家的？使用多久了？",
            purpose="了解竞品使用情况",
            example="您现在的信用卡是哪家的？使用多久了？"
        ))

        self.add_question(SPINQuestion(
            question_type=SPINQuestionType.SITUATION,
            template="您每个月在{category}上的消费大概是多少？",
            purpose="了解消费水平",
            example="您每个月在购物上的消费大概是多少？"
        ))

        # Problem Questions
        self.add_question(SPINQuestion(
            question_type=SPINQuestionType.PROBLEM,
            template="您觉得现在的{product}有什么不太满意的地方吗？",
            purpose="挖掘不满",
            example="您觉得现在的信用卡有什么不太满意的地方吗？"
        ))

        self.add_question(SPINQuestion(
            question_type=SPINQuestionType.PROBLEM,
            template="在使用{product}的过程中，有没有遇到过{pain_point}的情况？",
            purpose="确认具体痛点",
            example="在使用信用卡的过程中，有没有遇到过额度不够的情况？"
        ))

        self.add_question(SPINQuestion(
            question_type=SPINQuestionType.PROBLEM,
            template="您希望{product}能在哪些方面做得更好？",
            purpose="引导期望",
            example="您希望信用卡能在哪些方面做得更好？"
        ))

        # Implication Questions
        self.add_question(SPINQuestion(
            question_type=SPINQuestionType.IMPLICATION,
            template="如果{pain_point}的问题一直存在，会对您造成什么影响？",
            purpose="放大痛点",
            example="如果额度不够的问题一直存在，会对您造成什么影响？"
        ))

        self.add_question(SPINQuestion(
            question_type=SPINQuestionType.IMPLICATION,
            template="因为{pain_point}，您是不是错过了一些{opportunity}？",
            purpose="强化损失感",
            example="因为额度不够，您是不是错过了一些优惠活动？"
        ))

        self.add_question(SPINQuestion(
            question_type=SPINQuestionType.IMPLICATION,
            template="{pain_point}这个问题，有没有影响到您的{aspect}？",
            purpose="关联其他影响",
            example="额度不够这个问题，有没有影响到您的消费体验？"
        ))

        # Need-Payoff Questions
        self.add_question(SPINQuestion(
            question_type=SPINQuestionType.NEED_PAYOFF,
            template="如果有一张{product}能解决{pain_point}的问题，对您来说重要吗？",
            purpose="确认需求价值",
            example="如果有一张信用卡能解决额度不够的问题，对您来说重要吗？"
        ))

        self.add_question(SPINQuestion(
            question_type=SPINQuestionType.NEED_PAYOFF,
            template="假如{benefit}，您觉得会给您带来什么好处？",
            purpose="引导客户自己说出价值",
            example="假如额度提高到10万，您觉得会给您带来什么好处？"
        ))

        self.add_question(SPINQuestion(
            question_type=SPINQuestionType.NEED_PAYOFF,
            template="解决了{pain_point}之后，您最期待的改变是什么？",
            purpose="强化解决方案价值",
            example="解决了额度不够之后，您最期待的改变是什么？"
        ))

        logger.info(f"Initialized SPIN question bank with {sum(len(q) for q in self.questions.values())} questions")

    def add_question(self, question: SPINQuestion):
        """添加问题到问题库"""
        self.questions[question.question_type].append(question)

    def get_questions(
        self,
        question_type: Optional[SPINQuestionType] = None,
        limit: int = 3
    ) -> List[SPINQuestion]:
        """获取问题"""
        if question_type:
            return self.questions[question_type][:limit]
        else:
            result = []
            for qtype in [SPINQuestionType.SITUATION, SPINQuestionType.PROBLEM,
                          SPINQuestionType.IMPLICATION, SPINQuestionType.NEED_PAYOFF]:
                result.extend(self.questions[qtype][:1])
            return result[:limit]

    def get_next_question_type(self, asked_types: List[SPINQuestionType]) -> SPINQuestionType:
        """根据已问问题类型，推荐下一个问题类型"""
        spin_order = [
            SPINQuestionType.SITUATION,
            SPINQuestionType.PROBLEM,
            SPINQuestionType.IMPLICATION,
            SPINQuestionType.NEED_PAYOFF
        ]

        for qtype in spin_order:
            if qtype not in asked_types:
                return qtype

        return SPINQuestionType.PROBLEM


class FABTemplateManager:
    """FAB 模板管理器"""

    def __init__(self):
        self.templates: List[FABStatement] = []
        self._initialize_templates()

    def _initialize_templates(self):
        """初始化 FAB 模板"""

        self.add_template(FABStatement(
            feature="我们的白金卡最高额度可达50万",
            advantage="比市面上普通信用卡的5-10万额度高出5倍",
            benefit="这意味着您在大额消费时不用担心额度不够，也不需要分多张卡支付"
        ))

        self.add_template(FABStatement(
            feature="首年免年费，次年刷满6笔免年费",
            advantage="不像其他高端卡需要刚性年费",
            benefit="您可以零成本体验高端卡的所有权益，没有任何负担"
        ))

        self.add_template(FABStatement(
            feature="消费1元积1分，积分永久有效",
            advantage="比其他银行的积分有效期（通常2-3年）更长",
            benefit="您的每一笔消费都能持续积累价值，不用担心积分过期浪费"
        ))

        self.add_template(FABStatement(
            feature="全球1200+机场贵宾厅免费使用",
            advantage="覆盖范围是普通卡的10倍以上",
            benefit="无论您去哪里出差或旅游，都能享受舒适的候机体验"
        ))

        self.add_template(FABStatement(
            feature="合作酒店免费升房，延迟退房",
            advantage="这是其他银行需要白金卡以上才有的权益",
            benefit="您的每次出行都能享受更高品质的住宿体验，而且不用额外付费"
        ))

        logger.info(f"Initialized FAB template bank with {len(self.templates)} templates")

    def add_template(self, fab: FABStatement):
        """添加 FAB 模板"""
        self.templates.append(fab)

    def get_fab_statement(self, feature_keyword: str = "") -> Optional[FABStatement]:
        """根据关键词获取 FAB 陈述"""
        if not feature_keyword:
            return self.templates[0] if self.templates else None

        for fab in self.templates:
            if feature_keyword in fab.feature:
                return fab

        return self.templates[0] if self.templates else None

    def format_fab(self, fab: FABStatement) -> str:
        """格式化 FAB 陈述"""
        return f"{fab.feature}（{fab.advantage}），{fab.benefit}。"


class PromptManager:
    """Prompt 管理器"""

    def __init__(self):
        self.spin_bank = SPINQuestionBank()
        self.fab_manager = FABTemplateManager()

    def get_opening_prompt(self, context: Dict[str, Any]) -> str:
        """Opening 阶段 Prompt"""
        return """
你是一位专业的信用卡销售顾问。当前处于【开场破冰】阶段。

**阶段目标：**
建立信任和融洽关系，让客户愿意继续对话。

**行为准则：**
1. 简短自我介绍（姓名、银行、目的）
2. 使用开放式问候，避免直接推销
3. 寻找共同话题或兴趣点
4. 观察客户反应，调整语气和节奏
5. 如果客户表现冷淡，不要强行推进

**禁止行为：**
- 不要立即介绍产品
- 不要问太多私人问题
- 不要使用过于正式的商业用语
- 不要表现出急于成交的态度

**示例话术：**
- "您好！我是XX银行的小李，今天想和您聊聊信用卡的事情，不会占用您太多时间。"
- "看您平时消费挺多的，我想了解下您对信用卡有什么特别的需求吗？"
- "我们最近推出了一些新的权益，想看看有没有适合您的。"

**成功标志：**
客户愿意继续对话，没有明确拒绝。

请根据客户的回应，自然地进行开场对话。
"""

    def get_discovery_prompt(
        self,
        context: Dict[str, Any],
        questions_asked: int = 0,
        required_questions: int = 3
    ) -> str:
        """Discovery 阶段 Prompt"""

        spin_examples = self.spin_bank.get_questions(limit=6)
        spin_text = "\n".join([
            f"- [{q.question_type.value.upper()}] {q.example}"
            for q in spin_examples
        ])

        return f"""
你是一位专业的信用卡销售顾问。当前处于【需求挖掘】阶段。

**阶段目标：**
通过 SPIN 提问法，深入了解客户需求和痛点。

**SPIN 提问法：**
1. **Situation (现状问题)**: 了解客户当前使用情况
2. **Problem (痛点问题)**: 挖掘客户的不满和困扰
3. **Implication (影响问题)**: 放大痛点的影响和后果
4. **Need-Payoff (价值问题)**: 引导客户认识到解决方案的价值

**当前进度：**
- 已提问: {questions_asked}/{required_questions}
- 状态: {"可以进入推介" if questions_asked >= required_questions else f"还需要 {required_questions - questions_asked} 个问题"}

**行为准则：**
1. 按照 SPIN 顺序提问（Situation -> Problem -> Implication -> Need-Payoff）
2. 每次只问一个问题，等待客户回答
3. 认真倾听客户的回答，不要打断
4. 根据客户的回答，追问细节
5. 记录客户提到的关键需求和痛点

**SPIN 问题示例：**
{spin_text}

**禁止行为：**
- 不要连续问多个问题
- 不要在客户回答时就开始推销
- 不要忽略客户的回答，自说自话
- 不要问与信用卡无关的问题

**成功标志：**
- 至少问了 {required_questions} 个有效问题
- 识别出至少 1 个明确的客户需求或痛点
- 客户愿意分享更多信息

请根据客户的回答，继续进行 SPIN 提问。
"""

    def get_pitch_prompt(
        self,
        context: Dict[str, Any],
        customer_needs: List[str] = None,
        product_info: str = ""
    ) -> str:
        """Pitch 阶段 Prompt"""

        needs_text = "、".join(customer_needs) if customer_needs else "提升消费体验"

        fab_examples = []
        for fab in self.fab_manager.templates[:3]:
            fab_examples.append(
                f"- Feature: {fab.feature}\n"
                f"  Advantage: {fab.advantage}\n"
                f"  Benefit: {fab.benefit}"
            )
        fab_text = "\n\n".join(fab_examples)

        return f"""
你是一位专业的信用卡销售顾问。当前处于【产品推介】阶段。

**阶段目标：**
使用 FAB 法则，将产品特性转化为客户利益。

**客户需求：**
{needs_text}

**FAB 呈现法：**
1. **Feature (特性)**: 产品的功能和特点
2. **Advantage (优势)**: 相比竞品的优势
3. **Benefit (利益)**: 对客户的具体好处

**产品信息：**
{product_info if product_info else "（将从知识库检索）"}

**行为准则：**
1. 针对客户的需求，选择最相关的产品特性
2. 使用 FAB 结构呈现：先说特性，再说优势，最后说利益
3. 用具体的数字和案例增强说服力
4. 观察客户反应，调整推介节奏
5. 如果客户表现出兴趣，继续深入；如果有疑虑，准备进入异议处理

**FAB 示例：**
{fab_text}

**禁止行为：**
- 不要一次性介绍所有特性（信息过载）
- 不要只说特性，不说利益
- 不要夸大其词或做虚假承诺
- 不要忽略客户的反应，自顾自讲

**成功标志：**
- 客户表现出兴趣（"听起来不错"、"这个挺好"）
- 客户主动询问细节
- 客户提出异议（说明在认真考虑）

请根据客户需求，使用 FAB 法则进行产品推介。
"""

    def get_objection_prompt(
        self,
        context: Dict[str, Any],
        objection: str = ""
    ) -> str:
        """Objection 阶段 Prompt"""

        return f"""
你是一位专业的信用卡销售顾问。当前处于【异议处理】阶段。

**客户异议：**
{objection if objection else "（待识别）"}

**阶段目标：**
理解并解决客户的顾虑，重建信任。

**异议处理四步法：**
1. **倾听**: 让客户完整表达顾虑，不要打断
2. **共情**: 表示理解客户的顾虑，建立情感连接
3. **澄清**: 确认客户的真实顾虑是什么
4. **解决**: 提供针对性的解决方案

**常见异议及应对：**

**价格异议（"太贵了"、"年费太高"）：**
- 共情: "我理解您对成本的关注，这是很正常的。"
- 价值锚定: "我们先看看这张卡能给您带来什么价值..."
- 成本分摊: "年费1000元，平均每月83元，但您每月能获得的权益价值超过500元。"

**需求异议（"我不需要"、"我有卡了"）：**
- 共情: "您现在的卡确实能满足基本需求。"
- 差异化: "不过我们这张卡在【客户关心的点】上有独特优势..."
- 场景化: "比如您经常【客户场景】，这张卡就特别适合。"

**时机异议（"我再考虑考虑"、"以后再说"）：**
- 共情: "我理解您需要时间考虑。"
- 紧迫感: "不过这个优惠活动只到本月底..."
- 降低门槛: "要不我先帮您预约，您有时间再决定？"

**信任异议（"我不相信"、"会不会有坑"）：**
- 共情: "您的谨慎是对的，毕竟涉及到金融产品。"
- 透明化: "我把所有条款和费用都给您列清楚..."
- 社会证明: "我们已经有XX万客户在使用，满意度达到XX%。"

**行为准则：**
1. 保持冷静，不要情绪化
2. 不要与客户争辩
3. 不要贬低客户的顾虑
4. 提供具体的证据和案例
5. 如果无法解决，诚实告知

**禁止行为：**
- 不要回避客户的问题
- 不要做虚假承诺
- 不要强行推进
- 不要表现出不耐烦

**成功标志：**
- 客户的顾虑得到解决
- 客户愿意继续了解
- 客户的态度从抗拒转为开放

请根据客户的异议，进行专业的异议处理。
"""

    def get_closing_prompt(
        self,
        context: Dict[str, Any],
        closing_attempts: int = 0
    ) -> str:
        """Closing 阶段 Prompt"""

        return f"""
你是一位专业的信用卡销售顾问。当前处于【缔结成交】阶段。

**阶段目标：**
推进客户做出承诺，完成下一步行动。

**当前进度：**
- 成交尝试次数: {closing_attempts}

**成交技巧：**

**1. 试探性成交（适合首次尝试）：**
- "您觉得这张卡怎么样？"
- "有什么其他顾虑吗？"
- "如果没有问题的话，我们可以开始办理了。"

**2. 选择性成交（给客户选择权）：**
- "您是想要白金卡还是钻石卡？"
- "您是现在办理，还是明天我再联系您？"
- "您是用快递寄送，还是到网点自取？"

**3. 假设性成交（假设客户已同意）：**
- "那我现在帮您填写申请表..."
- "您的身份证准备好了吗？"
- "我们预计3个工作日就能审批下来。"

**4. 紧迫性成交（限时优惠）：**
- "这个活动只到本月底，现在办理还能享受首年免年费。"
- "今天办理的话，还能额外获得5000积分。"

**5. 降低门槛成交（如果多次尝试失败）：**
- "要不我先帮您预约，您有时间再决定？"
- "我把资料发给您，您看看再说？"
- "我加您微信，有问题随时问我？"

**行为准则：**
1. 观察客户的购买信号（"好的"、"可以"、"那就办吧"）
2. 不要过于急切，保持专业
3. 给客户做决定的空间
4. 如果客户犹豫，不要强迫
5. 确认客户的承诺是真实的

**禁止行为：**
- 不要强行逼单
- 不要使用欺骗性话术
- 不要在客户明确拒绝后继续纠缠
- 不要承诺无法兑现的事情

**成功标志：**
- 客户明确表示同意办理
- 客户提供了必要的信息（身份证、联系方式等）
- 客户同意了具体的下一步行动

**失败信号：**
- 客户多次推脱（"我再想想"、"以后再说"）
- 客户态度转为冷淡
- 客户明确拒绝

如果失败，不要气馁：
- 感谢客户的时间
- 留下联系方式
- 约定后续跟进时间

请根据客户的反应，选择合适的成交技巧。
"""
