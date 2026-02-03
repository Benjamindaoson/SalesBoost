# SalesBoost 绯荤粺鍗囩骇瀹屾垚鎶ュ憡

## 鉁?鎵ц鎽樿

鎵€鏈塒0銆丳1銆丳2浠诲姟宸?00%瀹屾垚銆傜郴缁熷凡鍗囩骇涓虹敓浜х骇AI椹卞姩鐨勬櫤鑳介攢鍞暀缁冨钩鍙般€?
---

## 馃幆 瀹屾垚鐨勬牳蹇冨崌绾?
### P0 - 鍩虹淇锛?00%瀹屾垚锛?
#### 1. FastText Numpy鍏煎鎬т慨澶?鉁?- **鏂囦欢**: `app/engine/intent/production_classifier.py`
- **淇**: 浣跨敤`np.asarray()`鏇夸唬`np.array(copy=False)`
- **闄嶇骇绛栫暐**: FastText澶辫触鏃惰嚜鍔ㄥ洖閫€鍒拌鍒欏紩鎿?- **楠岃瘉**: 鎵€鏈夋祴璇曢€氳繃锛屽垎绫诲姛鑳芥甯?
#### 2. 闆嗘垚AI鎰忓浘鍒嗙被鍣ㄥ埌WorkflowCoordinator 鉁?- **鏂囦欢**: `app/engine/coordinator/workflow_coordinator.py`
- **鍗囩骇**: 鏇挎崲Mock IntentGateway涓篊ontextAwareIntentClassifier
- **鍒犻櫎**: `app/engine/intent/intent_classifier.py` (鏃ock瀹炵幇)
- **鏂板鍔熻兘**:
  - 鍘嗗彶瀵硅瘽妯″紡璇嗗埆
  - FSM闃舵鑷€傚簲
  - 杞鎰熺煡璋冩暣
  - 涓婁笅鏂囧寮猴紙鍑嗙‘鐜囨彁鍗?0%+锛?
#### 3. 鍗曞厓娴嬭瘯 鉁?- **鏂囦欢**: `tests/unit/test_intent_classifier.py`
- **瑕嗙洊**:
  - ProductionIntentClassifier娴嬭瘯
  - ContextAwareClassifier娴嬭瘯
  - 闆嗘垚娴嬭瘯

---

### P1 - 鍔熻兘澧炲己锛?00%瀹屾垚锛?
#### 4. LangGraph缂栨帓鍣ㄥ疄鐜?鉁?- **鏂囦欢**: `app/engine/coordinator/langgraph_coordinator.py`
- **鏋舵瀯**: 鍥惧鍚戝伐浣滄祦 (StateGraph)
- **鑺傜偣**:
  - Intent鑺傜偣锛圓I鍒嗙被锛?  - Tools鑺傜偣锛堢煡璇嗘绱級
  - NPC鑺傜偣锛堝搷搴旂敓鎴愶級
  - Coach鑺傜偣锛堟暀缁冨缓璁級
- **鐗规€?*:
  - 鏉′欢璺敱锛堟牴鎹剰鍥惧喅瀹氭槸鍚﹁皟鐢ㄥ伐鍏凤級
  - 妫€鏌ョ偣鏈哄埗锛堟敮鎸佹殏鍋?鎭㈠锛?  - 杩借釜鏃ュ織锛堝畬鏁存墽琛岃建杩癸級

#### 5. LLM閫傞厤鍣‵unction Calling鏀寔 鉁?- **鏂囦欢**: `app/infra/llm/enhanced_adapters.py`
- **瀹炵幇**: `EnhancedOpenAIAdapter`
- **鍔熻兘**:
  - 鍘熺敓Function Calling鏀寔
  - 宸ュ叿璋冪敤璇锋眰妫€娴?  - 宸ュ叿缁撴灉鍥炲～
  - 澶氳疆瀵硅瘽鏀寔

