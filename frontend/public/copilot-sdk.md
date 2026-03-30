# SalesBoost Copilot SDK

可嵌入的销转助手 Widget，用于在第三方系统（智能客服、CRM、企业微信等）中实时获取销售话术建议。

## 快速开始

```html
<script src="https://your-domain.com/copilot.js"></script>
<script>
  SalesBoost.init({
    apiKey: "sk-xxx",           // 可选，用于鉴权
    dealId: 123,                // 可选，关联商机 ID
    baseUrl: "http://localhost:8000",  // 后端 API 地址
    methodology: "meddpicc",    // meddpicc | spin | challenger
    position: "right",          // right | left
    mode: "live",              // live | prep
  });

  // 当客户消息到来时调用
  SalesBoost.onCustomerMessage("你们比竞品贵30%");
  // → 侧边栏自动弹出并显示话术建议
</script>
```

## API

### `SalesBoost.init(opts)`

初始化 SDK。

| 参数 | 类型 | 说明 |
|------|------|------|
| apiKey | string | API 密钥（可选） |
| dealId | number | 商机 ID（可选） |
| baseUrl | string | 后端地址，默认 `window.location.origin` |
| methodology | string | 方法论，默认 `meddpicc` |
| position | string | 侧边栏位置，`right` \| `left` |
| mode | string | 模式，`live` \| `prep` |

### `SalesBoost.onCustomerMessage(message)`

传入客户消息，获取话术建议并展示。返回 `Promise`。

### `SalesBoost.close()`

关闭侧边栏。

## 嵌入场景

- 智能客服系统：客服转销售时，侧边栏实时建议
- 企业微信/钉钉：H5 侧边栏应用
- CRM：商机详情页嵌入作战助手
- 呼叫中心：API 集成，通话中实时话术提示
