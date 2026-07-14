1. 结构化目录与元数据读取

GET /api/v1/docs (获取文档列表)

参数： page, limit, tags, category, sort_by

功能： 让 Agent 获取特定标签（如“2026年日记”）下的所有文档清单，仅返回 doc_id、title、tags 等元数据，不返回正文。

GET /api/v1/docs/{doc_id}/outline (提取大纲结构)

参考思路： Obsidian API。

功能： 让 Agent 在阅读长文前，先调用此接口抽取文档的 Markdown 标题结构（#, ##, ###）。Agent 看到大纲后，再决定去读哪个具体章节。

2. 差异化阅读策略

GET /api/v1/docs/{doc_id}/content (读取全文)

功能： 获取完整的 Markdown 文本。仅在文档较短或需要做全局提炼总结时使用。

GET /api/v1/docs/{doc_id}/blocks (按块/段落读取)

参考思路： Notion API (Retrieve block children)。

功能： 允许 Agent 传入行号范围或块级 ID，仅拉取某几段内容。这对于处理超大文档（如十万字小说、长篇代码文档）极其重要。

3. 智能检索（最核心技能）

POST /api/v1/search/keyword (精准关键词检索)

参数： {"query": "服务器宕机报错", "regex": true}

功能： 传统的倒排索引搜索（类似 Elasticsearch 或 grep），适用于查代码片段、特定人名、精确术语。

核心模块二：精准变更与控制（增、删、改）—— Agent 的“手”
仅仅全量覆盖是危险的，修改接口必须支持“增量追加”和“打补丁”。

POST /api/v1/docs (新建文档)

请求体： {"title": "新项目规划", "content": "内容...", "tags": ["项目", "规划"]}

动作： 创建文件，执行 git add 和 git commit -m "Agent 创建: 新项目规划"。

PUT /api/v1/docs/{doc_id} (全量覆盖)

功能： 用新内容彻底替换老内容。适用于短文档的整体重写。

PATCH /api/v1/docs/{doc_id} (增量追加/打补丁)

参数： {"action": "append", "content": "\n\n## 补充记录..."} 或 {"action": "replace_block", "block_id": "xxx", "content": "..."}

功能： Agent 不用读取全文再改写全文，直接向文档末尾追加内容，或者仅替换指定的某一行/某一段。这极大降低了并发冲突和内容丢失的风险。

动作： 执行 git commit -m "Agent 追加/修改局部内容"。

PATCH /api/v1/docs/{doc_id}/meta (修改元数据)

参数： {"action": "add_tags", "tags": ["AI"]} 或 {"action": "update_title", "title": "新标题"}

功能： 仅修改文档的 Front-matter (YAML 区) 或相关元数据，不触碰正文内容，操作更轻量且安全。

DELETE /api/v1/docs/{doc_id} (逻辑删除)

动作： 不要执行物理删除，而是将其移动到 .trash/ 目录下（或打上 archived 标签），并在 Git 中记录，防止 Agent 发疯删空你的金库。

核心模块三：系统安全兜底（版本回退）—— 你的“后悔药”
Agent 是在黑盒中运行的，随时可能发生幻觉，这个模块是保障你心智安宁的基础。

GET /api/v1/docs/{doc_id}/history (查询修改历史)

功能： 获取该文件的 Git 提交记录（git log）。返回数组，包含 commit_hash, timestamp, message。

用途： Agent 可以自行查阅它昨天对这个文档做了什么修改；你也可以通过接口直接查询这些记录。

POST /api/v1/docs/{doc_id}/rollback (文档一键回滚)

参数： {"commit_hash": "a1b2c3d"}

底层机制： 锁定文件，执行 git checkout a1b2c3d -- {file_path}，然后再次 commit 生成一个新的回滚记录。

核心模块四：公网发布管理（生成 TOTP 保护端）—— 你的“窗口”
这部分接口依然是内网 Agent 调用的，用于它代替你完成“公网发布”这一动作。

POST /api/v1/share/publish (发布文档到只读区)

参数： {"doc_id": "xxx", "expire_in_hours": 24} (可选有效期)

功能： 后端将目标 Markdown 渲染成 HTML，生成静态文件放置在 Nginx 指向的特定目录，并生成 UUID。

GET /api/v1/share (获取已发布列表)

功能： 查阅当前有哪些文档正在公网挂着。

DELETE /api/v1/share/{uuid} (撤销公开链接)

功能： 物理删除 Nginx 目录下的那个 HTML 静态文件，公网访问立刻 404。



authenticator差点忘了，通过
/api/v1/open/authenticator打开totp动态口令页面
输入口令后，返回token，在访问/api/v1/share/publish时，传入token验证
GET /api/v1/open/authenticator → 返回 secret + otpauth_uri（首次配置用，手动录入 Authenticator App）
POST /api/v1/open/authenticator 传 {"code": "123456"} → 验证通过返回 {"publish_token": "xxx"}
POST /api/v1/share/publish 传 publish_token → 校验后才发布