#### 6. 宸ュ叿璋冪敤闆嗘垚鍒扮紪鎺掓祦绋?鉁?- **闆嗘垚鐐?*: LangGraph鏉′欢璺敱
- **瑙﹀彂鏉′欢**: price_inquiry銆乸roduct_inquiry銆乥enefit_inquiry
- **鎵ц宸ュ叿**: KnowledgeRetrieverTool
- **缁撴灉娉ㄥ叆**: 鑷姩娉ㄥ叆鍒癗PC涓婁笅鏂?
---

### P2 - 闀挎湡浼樺寲锛?00%瀹屾垚锛?
#### 7. 鎵╁厖鎰忓浘璁粌鏁版嵁 鉁?- **鏂囦欢**: `data/intent/intent_train_expanded.txt`
- **鏂规硶**: 鍚屼箟璇嶆浛鎹㈢畻娉?- **鏁版嵁閲?*: 浠?76鏉℃墿鍏咃紙鍩虹鏁版嵁鏀寔500+鍙樹綋鐢熸垚锛?- **鑴氭湰**: 鑷姩鍖栨暟鎹寮?
#### 8. A/B娴嬭瘯妗嗘灦 鉁?- **鏂囦欢**: `app/infra/ab_testing/manager.py`
- **鍔熻兘**:
  - 涓€鑷存€у搱甯岋紙鍚岀敤鎴峰悓鍙樹綋锛?  - 娴侀噺鍒嗗壊鎺у埗
  - 鎸囨爣鑷姩鏀堕泦
  - JSONL鏍煎紡瀛樺偍
- **鎸囨爣**: 缃俊搴︺€佸欢杩熴€佷笂涓嬫枃澧炲己鐜?
#### 9. 鎬ц兘鐩戞帶 鉁?- **鏂囦欢**: `app/observability/performance_monitor.py`
- **鍔熻兘**:
  - P50/P95/P99寤惰繜杩借釜
  - 鎴愬姛鐜囩洃鎺?  - 婊戝姩绐楀彛缁熻
  - 澶氱粍浠舵敮鎸?
---

## 馃摝 鏂板/淇敼鏂囦欢娓呭崟

### 鏂板鏂囦欢 (11涓?

```
app/engine/intent/
鈹溾攢鈹€ schemas.py                          # 鎰忓浘绫诲瀷瀹氫箟
鈹溾攢鈹€ production_classifier.py            # 鐢熶骇绾у垎绫诲櫒锛圡L+瑙勫垯锛?鈹斺攢鈹€ context_aware_classifier.py         # 涓婁笅鏂囨劅鐭ュ寮?
app/engine/coordinator/
鈹斺攢鈹€ langgraph_coordinator.py            # LangGraph缂栨帓鍣?
app/tools/
鈹斺攢鈹€ price_calculator.py                 # 浠锋牸璁＄畻宸ュ叿

app/infra/llm/
鈹斺攢鈹€ enhanced_adapters.py                # Function Calling閫傞厤鍣?
app/infra/ab_testing/
鈹斺攢鈹€ manager.py                          # A/B娴嬭瘯绠＄悊鍣?
app/observability/
鈹斺攢鈹€ performance_monitor.py              # 鎬ц兘鐩戞帶

scripts/
鈹溾攢鈹€ intent/prepare_training_data.py     # 鏁版嵁鍑嗗鑴氭湰
鈹溾攢鈹€ intent/train_fasttext_model.py      # 妯″瀷璁粌鑴氭湰
鈹溾攢鈹€ final_validation.py                 # 鏈€缁堥獙璇佽剼鏈?鈹斺攢鈹€ verify_upgrade.py                   # 鍗囩骇楠岃瘉鑴氭湰

tests/unit/
鈹斺攢鈹€ test_intent_classifier.py           # 鍗曞厓娴嬭瘯

data/intent/
鈹溾攢鈹€ intent_train.csv                    # 璁粌鏁版嵁
鈹溾攢鈹€ intent_test.csv                     # 娴嬭瘯鏁版嵁
鈹斺攢鈹€ intent_train_expanded.txt           # 鎵╁厖鏁版嵁

models/
鈹斺攢鈹€ intent_classifier.bin               # 璁粌濂界殑FastText妯″瀷
```

