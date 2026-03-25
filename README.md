# youtube-ai-to-wechat

`youtube-ai-to-wechat` 鏄竴涓潰鍚?Codex / 鏈湴鑴氭湰杩愯鐨勫唴瀹圭敓浜?skill锛岀敤鏉ユ妸 YouTube 涓婄殑 AI 涓婚瑙嗛涓庤ˉ鍏呯爺绌讹紝鏁寸悊鎴愰€傚悎寰俊鍏紬鍙疯崏绋跨鐨勪腑鏂囨枃绔犲寘銆?

褰撳墠浠撳簱鐘舵€佸搴旈涓叕寮€鍙戝竷鐗堟湰 `v0.2.0`锛岄粯璁ゅ畾浣嶆槸鈥滃崐鑷姩鐢熶骇鈥? 鑷姩瀹屾垚閫夐鍙戠幇銆佺礌鏉愭暣鐞嗐€佸啓浣溿€佸浘鐗囪鍒掋€佹帓鐗堝拰鑽夌涓婁紶鍑嗗锛屼汉鍐嶅鏍稿悗鍐冲畾鏄惁鍙戝竷銆?

## 鑳藉姏鑼冨洿

- 鍩轰簬涓婚璇嶆垨鍏抽敭璇嶆悳绱?YouTube AI 鍐呭鍊欓€?
- 瀵瑰€欓€夎棰戝仛鍘婚噸銆佸惎鍙戝紡鎵撳垎鍜屼紭鍏堢骇鎺掑簭
- 鐢熸垚 transcript/source pack锛屽苟琛ュ厖瀹樻柟璧勬枡绾跨储
- 鐢熸垚淇℃伅绋裤€佸井淇￠鏍兼敼鍐欑銆佹爣棰樺寘鍜屾憳瑕?
- 鐢熸垚灏侀潰鍥俱€侀厤鍥捐鍒掑拰淇℃伅鍥捐鍒?
- 杈撳嚭寰俊鍏紬鍙峰彲鐢ㄧ殑 HTML銆丮arkdown 棰勮鍜岃崏绋?payload
- 鏀寔鎸夐樁娈甸噸璇曘€佹柇鐐圭画璺戙€佸け璐ュ綊鍥犲拰杩愯鐘舵€佽惤鐩?

## 褰撳墠杈圭晫

- 榛樿浜у嚭鐩爣鏄?`draft_only`锛屼笉寤鸿鎶娾€滅洿鎺ュ彂甯冣€濅綔涓洪粯璁ゆ祦绋?
- 褰撳墠 transcript 闃舵浠?metadata fallback 涓轰富锛屼笉鏄畬鏁?ASR 绠＄嚎
- 浠撳簱娌℃湁鍐呯疆渚濊禆閿佸畾鏂囦欢锛岃繍琛屽墠闇€瑕佽嚜琛屽噯澶?Python 鐜
- 鐢熶骇妯℃澘榛樿鎸夊畼鏂规潵婧愪紭鍏堟姄鍥撅紝鎵句笉鍒版椂鎵嶅洖閫€ `Wikimedia`锛屼笉鍐嶉粯璁や娇鐢ㄦā鍨嬬敓鍥?

## 鐗堟湰涓庡彉鏇?

### 褰撳墠鐗堟湰

- 浠撳簱褰撳墠鍏紑鐗堟湰: `0.2.0`
- Git 鏍囩: `v0.2.0`
- 鍙戝竷鏃堕棿: `2026-03-25`

### 鍙樻洿璁板綍

#### [0.2.0] - 2026-03-25

鏈鏂板:

- 鏂板浠撳簱鍐呭彲鐩存帴缁存姢鐨勫叕寮€鍏ュ彛 `prompts/youtube-ai-to-wechat.prompt.md` 鍜 `scripts/run-youtube-ai-to-wechat.ps1`銆?
- 鏄庣‘ prompt 妯℃澘鍜岃繍琛岃剼鏈殑 canonical 缁存姢浣嶇疆鍦ㄥ綋鍓 skill 浠撳簱鍐咃紝渚夸簬鐙珛鍙戝竷涓庣増鏈拷韪€?
- 琛ユ洿 README 浣跨敤璇存槑锛岃ˉ鍏呬粨搴撳唴 prompt / runner 鍏ュ彛鍜岀浉鍏虫枃妗ｈ埅瀵笺€?

#### [0.1.1] - 2026-03-24

鏈淇:

- 鐮旂┒闃舵鎶?`topic` 鍜?`keywords` 绾冲叆瀹炰綋璇嗗埆锛岃ˉ榻?`wechat`銆乣tencent`銆乣n8n` 鐨勫畼鏂硅祫婧愭槧灏勶紝閬垮厤鈥滅浉鍏宠祫婧愨€濇钀戒负绌恒€?
- 璋冩暣鍥剧墖鎶撳彇绛栫暐涓哄畼鏂规潵婧愪紭鍏堬紝骞舵寜绔犺妭璇箟銆佹潵婧愬疄浣撳拰椤甸潰鍏冧俊鎭帓搴忥紝鎻愰珮姝ｆ枃閰嶅浘涓庡唴瀹圭殑鐩稿叧鎬с€?
- 淇灏侀潰鍥俱€佸唴鍥惧拰淇℃伅鍥剧殑姝ｆ枃鎸傝浇瑙勫垯锛岄伩鍏嶆妸鏂囩珷鏍囬璇綋鎴愰涓厤鍥剧珷鑺傘€?

#### [0.1.0] - 2026-03-24

棣栦釜鍏紑鐗堟湰銆?

鏈鏂板:

- 瀹屾垚 `youtube-ai-to-wechat` 鐙珛浠撳簱鐨勫叕寮€鍙戝竷鏁寸悊銆?
- 琛ラ綈椤跺眰璇存槑鏂囨。锛岃鐩栬兘鍔涜寖鍥淬€佽繍琛屽墠鍑嗗銆佸揩閫熷紑濮嬨€佷骇鐗╄鏄庡拰鏂囨。瀵艰埅銆?
- 绾冲叆褰撳墠瀹炵幇瀵瑰簲鐨勯厤缃€佽繍琛屻€丼chema銆佹ā鍨嬩笌鐜鍙橀噺璇存槑鏂囨。銆?

鏈増鏈寘鍚?:

- 浠?YouTube 鎼滅储銆佸€欓€夋帓搴忓埌 `source pack` 鐢熸垚鐨勪富棰橀┍鍔ㄥ彂鐜伴摼璺€?
- 甯﹂噸璇曘€佹仮澶嶃€侀樁娈垫棩蹇楀拰鏈哄櫒鍙杩愯鐘舵€佺殑 live pipeline 缂栨帓鑳藉姏銆?
- 闈㈠悜寰俊鍏紬鍙疯崏绋跨殑鍐欎綔銆佹敼鍐欍€佹帓鐗堛€佺礌鏉愭敞鍏ュ拰鑽夌 payload 鐢熸垚鑳藉姏銆?
- 鎸夊綋鍓嶉厤缃帴鍏ョ殑 Nanobanana 鍏煎鍥剧墖瑙勫垝涓庣敓鎴愰摼璺€?
- 鐢ㄤ簬棰勮銆佸垎鐜鎵ц鍜?OneIT 椋庢牸娴佺▼鐨?PowerShell 杩愯鑴氭湰绀轰緥銆?

## 浠撳簱缁撴瀯

```text
.
|-- SKILL.md
|-- CONFIG.md
|-- MODEL_ENV_GUIDE.zh-CN.md
|-- OPERATIONS.md
|-- SCHEMA.md
|-- VERSIONING.md
|-- prompts/
|-- assets/
|   |-- examples/
|   |-- templates/
|   `-- blocks/
|-- references/
|-- scripts/
`-- agents/
```

## 杩愯鍓嶅噯澶?

鏈€浣庡缓璁幆澧?

- Windows PowerShell 5.1+ 鎴?PowerShell 7+
- Python 3.10+
- 鍙洿鎺ヨ皟鐢ㄧ殑 `python`
- 绗笁鏂?Python 渚濊禆: `Pillow`

鎵€闇€澶栭儴鑳藉姏:

- `YOUTUBE_API_KEY`
- `MINIMAX_API_KEY`
- `WECHAT_ACCESS_TOKEN`
- 鎴栬€?`WECHAT_APP_ID` + `WECHAT_APP_SECRET`

寤鸿鍏堥槄璇?

- [`MODEL_ENV_GUIDE.zh-CN.md`](./MODEL_ENV_GUIDE.zh-CN.md)
- [`CONFIG.md`](./CONFIG.md)
- [`OPERATIONS.md`](./OPERATIONS.md)

瀹夎鏈€灏忎緷璧栫ず渚?

```powershell
python -m pip install Pillow
```

## 蹇€熷紑濮?

### 1. 澶嶅埗閰嶇疆妯℃澘

浠庝互涓嬫ā鏉垮紑濮嬩簩閫変竴:

- 閫氱敤妯℃澘: [`assets/examples/live_config.example.json`](./assets/examples/live_config.example.json)
- 鐢熶骇妯℃澘: [`assets/examples/environments/live_config.prod.example.json`](./assets/examples/environments/live_config.prod.example.json)

