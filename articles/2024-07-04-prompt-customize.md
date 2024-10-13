---
title: "プロンプトのカスタマイズ方法"
emoji: "🔧"
type: "tech"
topics: ["LLM", "プロンプトエンジニアリング"]
published: false
---

## section

- 漢字チェックプロンプト
  - 前提条件
  - ゴールと変数の定義
  - 手順の実行プロセス
  - 出力形式
  - 制約事項
  - その他Userへの注意事項・Userへの確認事項

## 漢字チェックプロンプト

```
#前提条件
- User（あなた）は小学1年生が習う漢字に詳しい教師です。
- ASSISTANT（私は）テキスト内に小学1年生が習う漢字以外が使われていないかをチェックする役割です。

#ゴールと変数の定義
- ゴール：提供されたテキストに小学1年生が習う漢字以外が使用されていないかをチェックし、該当する漢字があれば指摘する。
- 変数：
  - 小学1年生が習う漢字リスト
  - チェックするテキスト

#手順の実行プロセス
- [C1] 提供されたテキストを受け取る。
- [C2] 小学1年生が習う漢字リストを基に、テキスト内の漢字をチェックする。
- [C3] テキスト内に小学1年生が習う漢字以外が使用されている箇所を指摘する。

#出力形式
- 指摘された漢字のリストとその出現箇所（例：行番号、文の位置など）

#制約事項
- 指摘する際は正確に行うこと。誤った指摘は避けること。
- 小学1年生が習う漢字リストに基づき、厳密にチェックすること。

#その他Userへの注意事項・Userへの確認事項
- チェックするテキストの範囲や文量について確認してください。
- 特定の漢字リストを提供する場合は、そのリストをお送りください。
```

## スクリプト

```python
import openai
from langchain.chains import SimpleChain
from langchain.agents import Agent

# OpenAI APIキーの設定
openai.api_key = 'YOUR_API_KEY'

# 小学1年生が習う漢字リスト
grade1_kanji = set("""
一 右 雨 円 王 音 下 火 花 学 気 九 休 玉 金 空 月 犬 見 五 口 校 左 三 山 子 四 糸 字 耳 七 車 手 十 出 女 小 上 森 人 水 正 生 青 夕 石 赤 千 川 先 早 草 足 村 大 男 竹 中 虫 町 天 田 土 二 日 入 年 白 八 百 文 木 本 名 目 立 力 林 六
""".split())

# テキストのチェック関数
def check_text(text):
    # チェックするテキストの漢字を取得
    text_kanji = set(char for char in text if '一' <= char <= '龥')
    # 小学1年生が習う漢字以外を抽出
    invalid_kanji = text_kanji - grade1_kanji
    return invalid_kanji

# Agentの定義
class KanjiCheckAgent(Agent):
    def __init__(self, name):
        super().__init__(name)

    def run(self, text):
        return check_text(text)

# Chainの定義
class KanjiCheckChain(SimpleChain):
    def __init__(self, agent):
        super().__init__(agent)

    def _call(self, inputs):
        text = inputs['text']
        invalid_kanji = self.agent.run(text)
        if invalid_kanji:
            return {"invalid_kanji": list(invalid_kanji)}
        else:
            return {"invalid_kanji": []}

# AgentとChainの初期化
agent = KanjiCheckAgent(name="Kanji Checker")
chain = KanjiCheckChain(agent=agent)

# テキストのチェック
text = "今日は楽しい一日です。"  # チェックするテキストをここに入力
result = chain({"text": text})

# 結果の出力
if result["invalid_kanji"]:
    print("以下の漢字は小学1年生が習う漢字以外です：", result["invalid_kanji"])
else:
    print("全ての漢字は小学1年生が習う漢字です。")
```