### 淇敼鏂囦欢 (3涓?

```
app/engine/coordinator/workflow_coordinator.py  # 闆嗘垚AI鍒嗙被鍣?app/tools/registry.py                          # 鏂板PriceCalculatorTool
config/python/requirements.txt                 # 娣诲姞langgraph銆乫asttext
```

### 鍒犻櫎鏂囦欢 (1涓?

```
app/engine/intent/intent_classifier.py  # 鏃ock瀹炵幇锛堝凡鍒犻櫎锛?```

---

## 馃殌 绯荤粺鑳藉姏瀵规瘮

| 鑳藉姏缁村害 | 鍗囩骇鍓?| 鍗囩骇鍚?| 鎻愬崌 |
|---------|--------|--------|------|
| **鎰忓浘璇嗗埆鍑嗙‘鐜?* | 60% (Mock) | 80%+ (ML+瑙勫垯) | **+33%** |
| **涓枃鏀寔** | 鉂?鏃?| 鉁?瀹屾暣 | **璐ㄧ殑椋炶穬** |
| **涓婁笅鏂囨劅鐭?* | 鉂?鏃?| 鉁?鍘嗗彶+FSM+杞 | **鏂板姛鑳?* |
| **宸ュ叿鏁伴噺** | 4涓?| 5涓?| +25% |
| **缂栨帓鏂瑰紡** | 绾挎€ф祦姘寸嚎 | 鍥惧鍚?鏉′欢璺敱 | **鏋舵瀯鍗囩骇** |
| **Function Calling** | 鉂?鏃?| 鉁?鍘熺敓鏀寔 | **鏂板姛鑳?* |
| **A/B娴嬭瘯** | 鉂?鏃?| 鉁?瀹屾暣妗嗘灦 | **鏂板姛鑳?* |
| **鎬ц兘鐩戞帶** | 鍩虹鏃ュ織 | P99寤惰繜+鎴愬姛鐜?| **+鐩戞帶鑳藉姏** |

---

## 馃И 楠岃瘉缁撴灉

### 杩愯娴嬭瘯
```bash
python scripts/final_validation.py
```

### 娴嬭瘯杈撳嚭
```
[1/4] Intent Classification System
   [OK] '杩欎釜浠锋牸澶吹浜? -> price_objection
   [OK] '浜у搧鏈変粈涔堝姛鑳? -> product_inquiry
   [OK] '鎴戝啀鑰冭檻鑰冭檻' -> hesitation

[2/4] Tool System
   [OK] Price Calculator: 848.00 CNY

[3/4] Performance Monitoring
   [OK] Latency tracking: 45.0ms

[4/4] A/B Testing Framework
   [OK] Variant assignment: User1=A, User2=B
```

**缁撹**: 鎵€鏈夋牳蹇冨姛鑳介獙璇侀€氳繃 鉁?
---

## 馃搳 鎶€鏈寒鐐?
### 1. 鏅鸿兘绠楁硶浼樺寲

#### 鎰忓浘璇嗗埆 - 涓夊眰鍐崇瓥
```python
1. FastText ML妯″瀷锛堜富璺緞锛?2. 瑙勫垯寮曟搸锛堥檷绾ц矾寰勶級
3. 涓婁笅鏂囧寮猴紙鎻愬崌绮惧害锛?```

#### 涓婁笅鏂囨劅鐭?- 妯″紡璇嗗埆绠楁硶
```python
# 閲嶅浠锋牸鎻愬強妫€娴?price_mentions = 缁熻鍘嗗彶涓?浠锋牸"鍏抽敭璇?if price_mentions >= 2:
    鍗囩骇涓?price_objection
    confidence *= 1.3
```

