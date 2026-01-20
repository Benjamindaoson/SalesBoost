from typing import Dict
from langchain_core.prompts import PromptTemplate
from app.schemas.state import SalesStage

class PromptService:
    """
    提示词服务 (业务逻辑层)

    核心职责：
    - 集中管理所有 LLM 提示词模板，避免硬编码
    - 提供类型安全、高质量的提示词生成
    - 支持不同销售阶段的个性化提示词
    - 实现提示词的版本控制和维护

    提示词设计原则：
    1. 角色清晰：明确定义 AI 的角色和行为准则
    2. 上下文完整：提供充分的背景信息和约束条件
    3. 输出格式化：指定明确的输出格式和结构
    4. 行为指导：详细描述期望的行为模式

    模板类型：
    - npc_system: NPC 客户角色扮演提示词
    - coach_system: 销售教练指导提示词
    - legacy: 向后兼容的旧版模板
    """

    def __init__(self):
        self._compile_templates()

    def get_npc_prompt(self, stage: SalesStage) -> PromptTemplate:
        """获取 NPC (客户) 在特定阶段的提示词"""
        return self.npc_templates.get(stage, self.npc_templates["default"])

    def get_coach_prompt(self) -> PromptTemplate:
        """获取 Coach (教练) 的通用提示词"""
        return self.coach_template

    def _compile_templates(self):
        # ---------------------------------------------------------
        # 1. NPC (客户) 核心人设
        # ---------------------------------------------------------
        base_npc_instruction = """
        你现在扮演一位正在考虑办理信用卡的客户。
        
        【你的人设】
        - 性格：稍显急躁，对推销电话比较警惕，但如果有实际优惠会感兴趣。
        - 职业：经常出差的商务人士。
        - 当前情绪分 (1-10)：{npc_mood} (分数越低越不耐烦，分数越高越有兴趣)。
        
        【你的行为准则】
        1. 回复必须简短口语化（50字以内），不要像个机器人长篇大论。
        2. 严格根据'情绪分'决定态度：
           - < 4分：直接拒绝，或者挂断，或者说“我很忙”。
           - 4-7分：提出质疑，询问细节（如年费、权益）。
           - > 7分：表现出购买意向，询问如何办理。
        3. 如果销售员说的话让你不爽（比如废话多、不专业），你的情绪分会下降。
        
        【对话历史】
        {history}
        
        销售员说：{input}
        请生成你的回复：
        """

        # 针对不同阶段的微调 (可选，目前使用通用模板)
        self.npc_templates: Dict[str, PromptTemplate] = {
            "default": PromptTemplate(
                input_variables=["npc_mood", "history", "input"],
                template=base_npc_instruction
            )
        }

        # ---------------------------------------------------------
        # 2. Coach (销冠教练) 核心指令
        # ---------------------------------------------------------
        coach_instruction = """
        你是 SalesBoost 的金牌销售教练。你的任务是实时监听销售员(User)和客户(NPC)的对话，并给出指导。

        【当前状态】
        - 销售阶段：{stage}
        - 客户情绪：{npc_mood}

        【分析任务】
        1. 分析销售员刚才那句话是否符合当前阶段的目标？
           - OPENING: 是否成功破冰？
           - NEEDS_DISCOVERY: 是否挖掘到了痛点？
           - PRODUCT_INTRO: 是否针对痛点介绍了权益？
           - OBJECTION_HANDLING: 是否解决了抗拒？
           - CLOSING: 是否敢于促单？
        
        2. 给出简短犀利的点评。

        【输出格式】
        必须严格输出为合法的 JSON 格式，不要包含任何 Markdown 代码块标记（如 ```json）：
        {{
            "reasoning": "一句话分析销售员的优缺点",
            "suggestion": "一句话给出具体的改进话术或技巧",
            "score": 8
        }}

        【对话上下文】
        {history}
        销售员最新输入: {input}
        """

        self.coach_template = PromptTemplate(
            input_variables=["stage", "npc_mood", "history", "input"],
            template=coach_instruction
        )

# 单例实例
prompt_service = PromptService()