濡傛灉浣犻渶瑕佹湰鍦扮鏈夌幆澧冭剼鏈紝寤鸿鎶婄湡瀹炲瘑閽ユ斁鍒版湭绾冲叆鐗堟湰鎺у埗鐨勬湰鍦版枃浠朵腑锛屼笉瑕佺洿鎺ユ敼绀轰緥鏂囦欢鍚庢彁浜ゃ€?

### 2. 棰勮妯″紡璺戦€氫竴鏉′富棰橀摼璺?

浠撳簱鍐呮渶鐩存帴鐨?PowerShell 鍏ュ彛:

```powershell
powershell -ExecutionPolicy Bypass -File .\assets\examples\environments\run_oneit_topic.ps1 `
  -Topic "OpenAI Agents" `
  -Keywords "OpenAI Agents","AI agents" `
  -Preview
```

杩欎釜鍏ュ彛浼氬厛鐢熸垚:

- `search_candidates.auto.json`
- `ranked_candidates.auto.json`
- `transcript_pack.auto.json`
- `source_pack.auto.json`

鍐嶇户缁窇鏂囩珷涓庢帓鐗堥摼璺紝骞跺湪 `.runs/<run-name>/` 涓嬭緭鍑洪瑙堟枃浠跺拰鍙戝竷鍖呫€?

### 3. 鐩存帴浣跨敤 Python 涓诲叆鍙?

濡傛灉浣犲凡缁忔湁 `source_pack.json`锛屽彲浠ョ洿鎺ヨ皟鐢ㄥ畬鏁?live pipeline:

```powershell
python .\scripts\run_live_pipeline.py .\.runs\example\source_pack_v2.json `
  --output-dir .\.runs\2026-03-24-openai-agents-preview `
  --live-config .\assets\examples\environments\live_config.prod.example.json `
  --execute-llm `
  --max-retries 2 `
  --retry-policy smart
```

闇€瑕佺湡鐨勮皟鐢ㄥ浘鐗囨垨鑽夌涓婁紶鏃讹紝鍐嶆樉寮忓姞鍏?

- `--execute-images`
- `--execute-publish`

## 涓昏浜х墿

鍏稿瀷杩愯鐩綍浣嶄簬 `.runs/<run-name>/`锛屽父瑙佹枃浠跺寘鎷?

- `run_live_manifest.json`
- `pipeline_summary.json`
- `run_status.json`
- `article_preview.md`
- `article_preview.html`
- `formatted_article_live.json`
- `final_article_package_live.json`
- `draft_payload_live.json`
- `stage-logs/`

鏇村畬鏁寸殑瀛楁瀹氫箟瑙?[`SCHEMA.md`](./SCHEMA.md)銆?

## 浣滀负 Codex Skill 浣跨敤

濡傛灉浣犳妸杩欎釜浠撳簱浣滀负 skill 鐩存帴鎸傝浇缁?Codex锛屼富鍏ュ彛璇存槑鍦?[`SKILL.md`](./SKILL.md)銆?

鍦?`SkillsDemo` 涓讳粨搴撻噷锛屼篃鍙互閫氳繃浠撳簱绾у寘瑁呰剼鏈皟鐢?

```powershell
.\scripts\run-youtube-ai-to-wechat.ps1 -Topic "OpenAI Agents" -Preview
```


## Repository-local entrypoints

- Prompt template: [`prompts/youtube-ai-to-wechat.prompt.md`](./prompts/youtube-ai-to-wechat.prompt.md)
- Runner wrapper: [`scripts/run-youtube-ai-to-wechat.ps1`](./scripts/run-youtube-ai-to-wechat.ps1)
- Environment runner: [`assets/examples/environments/run_oneit_topic.ps1`](./assets/examples/environments/run_oneit_topic.ps1)

## 鏂囨。瀵艰埅

- [`SKILL.md`](./SKILL.md): skill 杈撳叆濂戠害涓庡伐浣滄祦
- [`CONFIG.md`](./CONFIG.md): 鍚堝苟閰嶇疆缁撴瀯璇存槑
- [`MODEL_ENV_GUIDE.zh-CN.md`](./MODEL_ENV_GUIDE.zh-CN.md): 褰撳墠瀹炵幇瀵瑰簲鐨勬ā鍨嬩笌鐜鍙橀噺閫熸煡
- [`OPERATIONS.md`](./OPERATIONS.md): 杩愯銆侀噸璇曘€佹仮澶嶅拰鏃ュ父 SOP
- [`SCHEMA.md`](./SCHEMA.md): 浜х墿缁撴瀯涓庡吋瀹瑰瓧娈?
- [`VERSIONING.md`](./VERSIONING.md): 鐗堟湰鍙蜂笌 tag 瑙勫垯
- `README.md`: 褰撳墠鐗堟湰鍙蜂笌鍙樻洿璁板綍