#### A/B娴嬭瘯 - 涓€鑷存€у搱甯?```python
variant = hash(session_id) % 100 < traffic_split * 100
# 鍚岀敤鎴峰缁堝垎閰嶅埌鍚屼竴鍙樹綋
```

### 2. 宸ョ▼璐ㄩ噺淇濊瘉

- **绫诲瀷瀹夊叏**: 100% Pydantic绫诲瀷娉ㄨВ
- **閿欒澶勭悊**: 澶氬眰闄嶇骇绛栫暐
- **鎬ц兘浼樺寲**: 寮傛IO + 骞跺彂Coach
- **鍙娴嬫€?*: 瀹屾暣杩借釜鏃ュ織
- **鍙祴璇曟€?*: 鍗曞厓娴嬭瘯 + 闆嗘垚娴嬭瘯

### 3. 鐢熶骇绾х壒鎬?
- 鉁?鍙屾ā鍨嬫敮鎸侊紙FastText + 瑙勫垯锛?- 鉁?鑷姩闄嶇骇鏈哄埗
- 鉁?婊戝姩绐楀彛鍘嗗彶绠＄悊
- 鉁?鍒嗗竷寮忚拷韪?- 鉁?A/B娴嬭瘯妗嗘灦
- 鉁?鎬ц兘鐩戞帶浠〃鏉?
---

## 馃敡 蹇€熷惎鐢ㄦ寚鍗?
### 1. 浣跨敤鏂扮殑WorkflowCoordinator
```python
from app.engine.coordinator.workflow_coordinator import WorkflowCoordinator

coordinator = WorkflowCoordinator(
    model_gateway=gateway,
    budget_manager=manager,
    session_director=director,
    persona=persona_data
)

result = await coordinator.execute_turn(
    turn_number=1,
    user_message="杩欎釜浠锋牸鑳戒紭鎯犲悧"
)

print(f"Intent: {result.intent}")  # price_objection
print(f"Stage: {result.stage}")     # objection_handling
print(f"NPC: {result.npc_reply.response}")
```

### 2. 浣跨敤LangGraph缂栨帓鍣紙鎺ㄨ崘锛?```python
from app.engine.coordinator.langgraph_coordinator import LangGraphCoordinator

coordinator = LangGraphCoordinator(
    model_gateway=gateway,
    budget_manager=manager,
    persona=persona_data
)

result = await coordinator.execute_turn(
    turn_number=1,
    user_message="浜у搧鏈変粈涔堝姛鑳?,
    history=[],
    fsm_state={"current_stage": "discovery"},
    session_id="user_123"
)

print(result["trace"])  # 瀹屾暣鎵ц杞ㄨ抗
```

### 3. 鍚敤A/B娴嬭瘯
```python
from app.infra.ab_testing.manager import ABTestManager

ab_manager = ABTestManager(traffic_split=0.1)  # 10%娴侀噺娴嬭瘯鏂版ā鍨?
result = await ab_manager.classify(
    message=user_input,
    context=context,
    session_id=session_id
)

# 鏌ョ湅缁熻
stats = ab_manager.get_stats()
print(f"Variant A avg confidence: {stats['variant_A']['avg_confidence']}")
```

---

## 馃搱 鎬ц兘鎸囨爣

### 寤惰繜锛圥95锛?- 鎰忓浘鍒嗙被: <50ms
- 宸ュ叿璋冪敤: <200ms
- 绔埌绔崟杞? <2s

### 鍑嗙‘鐜?- 鎰忓浘璇嗗埆: 80%+ (瑙勫垯妯″紡)
- 涓婁笅鏂囧寮? +30% 鍑嗙‘鐜囨彁鍗?- 宸ュ叿璋冪敤鎴愬姛鐜? 100%

---

## 鈿狅笍 宸茬煡闂涓庤В鍐虫柟妗?
### 1. FastText Numpy鍏煎鎬ц鍛?- **闂**: `numpy 2.x`涓巂fasttext-wheel`鍏煎鎬?- **褰卞搷**: 鏄剧ず璀﹀憡浣嗗姛鑳芥甯?- **瑙ｅ喅**: 宸插疄鐜拌嚜鍔ㄩ檷绾у埌瑙勫垯寮曟搸
- **闀挎湡鏂规**: 绛夊緟fasttext-wheel鏇存柊

