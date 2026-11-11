# -*- coding: utf-8 -*-
"""生成「慢题」并追加到 大纲题库/题库.json

慢题 = 必须读完一段材料才能作答的题。现有题库全是「《少年中国说》作者是谁」
这类一眼能排除的短选择题，语文实测 6.4 秒/题、100% 正确率，等于白做。

用法：python 大纲题库/add_slow.py
幂等：每次先删掉 id 以 -SLOW- 开头的旧题，再加新的。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BANK = os.path.join(HERE, "题库.json")

SLOW = []


def add(qid, kp, diff, typ, stem, right=None, options=None, answer=None,
        hint="", explain="", dscore=None):
    """right 传正确选项原文，自动查下标，避免手填错位。"""
    item = {
        "id": qid,
        "知识点": [kp],
        "难度": diff,
        "类型": typ,
        "题干": stem,
        "答案": answer,
        "提示": hint,
        "解析": explain,
        "难度拆解": {"A": 2, "B": 2, "C": 1, "D": 2, "E": 2},
        "难度分": dscore if dscore else (9 if diff >= 3 else 7),
        "慢题": True,
    }
    if typ == "choice":
        if not options or right is None:
            raise SystemExit("选择题必须给 options 和 right: " + qid)
        if right not in options:
            raise SystemExit("right 不在选项里: " + qid + " -> " + right)
        item["选项"] = options
        item["答案"] = options.index(right)
    else:
        if answer is None:
            raise SystemExit("填空题必须给 answer: " + qid)
    SLOW.append(item)


# ---------------- 语文 8 道：都要先读一段 ----------------

add("Q-C-SLOW-01", "C-5A-U1-01", 2, "choice",
    "外婆家的院子里有一棵桂花树。每年秋天，风一吹，满院都是甜的。"
    "我离开家乡那年，外婆把晒干的桂花装进一个小布袋，塞进我的行李。"
    "这些年我搬了三次家，布袋一直带在身边。有时打开闻一闻，"
    "好像又回到那个院子，听见外婆在树下喊我吃饭。<br><br>"
    "这段文字借桂花表达的是（　）",
    right="对家乡和亲人的思念",
    options=["对家乡和亲人的思念", "对桂花香味的单纯喜爱",
             "对搬家生活的厌倦", "对外婆做饭手艺的赞美"],
    hint="桂花只是个由头，想想作者真正放不下的是什么。",
    explain="借物抒情：物是线索，情才是目的。桂花连着外婆、院子和离开的家乡，"
            "所以写桂花其实是在写思念。只答“喜欢香味”就把文章读浅了。")

add("Q-C-SLOW-02", "C-5A-U2-01", 2, "choice",
    "读书时，眼睛并不是一个字一个字地看，而是一次看一组词。"
    "刚开始练习的人，可以在书上轻轻画斜线，把句子分成几组，视线跟着斜线移动。"
    "遇到不懂的词，先做个记号跳过去，读完一段再回头看。"
    "如果每遇到一个生词就停下来查字典，读读停停，反而记不住整段在讲什么。<br><br>"
    "这段话主要想告诉我们（　）",
    right="怎样读得快一些又不丢掉整体意思",
    options=["怎样读得快一些又不丢掉整体意思", "查字典是阅读中最重要的事",
             "读书必须一个字一个字地看", "生词多的文章最好不要读"],
    hint="注意“如果……反而……”这一句，作者在反对什么。",
    explain="整段都在讲方法：按词组看、画斜线、跳过生词回头再看。"
            "最后一句是反面提醒——不停查字典会破坏整体理解。")

add("Q-C-SLOW-03", "C-5A-U3-01", 2, "choice",
    "从前有个农夫，每天下地都要经过一座石桥。有一年大旱，河底裂开了缝。"
    "他在桥下发现一只陶罐，罐口封着蜡。打开一看，里面是一张字条，"
    "写着“留给过桥的人”，还有一捧谷种。农夫把谷种分给了村里人，"
    "那一年，只有他们村没有饿死人。后来人们才知道，那是上一辈人偷偷攒下的。<br><br>"
    "这个故事最能体现民间故事的什么特点？（　）",
    right="靠口耳相传流传，寄托着普通人的愿望",
    options=["靠口耳相传流传，寄托着普通人的愿望", "有确切的作者和写作年代",
             "用大量数据来说明一个道理", "描写的是现代城市里的生活"],
    hint="民间故事是谁讲给谁听的？讲的人想让大家记住什么？",
    explain="民间故事没有署名作者，靠一代代人口头讲下来。"
            "“善有善报、互相帮衬”正是普通人最朴素的愿望。")

add("Q-C-SLOW-04", "C-5A-U3-02", 2, "choice",
    "《猎人海力布》里，海力布听懂了鸟的语言，得知大山要崩塌。"
    "他挨家挨户劝乡亲们搬家，可谁也不信。为了让大家相信，他只好说出实情——"
    "而一旦说出，他就会变成石头。话刚说完，他就变成了石头。<br><br>"
    "如果要“创造性复述”这个故事，下面哪种做法最合适？（　）",
    right="加上海力布劝说时的心理活动，用他的口吻讲",
    options=["加上海力布劝说时的心理活动，用他的口吻讲",
             "把故事梗概原样抄一遍，一个字不改",
             "只讲结局，省掉起因和经过",
             "改写成说明文，列出山崩的科学原因"],
    hint="“创造性”三个字是关键：要在不改变故事的前提下加点自己的东西。",
    explain="创造性复述允许换人称、加细节、补心理活动，但不能改变情节和结局。"
            "照抄不算创造，砍掉经过就不成故事，改成说明文就换了体裁。")

add("Q-C-SLOW-05", "C-5A-U5-01", 2, "choice",
    "鲸是海洋里最大的动物。一头蓝鲸长可达三十米，重达一百五十吨，"
    "相当于二十五头大象的体重。它的舌头就有两吨重，上面站得下十几个成年人。"
    "这样庞大的动物，却以只有几厘米长的小虾为食。<br><br>"
    "“相当于二十五头大象的体重”这句话用了什么说明方法？（　）",
    right="作比较",
    options=["作比较", "打比方", "举例子", "分类别"],
    hint="拿蓝鲸和另一种东西比轻重，比的对象是什么？",
    explain="作比较是拿一个熟悉的事物去比，让人对陌生数字有概念。"
            "打比方是“像什么”，举例子是“比如”，分类别是“分几类”。")

add("Q-C-SLOW-06", "C-5A-U5-02", 3, "choice",
    "松鼠的窝通常搭在树枝分杈的地方，又干净又暖和。"
    "它们搭窝的时候，先搬些小木片，错杂着放在一起，再用一些干苔藓编扎起来，"
    "然后把苔藓挤紧、踏平，使那建筑物足够宽敞、足够坚实。<br><br>"
    "文中“通常”一词能不能删掉？为什么？（　）",
    right="不能删，“通常”表示大多数情况，删掉就变成全部，不符合事实",
    options=["不能删，“通常”表示大多数情况，删掉就变成全部，不符合事实",
             "能删，删掉以后句子更简洁",
             "不能删，因为“通常”是个形容词，删了就缺成分",
             "能删，松鼠本来就都搭在树枝分杈处"],
    hint="删掉以后，句子的意思有没有变得更“绝对”？",
    explain="说明文讲究准确。“通常”留了余地——大部分搭在分杈处，也有例外。"
            "删掉就变成了“全部”，反而不准确。")

add("Q-C-SLOW-07", "C-5A-U6-01", 2, "choice",
    "母亲说完，立刻又坐了下去，立刻又弯曲了背，立刻又将头俯在缝纫机板上了，"
    "立刻又陷入了忙碌……我手里捏着那本一元五角钱的《青年近卫军》，鼻子一酸。<br><br>"
    "这段文字主要用了什么方法写母亲？（　）",
    right="动作描写，用反复出现的动作表现母亲的辛劳",
    options=["动作描写，用反复出现的动作表现母亲的辛劳",
             "外貌描写，细致刻画了母亲的长相",
             "语言描写，完整记录了母亲说的话",
             "环境描写，烘托了车间里的气氛"],
    hint="数一数这段话里有几个“立刻又”，它们都在写什么。",
    explain="四个“立刻又”接连写坐、弯、俯、忙碌，全是动作。"
            "反复不是啰嗦，是把母亲的劳累写得停不下来。")

add("Q-C-SLOW-08", "C-5A-U1-02", 2, "choice",
    "落花生埋在土里，不像桃子、石榴、苹果那样，把鲜红嫩绿的果实高高地挂在枝头，"
    "使人一见就生爱慕之心。它矮矮地长在地上，等到成熟了，"
    "也不能立刻分辨出来它有没有果实，必须挖起来才知道。<br><br>"
    "这段话借花生说明了应该做什么样的人？（　）",
    right="不图虚名、默默做事的人",
    options=["不图虚名、默默做事的人", "外表好看、善于表现的人",
             "果实累累、让人羡慕的人", "长在高处、看得最远的人"],
    hint="花生和桃子苹果最大的不同在哪？作者赞美的是哪一种？",
    explain="借物喻人：用花生的“埋在地下、要挖才知道”比喻默默做事、"
            "不靠外表讨人喜欢的人。写桃子苹果是为了反衬。")

# ---------------- 英语 6 道：短文理解 ----------------

add("Q-E-SLOW-01", "E-5A-U1-02", 2, "choice",
    "Hello! I'm Amy. I have a new friend. Her name is Lily. She is tall and thin. "
    "She has long hair and big eyes. She is very kind. She often helps me with my English. "
    "We are in the same class.<br><br>What is Lily like?",
    right="She is tall and kind.",
    options=["She is tall and kind.", "She is short and strict.",
             "She is old and quiet.", "She is tall and funny."],
    hint="What is ... like? 问的是「什么样」，要看外貌和性格两方面。",
    explain="短文写了 tall and thin / long hair and big eyes（外貌），"
            "and very kind（性格）。B 的 short、C 的 old、D 的 funny 文中都没有。")

add("Q-E-SLOW-02", "E-5A-U2-02", 2, "choice",
    "Hi, I'm Tom. On Mondays I have Chinese, maths and English. "
    "On Wednesdays I have music and art. I like Thursdays best, because we have PE. "
    "I don't like Fridays, because there are two maths classes.<br><br>"
    "What does Tom have on Wednesdays?",
    right="Music and art.",
    options=["Music and art.", "Chinese and maths.",
             "PE and music.", "Two maths classes."],
    hint="先找到 Wednesdays 这个词，再看它后面跟着什么课。",
    explain="Wednesdays 对应 music and art。PE 是 Thursday，"
            "Chinese and maths 是 Monday，two maths classes 是 Friday。")

add("Q-E-SLOW-03", "E-5A-U3-02", 2, "choice",
    "Welcome to my home! Today is my birthday. There is a big cake on the table. "
    "We have juice, milk and tea. I'd like some juice. "
    "My brother would like a hamburger and some milk. "
    "My mother would like a sandwich and tea.<br><br>"
    "What would Tom's brother like?",
    right="A hamburger and some milk.",
    options=["A hamburger and some milk.", "A sandwich and tea.",
             "Some juice and a cake.", "A hamburger and some juice."],
    hint="注意问的是 brother，不是作者自己，也不是 mother。",
    explain="文中 My brother would like a hamburger and some milk。"
            "juice 是作者要的，sandwich and tea 是妈妈要的。")

add("Q-E-SLOW-04", "E-5A-U4-02", 2, "choice",
    "We have many clubs in our school. In the music club, you can sing and play the pipa. "
    "In the art club, you can draw pictures. In the sports club, "
    "you can play basketball and swim. I'm in the music club. "
    "I can sing well, but I can't play the pipa.<br><br>What can the writer do?",
    right="Sing well.",
    options=["Sing well.", "Play the pipa well.",
             "Draw pictures well.", "Play basketball well."],
    hint="最后两句用了 but，说明有一件事他会、另一件不会。",
    explain="I can sing well, but I can't play the pipa。"
            "draw 和 play basketball 都是别的社团的活动，文中没说他参加。")

add("Q-E-SLOW-05", "E-5A-U1-01", 2, "choice",
    "I have a good friend. His name is Ben. He is short but strong. "
    "He has short black hair and a round face. He wears glasses. "
    "He is good at maths. He often says, \"Let me help you.\"<br><br>"
    "Which is RIGHT about Ben?",
    right="He is short, strong and wears glasses.",
    options=["He is short, strong and wears glasses.",
             "He is tall and has long hair.",
             "He is thin and doesn't wear glasses.",
             "He is good at English."],
    hint="逐个选项回原文核对，只要有一处不符就排除。",
    explain="原文 short but strong、short black hair、wears glasses、good at maths。"
            "B 的 tall/long hair、C 的 doesn't wear glasses、D 的 English 都对不上。")

add("Q-E-SLOW-06", "E-6A-U4-02", 2, "choice",
    "My uncle is a teacher. He gets up at six every morning. He goes to school by bus. "
    "He teaches English. He likes reading books. "
    "After school, he often plays football with his students.<br><br>"
    "Which sentence is RIGHT?",
    right="He goes to school by bus.",
    options=["He goes to school by bus.", "He go to school by bus.",
             "He going to school by bus.", "He gone to school by bus."],
    hint="主语是 He（第三人称单数），动词要加 s。",
    explain="一般现在时、主语第三人称单数，动词加 -s：goes。"
            "go 是原形，going 缺 be 动词，gone 是过去分词，都不能单独作谓语。")

# ---------------- 数学 6 道：应用题，要动笔 ----------------

add("Q-M-SLOW-01", "M-5A-U1-05", 2, "number",
    "妈妈去超市买水果。苹果每千克 8.6 元，买了 2.5 千克；"
    "香蕉每千克 5.4 元，买了 1.8 千克。她付给收银员 50 元。<br><br>"
    "应找回多少元？（只填数字）",
    answer=18.78,
    hint="先分别算出两种水果各花多少钱，加起来，再用 50 去减。",
    explain="苹果 8.6×2.5=21.5 元，香蕉 5.4×1.8=9.72 元，合计 31.22 元，"
            "找回 50−31.22=18.78 元。")

add("Q-M-SLOW-02", "M-5A-U3-05", 2, "number",
    "一根绳子长 9.5 米，每 1.2 米剪一段做跳绳。"
    "剩下的不够一段就留着。<br><br>最多能剪成几段？（只填数字）",
    answer=7,
    hint="9.5÷1.2 除不尽。剪绳子只能取整数段，剩下的零头算不了一段。",
    explain="9.5÷1.2≈7.9。做跳绳要“整段”，多的 0.1 段不足一段，"
            "所以只能剪 7 段（这叫去尾法）。")

add("Q-M-SLOW-03", "M-5A-U5-04", 2, "number",
    "学校买了 8 个足球和 5 个篮球，一共花了 1015 元。"
    "每个篮球 75 元。<br><br>每个足球多少元？（只填数字）",
    answer=80,
    hint="先算 5 个篮球一共多少钱，剩下的钱就是 8 个足球的。",
    explain="篮球 75×5=375 元，足球共 1015−375=640 元，"
            "每个 640÷8=80 元。")

add("Q-M-SLOW-04", "M-5A-U1-04", 2, "number",
    "每袋大米重 2.5 千克，每箱装 4 袋。食堂买了 12 箱。<br><br>"
    "一共买了多少千克大米？（只填数字）",
    answer=120,
    hint="可以先把一箱的重量算出来，也可以先算总袋数。",
    explain="一箱 2.5×4=10 千克，12 箱 10×12=120 千克。"
            "也可以写成 2.5×4×12，先算 2.5×4 更简便。")

add("Q-M-SLOW-05", "M-5A-U3-03", 2, "number",
    "做一套衣服要用布 2.3 米。有一匹布长 15 米，"
    "做完剩下的布不够再做一套。<br><br>最多能做几套？（只填数字）",
    answer=6,
    hint="15÷2.3 除不尽。衣服只能做整套，零头布做不成一套。",
    explain="15÷2.3≈6.52。做衣服要“整套”，0.52 套做不出来，"
            "所以最多 6 套（去尾法）。")

add("Q-M-SLOW-06", "M-5A-U5-03", 2, "number",
    "小红买了 3 本同样的笔记本，付给售货员 20 元，找回 3.5 元。<br><br>"
    "每本笔记本多少元？（只填数字）",
    answer=5.5,
    hint="先算 3 本一共花了多少钱，再平摊到每本。",
    explain="3 本共花 20−3.5=16.5 元，每本 16.5÷3=5.5 元。"
            "也可以列方程 3x+3.5=20。")

# ---------------- 写入 ----------------

def main():
    if not os.path.exists(BANK):
        raise SystemExit("找不到题库：" + BANK)
    d = json.load(io.open(BANK, encoding="utf-8"))
    before = len(d["题目"])
    d["题目"] = [q for q in d["题目"] if "-SLOW-" not in q["id"]]
    removed = before - len(d["题目"])
    d["题目"].extend(SLOW)

    # 自检：id 不重复、知识点都存在、选择题答案下标合法
    ids = [q["id"] for q in d["题目"]]
    dup = [i for i in set(ids) if ids.count(i) > 1]
    if dup:
        raise SystemExit("id 重复：" + str(dup))
    kps = {k["id"] for k in d["知识点"]}
    for q in SLOW:
        for k in q["知识点"]:
            if k not in kps:
                raise SystemExit("知识点不存在：" + k)
        if q["类型"] == "choice":
            if not (0 <= q["答案"] < len(q["选项"])):
                raise SystemExit("答案下标越界：" + q["id"])

    json.dump(d, io.open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("原有 %d 题，移除旧慢题 %d 道，新增慢题 %d 道，现在共 %d 题"
          % (before, removed, len(SLOW), len(d["题目"])))
    for s in ["语", "英", "数"]:
        pass
    from collections import Counter
    c = Counter(q["id"].split("-")[1] for q in SLOW)
    print("分布：语文 %d / 英语 %d / 数学 %d" % (c.get("C", 0), c.get("E", 0), c.get("M", 0)))


if __name__ == "__main__":
    main()