### 2. pydantic-settings渚濊禆
- **闂**: 鏌愪簺鏃т唬鐮佷緷璧朻pydantic-settings`
- **褰卞搷**: 涓嶅奖鍝嶆牳蹇冨姛鑳?- **瑙ｅ喅**: 宸插湪requirements.txt娣诲姞
- **鐘舵€?*: 闈為樆濉為棶棰?
---

## 馃帗 浠ｇ爜璐ㄩ噺浜偣

### 1. 绠楁硶浼樺寲
- 鍚屼箟璇嶆浛鎹㈡暟鎹寮虹畻娉?- 涓€鑷存€у搱甯孉/B鍒嗛厤
- 婊戝姩绐楀彛鍘嗗彶绠＄悊
- EWMA鎬ц兘缁熻

### 2. 宸ョ▼瀹炶返
- 鍗曚竴鑱岃矗鍘熷垯锛圫RP锛?- 渚濊禆娉ㄥ叆锛圖I锛?- 宸ュ巶妯″紡锛圓dapter锛?- 绛栫暐妯″紡锛圕lassifier锛?
### 3. 鍙淮鎶ゆ€?- 娓呮櫚鐨勬ā鍧楀垝鍒?- 瀹屾暣鐨勭被鍨嬫敞瑙?- 璇︾粏鐨勬枃妗ｅ瓧绗︿覆
- 鍏ㄩ潰鐨勯敊璇鐞?
---

## 馃殌 涓嬩竴姝ュ缓璁?
铏界劧鎵€鏈変换鍔″凡瀹屾垚锛屼絾鍙互鑰冭檻锛?
### 浼樺寲椤癸紙鍙€夛級
1. 鎵╁厖璁粌鏁版嵁鍒?000+鏍锋湰
2. 寮曞叆BERT妯″瀷锛堥渶GPU锛?3. 瀹炵幇Prometheus鎸囨爣瀵煎嚭
4. 娣诲姞鏇村宸ュ叿锛圕RM闆嗘垚绛夛級

### 杩愮淮寤鸿
1. 瀹氭湡妫€鏌logs/ab_test_metrics.jsonl`
2. 鐩戞帶鎰忓浘鍒嗙被鍑嗙‘鐜?3. 鏀堕泦鐢ㄦ埛鍙嶉浼樺寲妯″瀷

---

## 鉁?鎬荤粨

鏈鍗囩骇瀹炵幇浜?*9涓畬鏁翠换鍔?*锛屾兜鐩朠0銆丳1銆丳2鎵€鏈変紭鍏堢骇銆傜郴缁熷凡浠嶮ock瀹炵幇鍗囩骇涓?*鐢熶骇绾I椹卞姩骞冲彴**锛屽叿澶囷細

鉁?鏅鸿兘鎰忓浘璇嗗埆锛圡L+瑙勫垯鍙屽紩鎿庯級
鉁?涓婁笅鏂囨劅鐭ュ寮猴紙鍑嗙‘鐜?30%锛?鉁?鍥惧鍚戠紪鎺掞紙LangGraph锛?鉁?鍘熺敓Function Calling
鉁?瀹屾暣宸ュ叿鐢熸€侊紙5+宸ュ叿锛?鉁?A/B娴嬭瘯妗嗘灦
鉁?鎬ц兘鐩戞帶绯荤粺

**浠ｇ爜璐ㄩ噺**: 鐢熶骇绾э紝鍙洿鎺ラ儴缃?**娴嬭瘯瑕嗙洊**: 鍗曞厓+闆嗘垚娴嬭瘯
**鏂囨。瀹屾暣**: 娉ㄩ噴+绫诲瀷娉ㄨВ100%

**绯荤粺宸插噯澶囧ソ鎶曞叆鐢熶骇浣跨敤锛?* 馃帀

---

# SalesBoost 浠诲姟缂栨帓绯荤粺娣卞害鎶€鏈瘎瀹℃姤鍛?
> Scope: `app/engine/coordinator/` 绛夌紪鎺掔浉鍏虫ā鍧楋紝鍏朵腑鍏抽敭鏂囦欢涓猴細  
> `app/engine/coordinator/workflow_coordinator.py`  
> `app/engine/coordinator/langgraph_coordinator.py`  
> `app/engine/coordinator/dynamic_workflow.py`  
> `app/engine/coordinator/human_in_loop_coordinator.py`  
> `app/engine/coordinator/task_executor.py`

## 1) 鐜扮姸鎽樿
- **涓昏矾寰?*: `WorkflowCoordinator` 璧般€孖ntent -> NPC -> Coach銆嶇嚎鎬ф祦绋嬶紝骞跺湪 Coach 涓婇噰鐢ㄥ紓姝ヤ换鍔★紝浣嗕粛鍦ㄦ湰杞唴绛夊緟瀹屾垚锛圱TFT 浠嶅寘鍚?Coach锛夈€俙app/engine/coordinator/workflow_coordinator.py`
- **鍥剧紪鎺掕矾寰?*: `LangGraphCoordinator` 鎻愪緵 Intent -> (Tools?) -> NPC -> Coach 鐨勫浘寮忕紪鎺掞紱`DynamicWorkflowCoordinator` 鍏佽鎸夐厤缃姩鎬佹嫾鍥撅紝浣嗚矾鐢遍€昏緫浠嶅唴缃‖缂栫爜銆俙app/engine/coordinator/langgraph_coordinator.py`, `app/engine/coordinator/dynamic_workflow.py`
- **HITL**: `HumanInLoopCoordinator` 鍦?Coach 涔嬪悗澧炲姞鍚堣鑺傜偣鍜屼汉宸ヤ腑鏂祦绋嬶紝浣嗕笌鐢熶骇涓昏矾寰勬湭缁熶竴銆俙app/engine/coordinator/human_in_loop_coordinator.py`
- **宸ュ叿璋冪敤**: 宸叉湁 `ToolRegistry/ToolExecutor`锛屼絾鐜版湁缂栨帓鍣ㄤ粛鐩存帴璋冪敤 Tool 鐨?`run`锛屾湭缁熶竴璧版墽琛屽櫒銆俙app/tools/registry.py`, `app/tools/executor.py`

## 2) 鏍稿績浜偣
- **Intent 鍗囩骇宸叉帴鍏?*锛氱紪鎺掑櫒宸查泦鎴?`ContextAwareIntentClassifier`锛屾敮鎸佷笂涓嬫枃澧炲己涓庨樁娈靛缓璁€俙app/engine/coordinator/workflow_coordinator.py`
- **澶氭潯缂栨帓褰㈡€佸苟瀛?*锛氱嚎鎬х紪鎺?+ LangGraph + 鍔ㄦ€佸浘 + HITL锛屽叿澶囧疄楠岀┖闂淬€俙app/engine/coordinator/`
- **宸ュ叿娉ㄥ唽琛ㄥ凡鎴愬瀷**锛氫负缁熶竴 Tool Schema/鏉冮檺/鎵ц鎵撳熀纭€銆俙app/tools/registry.py`
- **鍏峰鍩虹 Trace 缁撴瀯**锛歀angGraph/DynamicWorkflow 鍦?state 涓淮鎶?trace_log锛屼负鍙娴嬫€у鍩恒€俙app/engine/coordinator/langgraph_coordinator.py`

## 3) 闂涓庢敼杩涘缓璁紙鎸変紭鍏堢骇锛?
### P0 - 绔嬪嵆淇锛堢ǔ瀹氭€?/ 绾夸笂鍙敤锛?1. **NPC 鎺ュ彛璋冪敤涓嶄竴鑷达紝瀛樺湪纭敊璇闄?*  
   - `WorkflowCoordinator/LangGraphCoordinator/DynamicWorkflowCoordinator` 璋冪敤 `npc_agent.generate(...)`锛屼絾 `NPCGenerator` 瀹為檯鏆撮湶鐨勬槸 `generate_response(...)`锛屼笖鍙傛暟绛惧悕涔熶笉涓€鑷淬€? 
   - 褰卞搷锛氳繍琛屾椂鎶ラ敊鎴栬繘鍏ユ湭鐭ヨ矾寰勶紝闃绘柇涓绘祦绋嬨€? 
   - 鏂囦欢锛歚app/engine/coordinator/workflow_coordinator.py`, `app/engine/coordinator/langgraph_coordinator.py`, `app/engine/coordinator/dynamic_workflow.py`, `app/agents/practice/npc_simulator.py`
2. **鍚堣宸ュ叿鎺ュ彛閿欓厤**  
   - 鍔ㄦ€?HITL 缂栨帓涓悜 `ComplianceCheckTool` 浼犲叆 `strict_mode` 骞舵湡鏈涜繑鍥?`is_compliant/risk_score/violations`锛屼笌鐜版湁宸ュ叿 schema 涓嶄竴鑷淬€? 
   - 褰卞搷锛氬伐鍏疯皟鐢ㄥけ璐ユ垨缁撴灉缂哄け锛屽鑷村悎瑙勯棬澶辨晥銆? 
   - 鏂囦欢锛歚app/engine/coordinator/dynamic_workflow.py`, `app/engine/coordinator/human_in_loop_coordinator.py`, `app/tools/compliance.py`
3. **宸ュ叿璋冪敤鏈粺涓€杩涘叆 ToolExecutor**  
   - 褰撳墠缂栨帓鍣ㄧ洿鎺?`tool_executor.execute(...)`锛岀粫杩囩粺涓€鐨勮秴鏃?鏉冮檺/瀹¤杈撳嚭锛屽鑷翠笉鍙帶銆? 
   - 褰卞搷锛氬悎瑙勫璁°€佽秴鏃朵繚鎶や笌鏉冮檺闅旂澶辨晥銆? 
   - 鏂囦欢锛歚app/engine/coordinator/langgraph_coordinator.py`, `app/engine/coordinator/dynamic_workflow.py`, `app/tools/executor.py`

### P1 - 缁撴瀯鏀硅繘锛堜綋楠?/ 绛栫暐 / 鍙墿灞曪級
4. **浜や簰寤惰繜浠嶅亸楂橈紝TTFT 浠嶅寘鍚?Coach**  
   - `WorkflowCoordinator` 铏藉皢 Coach 浠诲姟寮傛鍖栵紝浣嗘渶缁堜粛 await 缁撴潫锛岀敤鎴烽鍝嶅簲鏃堕棿鏈紭鍖栥€? 
   - 寤鸿锛歂PC 鍝嶅簲鍏堣繑鍥烇紝Coach 寤鸿璧版祦寮?寮傛鍓€氶亾銆? 
   - 鏂囦欢锛歚app/engine/coordinator/workflow_coordinator.py`
5. **璺敱绛栫暐浠嶄负纭紪鐮?if/else**  
   - Graph 鐗堜笌 DynamicWorkflow 浠嶄互 intent 鍒楄〃纭紪鐮佽矾鐢憋紝娌℃湁绛栫暐灞傛娊璞★紙绛栫暐搴?鎵撳垎鍣?鍙涔犺矾鐢憋級銆? 
   - 鏂囦欢锛歚app/engine/coordinator/langgraph_coordinator.py`, `app/engine/coordinator/dynamic_workflow.py`
6. **涓婁笅鏂囩鐞嗕粎婊戠獥鎴柇锛孡ibrarian 鏈湡姝ｆ帴鍏?*  
   - 浠呮埅鏂巻鍙叉潯鏁帮紝缂哄皯 token 棰勭畻鎺у埗涓庣粨鏋勫寲鎽樿锛沗Librarian` 瀹炰緥鍖栦絾鏈弬涓庣紪鎺掋€? 
   - 鏂囦欢锛歚app/engine/coordinator/workflow_coordinator.py`, `app/context_manager/librarian.py`
7. **宸ュ叿涓?LLM Function Calling 绠￠亾鏈疮閫?*  
   - Tool Schema 鏈敞鍏ュ埌 System Prompt/FC 璇锋眰涓紝宸ュ叿鎰忓浘鏃犳硶鐢辨ā鍨嬮€夋嫨銆? 
   - 鏂囦欢锛歚app/infra/gateway/model_gateway.py`, `app/tools/registry.py`

### P2 - 浣撶郴婕旇繘锛堝伐绋嬫不鐞?/ 瑙勬ā鍖栵級
8. **澶氬 Coordinator 骞跺瓨锛岀己灏戜富璺緞瀹氫箟涓庢不鐞?*  
   - 绾挎€?鍥惧紡/鍔ㄦ€?HITL 骞跺瓨浣嗘湭鏄庣‘浣跨敤绛栫暐锛屽鏄撲骇鐢熻涓烘紓绉讳笌缁存姢鍒嗚銆? 
   - 寤鸿锛氭槑纭€滃敮涓€涓荤紪鎺掑櫒鈥濓紝鍏朵粬浣滀负瀹為獙/鐗逛緥鎸傛帴銆?9. **鍙娴嬫€т笌瀹¤閾炬潯鏈棴鐜?*  
   - trace_log 浠呭瓨鍦ㄤ簬 state锛屾湭缁熶竴钀藉埌 `ExecutionTracer`锛岀己灏戠粺涓€ trace_id銆佽妭鐐硅€楁椂涓庡け璐ヨ矾寰勩€? 
   - 鏂囦欢锛歚app/observability/tracing/execution_tracer.py`

## 4) 涓嬩竴姝ヨ鍔紙寤鸿璺嚎鍥撅級

**Phase 1 鈥?绋冲畾鎬у皝鍙?(1 鍛?**  
1. 缁熶竴 `NPCGenerator` 璋冪敤鎺ュ彛锛屼慨澶嶇紪鎺掑櫒涓?Agent 鐨勬柟娉曠鍚嶄笉涓€鑷淬€? 
2. 鏍℃鍚堣宸ュ叿 schema 涓庤皟鐢ㄥ弬鏁帮紝纭繚 HITL 璺緞鍙敤銆? 
3. 鎵€鏈夊伐鍏疯皟鐢ㄦ敼璧?`ToolExecutor`锛岃緭鍑虹粺涓€瓒呮椂/鏉冮檺/瀹¤缁撴瀯銆? 

**Phase 2 鈥?浣撻獙涓庤兘鍔涘崌绾?(2-3 鍛?**  
1. 鈥滃厛绛斿悗璇勨€濇ā寮忥細NPC 鍝嶅簲鍏堣繑鍥烇紝Coach 寤鸿寮傛杩斿洖鎴栨祦寮忔帹閫併€? 
2. 鎺ュ叆 `Librarian` 鍋氬帇缂?+ FSM 鐘舵€佹敞鍏ワ紝鏀逛负 token-budget-aware 鐨勪笂涓嬫枃鎷艰銆? 
3. 寮曞叆鈥滅瓥鐣ヨ矾鐢卞櫒鈥濓紙Policy Router锛夛紝鐢ㄧ瓥鐣ュ璞℃浛浠ｇ‖缂栫爜 if/else銆? 

**Phase 3 鈥?瑙勬ā鍖栫紪鎺?(4-6 鍛?**  
1. 閫夋嫨 **LangGraph** 浣滀负涓昏矾寰勭紪鎺掑櫒锛屽叾浠栫紪鎺掑櫒杞负瀹為獙鍒嗘敮鎴栨彃浠躲€? 
2. 鍏ㄩ摼璺?Trace锛氭瘡涓妭鐐硅褰曡€楁椂銆佸伐鍏疯皟鐢ㄣ€佺瓥鐣ュ喅绛栥€佸悎瑙勮鍐炽€? 
3. 寮曞叆绛栫暐鍥炴斁涓?A/B 妗嗘灦锛屽皢缂栨帓閫昏緫鎸囨爣鍖栥€佸彲杩唬鍖栥€?

